import json
from pathlib import Path
import threading
import unittest
import urllib.error
import urllib.request

from live_budget import BudgetDenied, MODEL, PHASE
from live_provider import LOCAL_TOKEN, NoRedirect, PrivateProvider, create_server
import test_live_budget as budget_tests


class LiveProviderTests(unittest.TestCase):
    setUp = budget_tests.LiveBudgetTests.setUp
    save = budget_tests.LiveBudgetTests.save
    read = budget_tests.LiveBudgetTests.read
    body = budget_tests.LiveBudgetTests.body

    def provider(self, send):
        return PrivateProvider(self.budget, "not-a-real-key-test-only-" + "x" * 32,
                               send=send, wait=lambda seconds: setattr(self, "now", self.now + seconds))

    def response(self):
        return 200, json.dumps({"model": MODEL, "usage": {"prompt_tokens": 500, "completion_tokens": 100},
                               "choices": [{"message": {"role": "assistant", "content": "synthetic test"}}]}).encode()

    def test_HTTP_admission_is_durable_before_send_and_archived_before_settlement(self):
        calls = []
        def send(raw):
            state = self.read()
            self.assertEqual(len(state[PHASE]["in_flight"]), 1)
            self.assertEqual(len(state["reserved"]), 2)
            calls.append(raw)
            return self.response()
        provider = self.provider(send)
        status, body = provider.complete(self.body())
        self.assertEqual(status, 200)
        self.assertEqual(len(calls), 1)
        entry = self.read()["calls"][-1]
        archive = self.root / entry["response_archive"]["path"]
        self.assertEqual(archive.read_bytes(), body)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.read()["reserved"], self.state["reserved"])
        self.assertNotIn(provider.key.encode(), archive.read_bytes())

    def test_pacing_is_before_second_admission_and_not_a_provider_retry(self):
        calls = []
        def send(raw):
            calls.append(self.now)
            return self.response()
        provider = self.provider(send)
        self.assertEqual(provider.complete(self.body())[0], 200)
        self.assertEqual(provider.complete(self.body())[0], 200)
        self.assertEqual(calls[1] - calls[0], 15)
        self.assertEqual(self.read()["forwarded_calls"], 205)

    def test_slow_admission_persistence_does_not_shorten_actual_start_interval(self):
        original = self.budget.admit
        first = True
        def delayed_admit(*args):
            nonlocal first
            result = original(*args)
            if first:
                self.now += 20
                first = False
            return result
        self.budget.admit = delayed_admit
        starts = []
        def send(raw):
            starts.append(self.now)
            return self.response()
        provider = self.provider(send)
        self.assertEqual(provider.complete(self.body())[0], 200)
        self.assertEqual(provider.complete(self.body())[0], 200)
        self.assertGreaterEqual(starts[1] - starts[0], 15)

    def test_timeout_or_invalid_JSON_keeps_reserve_without_secret_exception_or_retry(self):
        for problem in ("timeout", "invalid"):
            self.save(self.state)
            calls = []
            def send(raw):
                calls.append(1)
                if problem == "timeout":
                    raise TimeoutError("not-a-real-key-test-only-" + "x" * 32)
                return 200, b"invalid JSON"
            provider = self.provider(send)
            status, body = provider.complete(self.body())
            self.assertEqual(status, 502)
            self.assertNotIn(provider.key.encode(), body)
            self.assertFalse(self.read()[PHASE]["enabled"])
            self.assertEqual(len(self.read()["reserved"]), 2)
            self.assertNotEqual(provider.complete(self.body())[0], 200)
            self.assertEqual(len(calls), 1)

    def test_provider_secret_echo_is_never_archived_or_forwarded(self):
        provider = self.provider(lambda raw: (200, b'{}'))
        provider.send = lambda raw: (200, provider.key.encode())
        status, body = provider.complete(self.body())
        self.assertEqual(status, 502)
        self.assertNotIn(provider.key.encode(), body)
        self.assertEqual(list(provider.archive.iterdir()), [])
        self.assertEqual(len(self.read()["reserved"]), 2)

    def test_process_interruption_keeps_inflight_attempt_for_reconciliation(self):
        def send(raw):
            raise KeyboardInterrupt()
        provider = self.provider(send)
        with self.assertRaises(KeyboardInterrupt):
            provider.complete(self.body())
        state = self.read()
        self.assertEqual(len(state[PHASE]["in_flight"]), 1)
        calls = []
        provider.send = lambda raw: calls.append(raw)
        self.assertNotEqual(provider.complete(self.body())[0], 200)
        self.assertEqual(calls, [])

    def test_disabled_phase_and_unapproved_options_never_reach_transport(self):
        calls = []
        provider = self.provider(lambda raw: calls.append(raw))
        before = self.path.read_bytes()
        self.assertNotEqual(provider.complete(dict(self.body(), model="another"))[0], 200)
        self.assertEqual(before, self.path.read_bytes())
        state = self.read()
        state[PHASE]["enabled"] = False
        self.save(state)
        self.assertNotEqual(provider.complete(self.body())[0], 200)
        self.assertEqual(calls, [])

    def test_local_HTTP_peer_path_auth_and_JSON_guards(self):
        credential = self.root / "test-provider-key"
        credential.write_text("not-a-real-key-test-only-" + "x" * 32)
        credential.chmod(0o600)
        sent = []
        def send(raw):
            sent.append(raw)
            return self.response()
        server = create_server(self.root, credential, "127.0.0.1", 0, ["127.0.0.1"], send=send)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:" + str(server.server_address[1])
            before = self.path.read_bytes()
            for route in ("/v1/models", "/v1/models/" + MODEL):
                with urllib.request.urlopen(base + route, timeout=3) as reply:
                    metadata = json.load(reply)
                    model = metadata["data"][0] if "data" in metadata else metadata
                    self.assertEqual(model["id"], MODEL)
                    self.assertEqual(model["owned_by"], "local-allowlist-not-provider-observation")
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(sent, [])
            for route, headers in (("/chat/completions", {}), ("/wrong", {"Authorization": "Bearer " + LOCAL_TOKEN})):
                request = urllib.request.Request(base + route, data=json.dumps(self.body()).encode(), headers=headers)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(error.exception.code, 403)
                self.assertNotIn("WWW-Authenticate", error.exception.headers)
                error.exception.close()
            self.assertEqual(sent, [])
            request = urllib.request.Request(base + "/chat/completions", data=json.dumps(self.body()).encode(),
                      headers={"Authorization": "Bearer " + LOCAL_TOKEN, "Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=3) as reply:
                self.assertEqual(reply.status, 200)
            self.assertEqual(len(sent), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_wildcard_public_bind_and_provider_redirect_are_denied(self):
        with self.assertRaisesRegex(BudgetDenied, "private_bind"):
            create_server(self.root, self.root / "absent", "0.0.0.0", 0, ["127.0.0.1"])
        with self.assertRaisesRegex(BudgetDenied, "redirect"):
            NoRedirect().redirect_request(None, None, None, None, None)


if __name__ == "__main__":
    unittest.main()
