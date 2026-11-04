import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from pbp_solana_demo.adapter import anchor, anchor_json, DEVNET, MEMO_PROGRAM

COMMIT = 'a' * 64
SIGNATURE = 'A' * 88

class SolanaDemoTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.key = self.root / 'key.json'
        self.key.write_text(json.dumps([7] * 64))
        self.key.chmod(0o600)
        self.calls = []
        self.confirmed = True
        self.timeout = False
        self.wrong_memo = False

    def build(self, key, memo, blockhash):
        self.assertEqual(key, self.key.read_bytes())
        self.assertEqual(memo, 'pbp1:' + COMMIT)
        return 'synthetic-signed-transaction', SIGNATURE

    def rpc(self, method, params):
        self.calls.append(method)
        if method == 'getLatestBlockhash':
            return {'value': {'blockhash': 'synthetic-test-only'}}
        if method == 'sendTransaction':
            # Durable expected signature and only Memo commitment BEFORE send.
            state = json.loads((self.root / (COMMIT + '.json')).read_text())
            self.assertEqual(state['signature'], SIGNATURE)
            self.assertEqual(state['state'], 'prepared')
            self.assertEqual(params[1]['maxRetries'], 0)
            self.assertFalse(params[1]['skipPreflight'])
            if self.timeout:
                raise TimeoutError('private provider message must not escape')
            return SIGNATURE
        if method == 'getTransaction':
            if not self.confirmed:
                return None
            return {'slot': 123, 'meta': {'err': None}, 'transaction': {'signatures': [SIGNATURE], 'message': {'instructions': [
                {'programId': MEMO_PROGRAM, 'parsed': 'wrong' if self.wrong_memo else 'pbp1:' + COMMIT}
            ]}}}
        self.fail('Unexpected RPC: ' + method)

    def run_anchor(self):
        return anchor(COMMIT, self.key, self.root, True, rpc=self.rpc, build=self.build, polls=1)

    def test_default_disabled_does_not_read_key_state_or_contact_network(self):
        reply = anchor_json('bad', '/absent/key', '/absent/state')
        self.assertEqual(json.loads(reply)['state'], 'disabled')
        self.assertEqual(self.calls, [])

    def test_one_send_confirmed_by_exact_memo_readback(self):
        result = self.run_anchor()
        self.assertTrue(result['ok'])
        self.assertTrue(result['on_chain_verified'])
        self.assertFalse(result['authorizes_payment'])
        self.assertIn('?cluster=devnet', result['explorer'])
        self.assertEqual(self.calls.count('sendTransaction'), 1)
        state = (self.root / (COMMIT + '.json')).read_text()
        self.assertNotIn(self.key.read_text(), state)
        self.assertNotIn('synthetic-signed-transaction', state)
        self.assertEqual(json.loads(state)['cluster_url'], DEVNET)

    def test_uncertain_send_reconciles_expected_signature_without_resending(self):
        self.timeout, self.confirmed = True, False
        first = self.run_anchor()
        self.assertFalse(first['ok'])
        self.assertEqual(first['state'], 'uncertain')
        self.timeout, self.confirmed = False, True
        second = self.run_anchor()
        self.assertTrue(second['ok'])
        self.assertEqual(self.calls.count('sendTransaction'), 1)
        self.assertEqual(self.calls.count('getLatestBlockhash'), 1)

    def test_wrong_memo_never_counts_as_verified(self):
        self.wrong_memo = True
        self.assertFalse(self.run_anchor()['ok'])
        self.assertFalse(self.run_anchor()['ok'])
        self.assertEqual(self.calls.count('sendTransaction'), 1)

    def test_readback_from_another_signature_is_not_confirmation(self):
        original = self.rpc
        def wrong_signature(method, params):
            result = original(method, params)
            if method == 'getTransaction': result['transaction']['signatures'] = ['B' * 88]
            return result
        result = anchor(COMMIT, self.key, self.root, True, rpc=wrong_signature, build=self.build, polls=1)
        self.assertFalse(result['ok'])
        self.assertEqual(self.calls.count('sendTransaction'), 1)

    def test_two_callers_share_one_durable_intent_and_send(self):
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.run_anchor())) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result['ok'] for result in results))
        self.assertEqual(self.calls.count('sendTransaction'), 1)

    def test_corrupt_intent_is_preserved_without_new_send(self):
        path = self.root / (COMMIT + '.json')
        path.write_text('{}');path.chmod(0o600)
        with self.assertRaises(ValueError): self.run_anchor()
        self.assertEqual(path.read_text(), '{}')
        self.assertEqual(self.calls, [])

    def test_public_key_file_and_symlink_state_are_refused(self):
        self.key.chmod(0o644)
        with self.assertRaises(ValueError): self.run_anchor()
        self.assertEqual(self.calls, [])
        link = self.root / 'link';link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): anchor(COMMIT, self.key, link, True, rpc=self.rpc, build=self.build)
        self.assertEqual(self.calls, [])

if __name__ == '__main__': unittest.main()
