"""End-to-end smoke inside IRIS embedded Python (irispython tests/iris/production_smoke.py /opt/pbp):
setup, start the production, feed the synthetic cases (recorded agent, no key), review as the current
IRIS user (needs PBPReview:U or %All), and assert: seal before effect, one effect, tamper detection,
duplicate intake ignored, ledger refusals sealed and acknowledged without effect. Prints a JSON marker."""
import json, sys, time, uuid
from pathlib import Path


def j(s):
    return json.loads(s if isinstance(s, str) else s._ToJSON())


def run(root='/opt/pbp'):
    import iris
    if iris.cls('pbp.Agent').HasKey() and iris.cls('pbp.Util').Env('PBP_LLM_MODE','auto') != 'recorded':
        raise RuntimeError('recorded_lab_required_no_implicit_paid_inference')
    tag = uuid.uuid4().hex[:10]
    cid = lambda original: original + ':' + tag
    out = {'schema': 'pbp.iris.production_smoke/3', 'run_tag': tag, 'checks': []}
    status_cls = iris.cls('%SYSTEM.Status')

    def check(name, cond, detail=''):
        if not cond:
            raise AssertionError(f'{name}: {detail}')
        out['checks'].append(name)

    sc = iris.cls('pbp.Setup').Install(root, 1)
    check('setup_ok', status_cls.IsOK(sc), status_cls.GetErrorText(sc))
    director = iris.cls('Ens.Director')
    for _ in range(60):
        name = iris.ref('')
        if director.IsProductionRunning(name) and name.value == 'pbp.Production':
            break
        time.sleep(1)
    name = iris.ref('')
    check('production_running', director.IsProductionRunning(name) and name.value == 'pbp.Production', str(name.value))
    svc = iris.ref(None)
    sc = director.CreateBusinessService('pbp.Service.Intake', svc)
    check('intake_service', status_cls.IsOK(sc))
    payloads = {}
    for path in sorted(Path(root, 'fixtures/cases').glob('*.json')):
        case = json.loads(path.read_text())
        original = case['case_id']
        case['case_id'] = cid(original)
        for payment in case.get('payments', []):
            payment['payment_ref'] += ':' + tag
        payloads[original] = json.dumps(case)
        replay = iris.gref('^pbp.replay').get([original])
        if replay:
            decision = json.loads(replay)
            decision['evidence_refs'] = [ref + ':' + tag if ref.startswith('pix:') else ref for ref in decision.get('evidence_refs', [])]
            iris.gref('^pbp.replay').set([cid(original)], json.dumps(decision))
        sc = svc.value.ProcessInput(iris.cls('Ens.StringContainer')._New(payloads[original]), iris.ref(None))
        check('feed_' + original, status_cls.IsOK(sc), status_cls.GetErrorText(sc))

    def statuses():
        return {case_id: st for case_id, st in iris.sql.exec('SELECT CaseId, Status FROM pbp_Data."Case" WHERE CaseId LIKE ?', '%:' + tag)}

    def wait_for(expected, seconds=120):
        deadline = time.time() + seconds
        st = {}
        while time.time() < deadline:
            st = statuses()
            if all(st.get(cid(c)) in exp for c, exp in expected.items()):
                return st
            time.sleep(2)
        return st

    phase1 = {
        'pix-0001': {'awaiting_human'},  # R1 refund_duplicate 18990: staged in the test ledger, reviewer needed
        'pix-0002': {'awaiting_human'},  # R1 129900 > ledger cap: sealed, ledger blocked, reviewer acknowledges
        'pix-0003': {'closed'},          # R2 no money
        'pix-0004': {'closed'},          # R3 no money
        'pix-0005': {'awaiting_human'},  # recorded escalate
        'pix-0006': {'awaiting_human'},  # recorded hold_for_evidence
        'pix-0007': {'awaiting_human'},  # recorded escalate
        'pix-0008': {'awaiting_human'},  # recorded retry_withdrawal, human
        'pix-0009': {'awaiting_human'},  # refund target unknown: sealed, ledger blocked
        'pix-0010': {'closed'},          # R2 underpayment
    }
    st = wait_for(phase1)
    for c, exp in phase1.items():
        check(f'phase1_{c}', st.get(cid(c)) in exp, f'got {st.get(cid(c))}')

    seals = {cid: (src, led) for cid, src, led in iris.sql.exec("SELECT CaseId, Source, LedgerState FROM pbp_Data.Seal WHERE Kind = 'decision'")}
    check('pix1_staged_in_ledger', seals.get(cid('pix-0001')) == ('ledger', 'awaiting_approval'), str(seals.get(cid('pix-0001'))))
    check('pix2_sealed_but_ledger_blocked', seals.get(cid('pix-0002'), ('', ''))[1].startswith('blocked:refund_cap_exceeded'), str(seals.get(cid('pix-0002'))))
    check('pix9_sealed_but_ledger_blocked', seals.get(cid('pix-0009'), ('', ''))[1].startswith('blocked:'), str(seals.get(cid('pix-0009'))))

    review = iris.cls('pbp.Review')
    def head(cid):
        return list(iris.sql.exec('SELECT HeadCommitment FROM pbp_Data."Case" WHERE CaseId = ?',cid))[0][0]
    r = j(review.Act(cid('pix-0001'), 'Approve', 'smoke approval',head(cid('pix-0001'))))
    check('review_approve_pix1', r['ok'], json.dumps(r))
    approved_user = r['user']
    r = j(review.Act(cid('pix-0006'), 'Reject', 'smoke rejection',head(cid('pix-0006'))))
    check('review_reject_pix6', r['ok'], json.dumps(r))
    r = j(review.Act(cid('pix-0002'), 'Approve', 'acknowledged, no effect possible',head(cid('pix-0002'))))
    check('review_ack_pix2', r['ok'], json.dumps(r))

    phase2 = {'pix-0001': {'closed'}, 'pix-0006': {'rejected'}, 'pix-0002': {'closed_no_effect'}}
    st = wait_for(phase2)
    for c, exp in phase2.items():
        check(f'phase2_{c}', st.get(cid(c)) in exp, f'got {st.get(cid(c))}')

    commit = list(iris.sql.exec("SELECT Commitment FROM pbp_Data.Seal WHERE CaseId = ? AND Kind = 'decision'",cid('pix-0001')))[0][0]
    led = j(iris.cls('ProofBeforePay.Ledger').Read(commit))
    check('ledger_confirmed_one_effect', led['ok'] and led['state'] == 'confirmed' and led.get('effect_count') == 1, json.dumps(led))
    rc = led['receipt']
    check('seal_before_authorize_before_effect', rc['sealed_seq'] < rc['authorized_seq'] < rc['executed_seq'], json.dumps(rc))
    check('approved_by_reviewer_session', led.get('approved_by') == approved_user and approved_user not in ('', 'operator', '_Ensemble'), str(led.get('approved_by')))
    rows = list(iris.sql.exec("SELECT Status FROM pbp_Data.Receipt WHERE CaseId = ?",cid('pix-0001')))
    check('one_receipt_copy', len(rows) == 1 and rows[0][0] == 'effected', str(rows))
    kinds = [k for (k,) in iris.sql.exec("SELECT Kind FROM pbp_Data.Seal WHERE CaseId = ? ORDER BY ID",cid('pix-0001'))]
    check('decision_then_approval_sealed', kinds == ['decision', 'approval'], str(kinds))

    s = iris.cls('pbp.Data.Seal').Find(commit)
    rec = json.loads(s.RecordJSON)
    rec['decision']['amount_minor'] = '1'
    reply = j(s.Verify(json.dumps(rec)))
    check('tamper_detected', reply['ok'] is False and reply['state'] == 'tampered', str(reply.get('reason')))
    reply = j(s.Verify(''))
    check('intact_verifies', reply['ok'] is True, str(reply.get('reason')))

    svc = iris.ref(None)
    sc = director.CreateBusinessService('pbp.Service.Intake', svc)
    check('intake_service', status_cls.IsOK(sc))
    sc = svc.value.ProcessInput(iris.cls('Ens.StringContainer')._New(payloads['pix-0001']), iris.ref(None))
    time.sleep(5)
    led2 = j(iris.cls('ProofBeforePay.Ledger').Read(commit))
    check('duplicate_intake_no_second_effect', led2.get('effect_count') == 1, json.dumps(led2))
    dup = list(iris.sql.exec("SELECT COUNT(*) FROM pbp_Data.Event WHERE CaseId = ? AND Kind = 'duplicate_intake_ignored'",cid('pix-0001')))[0][0]
    check('duplicate_intake_event', dup >= 1, str(dup))

    bad = iris.cls('pbp.Util').GuardJSON('{"case_id":"pii-1","exception":"x","evidence":{"mail":"a@b.invalid"}}', 60000)
    check('intake_guard_pii', bad == 'personal_data_found', bad)

    by = {r[0].lower(): r[1] for r in iris.sql.exec('SELECT Source, COUNT(*) FROM pbp_Data.Decision WHERE CaseId LIKE ? GROUP BY Source', '%:' + tag)}
    check('rules_and_model_split', by.get('rules', 0) >= 5 and by.get('model', 0) >= 4, str(by))
    modes = {r[0].lower() for r in iris.sql.exec("SELECT DISTINCT Mode FROM pbp_Data.Decision WHERE Source = 'model' AND CaseId LIKE ?", '%:' + tag)}
    check('model_mode_labelled', modes <= {'recorded', 'live'} and modes, str(modes))
    check('stale_review_version_denied', j(review.Act(cid('pix-0005'), 'Approve', '', '0' * 64)).get('reason') == 'reviewed_version_changed')
    out['ok'] = True
    out['count'] = len(out['checks'])
    out['status'] = statuses()
    return json.dumps(out, sort_keys=True)


if __name__ == '__main__':
    try:
        print('PBP_PRODUCTION_SMOKE=' + run(sys.argv[1] if len(sys.argv) > 1 else '/opt/pbp'))
    except Exception as e:  # noqa
        print('PBP_PRODUCTION_SMOKE=' + json.dumps({'ok': False, 'error': str(e)}))
        sys.exit(1)
