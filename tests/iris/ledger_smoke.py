"""Actual native IRIS storage, approval, effect and recovery tests (no model calls)."""
import copy,json,sys,uuid
from pathlib import Path


def run():
    import iris
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from ledger_fixtures import refund
    ledger=iris.cls('ProofBeforePay.Ledger')
    db=iris.gref('^PBP49Ledger')
    run_id='run'+uuid.uuid4().hex[:8]
    checks=[]
    def check(name,value):
        if not value:raise AssertionError(name)
        checks.append(name)
    def call(method,*args):return json.loads(getattr(ledger,method)(*args))
    r=refund(run_id)
    staged=call('Stage',json.dumps(r));check('stage_succeeds',staged.get('ok') is True)
    c=staged['commitment'];key=r['saw']['inputs']['refund_payment_ref']
    check('stage_persisted_before_effect',staged['state']=='awaiting_approval' and not staged['test_effect'])
    check('no_real_payment_or_anchor_claim',staged['authorizes_real_payment'] is False and staged['on_chain_verified'] is False)
    check('proof_matches_locally',call('Verify',c)['ok'])
    check('cannot_execute_before_approval',call('Execute',c)['reason']=='not_authorized')
    probe=iris.cls('ProofBeforePay.Tests.LedgerProbe')
    forbidden=json.loads(probe.UnprivilegedApprove(c))
    check('unprivileged_reviewer_denied',forbidden['reason']=='review_forbidden' and forbidden.get('test_logged_in') is True and forbidden.get('test_user_deleted') is True)
    nested=json.loads(probe.NestedStage(json.dumps(refund('nested-'+run_id))))
    check('does_not_commit_or_rollback_callers_transaction',nested['reason']=='nested_transaction' and nested['before']==nested['after']==1)
    check('cannot_approve_other_version',call('Approve','f'*64)['ok'] is False)
    # Change the stored record after sealing, then restore it for the next test.
    original=db['decision',c,'record']
    tampered=copy.deepcopy(r);tampered['missing']['delivery_photo']='filled after sealing'
    db['decision',c,'record']=json.dumps(tampered)
    check('filled_missing_breaks_proof',not call('Verify',c)['ok'])
    check('invalid_proof_cannot_be_approved',call('Approve',c)['reason']=='proof_invalid')
    db['decision',c,'record']=original
    a=call('Approve',c);check('authenticated_review',a['ok'] and a['state']=='authorized' and bool(a['approved_by']))
    check('approval_bound_to_commitment',db['decision',c,'approved_commitment']==c)
    tampered=copy.deepcopy(r);tampered['saw']['inputs']['recipient_ref']='test:changed-after-review'
    db['decision',c,'record']=json.dumps(tampered)
    check('approved_record_cannot_change_target',call('Execute',c)['reason']=='proof_invalid')
    db['decision',c,'record']=original
    first=call('Execute',c);check('test_effect_persisted',first['ok'] and first['state']=='executed')
    receipt=first['receipt']
    check('effect_uses_sealed_target_amount',receipt['amount_minor']=='15990' and receipt['recipient_ref']==r['saw']['inputs']['recipient_ref'] and receipt['effect_key']==key)
    check('seal_and_approval_precede_effect',receipt['sealed_seq']<receipt['authorized_seq']<receipt['executed_seq'])
    # Pretend that the first committed response was lost: query/retry, no repost
    # with a new idempotency key or newly supplied amount/recipient.
    again=call('Execute',c)
    check('uncertain_response_retry_same_receipt',again['ok'] and again['receipt']==receipt and again['replayed'])
    check('one_effect_after_retry',again['effect_count']==1)
    # A new salt and a different case still cannot refund the same payment twice.
    duplicate=copy.deepcopy(r);duplicate['case']['id']='test:another-'+run_id
    d=call('Stage',json.dumps(duplicate))
    check('different_case_and_seal_deduplicated',not d['ok'] and d['reason']=='payment_already_staged' and call('Read',c)['effect_count']==1)
    raw_effect=db['effect',key]
    changed=json.loads(raw_effect);changed['amount_minor']='1'
    db['effect',key]=json.dumps(changed)
    check('independent_readback_rejects_effect_tamper',call('Confirm',c)['reason']=='readback_mismatch')
    db['decision',c,'receipt']=json.dumps(changed)
    check('rewriting_both_receipt_copies_cannot_change_bound_effect',call('Confirm',c)['reason']=='readback_mismatch')
    check('replay_also_checks_bound_receipt',call('Execute',c)['reason']=='readback_mismatch')
    db['decision',c,'receipt']=raw_effect
    db['effect',key]=raw_effect
    confirmed=call('Confirm',c)
    check('readback_confirms_effect',confirmed['state']=='confirmed' and confirmed['confirmed_seq']>receipt['executed_seq'])
    check('confirmed_replay_is_idempotent',call('Execute',c)['receipt']==receipt and call('Read',c)['effect_count']==1)
    check('receipt_does_not_claim_settlement',receipt['environment']=='sandbox' and receipt['settlement_verified'] is False)
    check('read_omits_salt',not {'salt','record'} & call('Read',c).keys())
    other=refund('reject-'+run_id);o=call('Stage',json.dumps(other));oc=o['commitment']
    check('human_rejection_persisted',call('Reject',oc)['state']=='rejected')
    check('rejected_cannot_execute',call('Execute',oc)['reason']=='not_authorized')
    bad=refund('bad-'+run_id);bad['decision']['requires_human']=False;bad['limits']['autonomous_minor']='999999'
    check('model_cannot_raise_own_autonomy',call('Stage',json.dumps(bad))['reason']=='human_required')
    missing=refund('missing-'+run_id);missing['missing']['refund_target']=None
    check('critical_missing_blocks_stage',call('Stage',json.dumps(missing))['reason']=='required_evidence_missing')
    held=refund('held-'+run_id);held['decision'].update(action='request_information',moves_money=False)
    h=call('Stage',json.dumps(held));check('nonfinancial_decision_is_sealed',h['ok'] and h['state']=='sealed' and not h['test_effect'])
    check('nonfinancial_cannot_execute',call('Execute',h['commitment'])['reason']=='not_authorized')
    for malformed in ('','F'*64,'x'*64,'f'*65):
        check('malformed_commitment_'+str(len(checks)),not call('Execute',malformed)['ok'])
    expired=call('Stage',json.dumps(refund('expired-before-'+run_id)));ec=expired['commitment']
    db['decision',ec,'expires_seconds']=0
    check('expired_decision_cannot_be_approved',call('Approve',ec)['reason']=='authorization_expired')
    expired=call('Stage',json.dumps(refund('expired-after-'+run_id)));ec=expired['commitment']
    call('Approve',ec);db['decision',ec,'expires_seconds']=0
    check('expired_authorization_cannot_execute',call('Execute',ec)['reason']=='authorization_expired')
    # Prepare a distinct authorized item for independent IRIS session workers.
    concurrent=refund('race-'+run_id);race=call('Stage',json.dumps(concurrent));rc=race['commitment']
    check('race_prepared',call('Approve',rc)['state']=='authorized')
    return json.dumps(dict(schema='pbp.iris.ledger-tests/1',ok=True,count=len(checks),checks=checks,
                           concurrency_commitment=rc,confirmed_commitment=c,run_id=run_id,
                           model_calls=0,external_payments=0),sort_keys=True)
