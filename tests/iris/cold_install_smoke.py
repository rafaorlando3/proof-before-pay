"""One recorded non-money case after a fresh isolated installation.

Requires an empty USER application extent and recorded mode. Creates one synthetic
case and a pending review task; never approves, pays, enables RAG or calls a model.
Run via scripts/cold-install-smoke.script inside a disposable stock154U instance.
This is separate from the full production_smoke.py workflow.
"""
import json
import traceback

def error_record(error):
    record = {'type': type(error).__name__, 'message_ascii': ascii(str(error))[:1024],
              'traceback_ascii': traceback.format_exc(limit=12).encode('ascii', 'backslashreplace').decode('ascii')[:4096]}
    if isinstance(error, UnicodeDecodeError):
        record.update(encoding=error.encoding, start=error.start, end=error.end,
                      reason=error.reason, object_bytes=len(error.object),
                      object_prefix_hex=error.object[:256].hex(), prefix_limit_bytes=256)
    return record

def present(value, expected):
    """Check a specific native class without testing the proxy's truth value."""
    assert expected in {'pbp.Data.Case', 'pbp.Data.Seal', 'Ens.Config.Production'}
    if any(type(value) is primitive for primitive in
           (type(None), str, bytes, int, float, bool)):
        return False
    answer = value._IsA(expected)
    assert type(answer) is int or type(answer) is bool, 'native_IsA_unexpected_type'
    assert answer in (0, 1), 'native_IsA_not_boolean'
    return answer == 1
import time
from pathlib import Path


def run():
    import iris
    out = {'schema': 'pbp.cold.nonmoney/2', 'checks': [], 'fixture': 'pix-0006',
           'HTTP_exercised': False, 'model_inference': False, 'financial_effect': False}

    try:
        def check(name, condition):
            out['last_check_entered'] = name
            if not condition:
                raise AssertionError(name)
            out['checks'].append(name)

        def rows(sql, *args):
            out['last_sql'] = {'sql': sql, 'arguments': list(args), 'stage': 'original_exec_and_list'}
            result = list(iris.sql.exec(sql, *args))
            out['last_sql']['stage'] = 'returned_rows'
            return result

        def count(table):
            # Tables are literal internal constants, never input from the fixture.
            return int(rows('SELECT COUNT(*) FROM ' + table)[0][0])

        def obj(value):
            return json.loads(value if isinstance(value, str) else value._ToJSON())

        check('recorded_environment', str(iris.cls('pbp.Util').Env('PBP_LLM_MODE', '')) == 'recorded')
        check('no_provider_key', not iris.cls('pbp.Agent').HasKey())
        for table in ['pbp_Data."Case"', 'pbp_Data.Decision', 'pbp_Data.Seal',
                      'pbp_Data.Permit', 'pbp_Data.Receipt', 'EnsLib_Workflow.TaskResponse']:
            check('empty_before_' + table, count(table) == 0)
        prod = iris.cls('Ens.Config.Production')._OpenId('pbp.Production')
        enabled = {}
        for index in range(1, int(prod.Items.Count()) + 1):
            item = prod.Items.GetAt(index)
            enabled[str(item.Name)] = bool(item.Enabled)
        check('live_item_disabled', enabled.get('pbp.Operation.Agent') is False)
        check('replay_item_enabled', enabled.get('pbp.Operation.Replay') is True)
        check('no_staged_demo', not iris.cls('pbp.Demo.Runtime').Config())
        name = iris.ref('')
        check('production_running', bool(iris.cls('Ens.Director').IsProductionRunning(name))
              and str(name.value) == 'pbp.Production')
        payload = Path('/opt/pbp/fixtures/cases/pix-0006.json').read_text()
        original = json.loads(payload)
        check('fixed_fixture_identity', original['case_id'] == 'pix-0006')
        svc = iris.ref(None)
        sc = iris.cls('Ens.Director').CreateBusinessService('pbp.Service.Intake', svc)
        check('native_intake_created', bool(iris.cls('%SYSTEM.Status').IsOK(sc)))
        sc = svc.value.ProcessInput(iris.cls('Ens.StringContainer')._New(payload), iris.ref(None))
        check('native_intake_accepted', bool(iris.cls('%SYSTEM.Status').IsOK(sc)))
        deadline = time.monotonic() + 75
        case = None
        task_id = ''
        # Poll committed SQL scalars only: an in-process object can be cached.
        poll_count = 0
        stored = []
        while time.monotonic() < deadline:
            stored = rows('SELECT "Status", "HeadCommitment", "SessionId" '
                          'FROM pbp_Data."Case" WHERE "CaseId" = ?', 'pix-0006')
            poll_count += 1
            assert len(stored) <= 1, 'unexpected_duplicate_case_row'
            if stored:
                state, head, session_id = [str(v) for v in stored[0]]
                if state in {'blocked', 'closed', 'rejected', 'closed_no_effect'}:
                    raise AssertionError('unexpected_terminal_status:' + state)
                if state == 'awaiting_human' and head:
                    task_id = str(iris.cls('pbp.Review').FindTask(session_id))
                    if task_id:
                        break
            time.sleep(1)
        out['sql_poll_count'] = poll_count
        out['last_committed_state'] = [list(row) for row in stored]
        assert task_id, 'committed_case_and_task_not_ready'
        # Open once after SQL is ready. Refresh once and retain both views.
        case = iris.cls('pbp.Data.Case').Find('pix-0006')
        assert present(case, 'pbp.Data.Case'), 'case_reference_missing'
        before = {'status': str(case.Status), 'head': str(case.HeadCommitment)}
        reload_sc = case._Reload()
        assert iris.cls('%SYSTEM.Status').IsOK(reload_sc), 'case_reload_failed'
        after = {'status': str(case.Status), 'head': str(case.HeadCommitment)}
        out['object_refresh'] = {'before': before, 'after': after,
                                 'reloads': 1, 'changed': before != after}
        check('awaiting_human', present(case, 'pbp.Data.Case') and str(case.Status) == 'awaiting_human')
        check('one_pending_task', bool(task_id) and count('EnsLib_Workflow.TaskResponse') == 1)
        ds = rows('SELECT "Source", "Mode", "Action", "MovesMoney", "RequiresHuman", '
                  '"ModelProvider", "PromptTokens", "CompletionTokens", "CostMicroUSD" '
                  'FROM pbp_Data.Decision WHERE "CaseId" = ?', 'pix-0006')
        check('one_decision', len(ds) == 1)
        row = ds[0]
        check('recorded_decision_row', str(row[0]) == 'model' and str(row[1]) == 'recorded'
              and str(row[2]) == 'hold_for_evidence' and int(row[3]) == 0
              and int(row[4]) == 1 and str(row[5]) == 'replay'
              and all(int(v) == 0 for v in row[6:]))
        check('one_decision_seal', count('pbp_Data.Seal') == 1)
        seal = iris.cls('pbp.Data.Seal').Find(str(case.HeadCommitment))
        check('witness_nonmoney_path', present(seal, 'pbp.Data.Seal') and str(seal.Kind) == 'decision'
              and str(seal.Source) == 'witness' and not str(seal.LedgerState))
        verification = obj(seal.Verify())
        check('seal_intact', verification['ok'] is True)
        record = json.loads(str(seal.RecordJSON))
        check('sealed_recorded_model', record['model']['mode'] == 'recorded'
              and record['model']['provider'] == 'replay'
              and record['model']['id'] == 'fixtures/replay/decisions.json')
        check('sealed_nonmoney_action', record['decision']['action'] == 'hold_for_evidence'
              and record['decision']['moves_money'] is False
              and record['decision']['requires_human'] is True)
        check('declared_missing_signature', record['missing'].get('evidence.carrier_signature', 'absent') is None)
        check('five_sealed_readonly_tools', len(record['saw']['tools']) == 5
              and {t['name'] for t in record['saw']['tools']} ==
              {'GetOrder', 'GetPixEvents', 'GetPayerHistory', 'GetEvidence', 'GetStorePolicy'})
        check('no_RAG_retrieval', all('retrieval' not in t['output'] for t in record['saw']['tools']
                                   if t['name'] == 'GetStorePolicy'))
        check('five_tool_rows', int(rows('SELECT COUNT(*) FROM pbp_Data.ToolCall WHERE "CaseId" = ?', 'pix-0006')[0][0]) == 5)
        check('zero_permits', count('pbp_Data.Permit') == 0)
        check('zero_receipts', count('pbp_Data.Receipt') == 0)
        check('zero_agent_messages', int(rows('SELECT COUNT(*) FROM Ens.MessageHeader WHERE TargetConfigName = ?',
                                             'pbp.Operation.Agent')[0][0]) == 0)
        ledger = obj(iris.cls('ProofBeforePay.Ledger').Read(str(seal.Commitment)))
        check('ledger_not_staged', ledger['ok'] is False and ledger['reason'] == 'not_found')
        check('one_case_total', count('pbp_Data."Case"') == 1)
        # Paired diagnostic only, once after every business check has passed.
        observation = {'attempted': True, 'proxy_type': type(case).__name__,
                       'explicit_presence': present(case, 'pbp.Data.Case')}
        try:
            observation['returned'] = bool(case)
            observation['error'] = None
        except BaseException as proxy_error:
            observation['error'] = error_record(proxy_error)
        out['implicit_case_truthiness_observation'] = observation
        out.update(ok=True, status=str(case.Status), session_id=str(case.SessionId),
                   task_id=task_id, commitment=str(seal.Commitment), decision_action=record['decision']['action'],
                   mode=record['model']['mode'], provider=record['model']['provider'],
                   seal_verification=verification, permits=0, receipts=0, Agent_messages=0,
                   pending_review_not_completed=True, test_approval_performed=False)
        return json.dumps(out, sort_keys=True)

    except BaseException as error:
        out.update(ok=False, error=error_record(error))
        return json.dumps(out, ensure_ascii=True, sort_keys=True)
