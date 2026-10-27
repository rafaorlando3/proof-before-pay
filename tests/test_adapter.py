import copy
import io
import json
import re
import unittest
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from pbp_witness import adapter
from pbp_s0_core.record import commitment
from s0_fixtures import decision

class AdapterTests(unittest.TestCase):
    def test_unknown_temperature_sentinel_keeps_frozen_schema(self):
        r = decision()
        r['model']['temperature'] = -1
        sealed = self.seal(r)
        self.assertTrue(sealed['ok'])
        env = {'record': r, 'salt': sealed['salt'], 'commitment': sealed['commitment']}
        self.assertTrue(json.loads(adapter.verify_local_json(json.dumps(env)))['ok'])

    def seal(self, record=None):
        return json.loads(adapter.seal_json(json.dumps(decision() if record is None else record)))

    def envelope(self):
        r = decision()
        value = self.seal(r)
        return {'record':r, 'salt':value['salt'], 'commitment':value['commitment']}

    def assert_public_error(self, result, secret='synthetic-private@example.invalid'):
        self.assertFalse(result['ok'])
        self.assertEqual(set(result), {'schema','spec','mode','ok','state','reason','on_chain_verified','authorizes_payment','money_order_verified'})
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn('path', result)
        self.assertNotIn('findings', result)
        self.assertEqual(result['state'], 'unverifiable')

    def test_generated_salt_is_32_random_bytes_and_matches_s0(self):
        r = decision(); a = self.seal(r); b = self.seal(r)
        self.assertEqual(len(bytes.fromhex(a['salt'])), 32)
        self.assertRegex(a['salt'], r'\A[0-9a-f]{64}\Z')
        self.assertNotEqual(a['salt'], b['salt'])
        self.assertEqual(a['commitment'], commitment(r, a['salt']))
        self.assertEqual(a['memo'], 'pbp1:' + a['commitment'])

    def test_success_is_local_pending_without_payment_or_chain_claim(self):
        a = self.seal()
        self.assertTrue(a['ok']); self.assertEqual(a['state'], 'pending')
        self.assertEqual(a['reason'], 'local_only_not_anchored')
        for k in ('on_chain_verified','authorizes_payment','money_order_verified'):
            self.assertIs(a[k], False)
        self.assertNotIn('record', a)

    def test_local_match_remains_pending(self):
        a = json.loads(adapter.verify_local_json(json.dumps(self.envelope())))
        self.assertTrue(a['ok']); self.assertEqual(a['state'], 'pending')
        self.assertEqual(a['reason'], 'local_match_not_anchored')
        self.assertNotIn('salt', a)

    def test_fraud_changes_record_without_resealing(self):
        e = self.envelope(); e['record']['decision']['rationale'] = 'Edited synthetic decision after the commitment.'
        a = json.loads(adapter.verify_local_json(json.dumps(e)))
        self.assertFalse(a['ok']); self.assertEqual(a['reason'], 'commitment_mismatch')

    def test_pii_value_is_not_returned(self):
        r = decision(); r['saw']['inputs']['note'] = 'synthetic-private@example.invalid'
        a = self.seal(r); self.assert_public_error(a)
        self.assertEqual(a['reason'], 'personal_data_found')

    def test_pii_in_key_does_not_leak_through_path(self):
        r = decision(); r['saw']['inputs']['synthetic-private@example.invalid'] = 'fixture'
        self.assert_public_error(self.seal(r))

    def test_unknown_key_does_not_leak_through_validation_error(self):
        r = decision(); r['synthetic-private@example.invalid'] = 'fixture'
        a = self.seal(r); self.assert_public_error(a); self.assertEqual(a['reason'], 'unknown_field')

    def test_duplicate_key_error_does_not_include_key(self):
        raw = '{"synthetic-private@example.invalid":1,"synthetic-private@example.invalid":2}'
        a = json.loads(adapter.seal_json(raw)); self.assert_public_error(a)
        self.assertEqual(a['reason'], 'duplicate_field')

    def test_duplicate_record_fields_rejected(self):
        raw = json.dumps(decision()); raw = raw[:-1] + ',"prev":null}'
        self.assertEqual(json.loads(adapter.seal_json(raw))['reason'], 'duplicate_field')

    def test_json_bounds_and_nonfinite(self):
        for raw, reason in [(b'{}','json_string_required'), ('[]','json_object_required'), ('x','invalid_json'), ('{"x":NaN}','nonfinite_json'), (' ' * 32769,'input_too_large')]:
            with self.subTest(reason=reason):
                a = json.loads(adapter.seal_json(raw)); self.assert_public_error(a)
                self.assertEqual(a['reason'], reason)

    def test_depth_bound(self):
        value = {}
        for _ in range(22): value = {'x':value}
        self.assertEqual(json.loads(adapter.seal_json(json.dumps(value)))['reason'], 'input_too_deep')

    def test_external_salt_requires_exact_64_lower_hex(self):
        base = self.envelope()
        for salt in [base['salt']+'\n', '', 'A'*64, 'g'*64, 7, None, '1'*63, '1'*65]:
            with self.subTest(salt_type=type(salt).__name__):
                value = copy.deepcopy(base); value['salt'] = salt
                a = json.loads(adapter.verify_local_json(json.dumps(value)))
                self.assert_public_error(a); self.assertEqual(a['reason'], 'bad_salt')

    def test_anchor_fields_cannot_forge_on_chain_claim(self):
        value = self.envelope(); value['anchor'] = {'memo':'synthetic'}
        a = json.loads(adapter.verify_local_json(json.dumps(value)))
        self.assert_public_error(a); self.assertEqual(a['reason'], 'envelope_fields')

    def test_human_boundary_preserved(self):
        r = decision(); r['decision']['requires_human'] = False
        a = self.seal(r); self.assert_public_error(a)
        self.assertEqual(a['reason'], 'money_above_limit_without_human')

    def test_unexpected_exception_is_generic_and_silent(self):
        stdout=io.StringIO(); stderr=io.StringIO()
        with patch.object(adapter, 'seal', side_effect=RuntimeError('synthetic-private@example.invalid')):
            with redirect_stdout(stdout), redirect_stderr(stderr): a=self.seal()
        self.assert_public_error(a); self.assertEqual(a['reason'],'internal_error')
        self.assertEqual(stdout.getvalue(),''); self.assertEqual(stderr.getvalue(),'')

    def test_historical_s0_devnet_fixture_is_offline_only(self):
        path = Path(__file__).resolve().parents[1] / 'fixtures/S0-devnet-proof-1.json'
        if not path.exists(): self.skipTest('optional_public_historical_fixture_absent')
        proof = json.loads(path.read_bytes())
        self.assertTrue(proof['ok'])
        anchor = next(step for step in proof['steps'] if step['step']=='anchor')
        self.assertEqual(anchor['slot'],510848536)
        self.assertEqual(anchor['memo'],'pbp1:'+proof['commitment'])
        envelope = {k:proof[k]for k in ('record','salt','commitment')}
        a = json.loads(adapter.verify_local_json(json.dumps(envelope)))
        self.assertTrue(a['ok']);self.assertEqual(a['state'],'pending')
        self.assertIs(a['on_chain_verified'],False)
        envelope['record']['decision']['rationale'] = 'Historical synthetic record edited offline.'
        self.assertEqual(json.loads(adapter.verify_local_json(json.dumps(envelope)))['reason'],'commitment_mismatch')
