"""Runs inside IRIS embedded Python. Calls ObjectScript, which calls Python again."""
import copy
import json
import sys
from pathlib import Path

def run():
    import iris
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'tests'))
    from s0_fixtures import decision
    cls = iris.cls('ProofBeforePay.Witness')
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    r = decision()
    a = json.loads(cls.Seal(json.dumps(r)))
    check('seal_bridge_succeeds', a['ok'] is True)
    check('fresh_salt', len(bytes.fromhex(a['salt'])) == 32)
    check('local_seal_pending', a['state'] == 'pending' and a['on_chain_verified'] is False)
    check('no_payment_authority', a['authorizes_payment'] is False and a['money_order_verified'] is False)
    env = {'record': r, 'salt': a['salt'], 'commitment': a['commitment']}
    v = json.loads(cls.VerifyLocal(json.dumps(env)))
    check('verify_bridge_succeeds', v['ok'] is True and v['state'] == 'pending')
    check('no_salt_in_verify_reply', 'salt' not in v)
    edited = copy.deepcopy(env)
    edited['record']['decision']['rationale'] = 'Changed after sealing; synthetic test.'
    v = json.loads(cls.VerifyLocal(json.dumps(edited)))
    check('tamper_detected', v['ok'] is False and v['state'] == 'tampered')
    bad = copy.deepcopy(r)
    bad['saw']['inputs']['private@example.invalid'] = 'synthetic'
    v = json.loads(cls.Seal(json.dumps(bad)))
    check('pii_key_redacted', not v['ok'] and v['reason'] == 'personal_data_found' and 'private@example.invalid' not in json.dumps(v))
    bad = copy.deepcopy(r)
    bad['decision']['requires_human'] = False
    v = json.loads(cls.Seal(json.dumps(bad)))
    check('human_boundary', not v['ok'] and v['reason'] == 'money_above_limit_without_human')
    v = json.loads(cls.Seal('{"prev":null,"prev":null}'))
    check('duplicate_key', not v['ok'] and v['reason'] == 'duplicate_field')
    v = json.loads(cls.Seal(' ' * 32769))
    check('input_bound', not v['ok'] and v['reason'] == 'input_too_large')
    # Force the actual ObjectScript Catch path without changing installed modules.
    import pbp_witness.adapter as adapter
    original = adapter.seal_json
    try:
        def unavailable(_):
            raise RuntimeError('synthetic-private@example.invalid')
        adapter.seal_json = unavailable
        raw = cls.Seal('{}')
        v = json.loads(raw)
        check('bridge_failure_closed', v['reason'] == 'bridge_unavailable' and v['state'] == 'unverifiable' and 'synthetic-private' not in raw)
    finally:
        adapter.seal_json = original
    return json.dumps({'schema': 'pbp.iris.smoke/1', 'ok': True, 'checks': checks, 'count': len(checks), 'IRIS_version': str(iris.cls("%SYSTEM.Version").GetVersion()), 'LLM_calls': 0, 'financial_effect': False}, sort_keys=True)
