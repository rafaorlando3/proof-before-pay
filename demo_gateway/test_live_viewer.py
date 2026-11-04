import json
from pathlib import Path
import unittest
import test_contract as contract_tests


class FakeLive:
    def __init__(self):
        self.calls = []
        self.case = "public-live:" + "a" * 16
        self.job = {"status": "complete", "scenario": "missing_evidence", "case_id": self.case,
                    "commitment": "d" * 64, "session_id": "123"}

    def status(self, token=None):
        self.calls.append(("status", token))
        return {"ok": True, "job": self.job} if token else {"ok": True, "available": False, "mode": "recorded", "reason": "live_disabled_or_expired", "scenarios": ["missing_evidence"]}

    def submit(self, body):
        self.calls.append(("submit", body))
        return {"ok": False, "mode": "recorded", "reason": "live_disabled_or_expired"}

    def completed_cases(self):
        return {self.case: self.job}


class LiveViewerTests(unittest.TestCase):
    setUp = contract_tests.Contract.setUp
    call = contract_tests.Contract.call

    def enable(self):
        self.live = FakeLive()
        self.g.live = self.live

    def test_live_auth_and_same_origin_guards_precede_admission(self):
        self.enable()
        body = b'{"scenario":"missing_evidence","request_id":"aaaaaaaaaaaaaaaa"}'
        self.assertEqual(self.call("POST", "/pbp/api/live", {}, body)[0], 401)
        self.assertEqual(self.call("POST", "/pbp/api/live", body=body)[0], 403)
        headers = {**self.headers, "Origin": self.c.origin, "Content-Type": "application/json", "X-PBP-Request": "1"}
        self.assertEqual(self.call("POST", "/pbp/api/live", headers, body)[0], 200)
        self.assertEqual(self.live.calls, [("submit", json.loads(body))])
        self.assertEqual(self.calls, [])
        for route in ("/pbp/api/cases", "/pbp/api/review/" + self.live.case):
            self.assertEqual(self.call("POST", route, headers, body)[0], 405)

    def test_no_live_configuration_is_explicit_recorded_fallback(self):
        status, _, raw = self.call("GET", "/pbp/api/live")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["mode"], "recorded")
        self.assertFalse(json.loads(raw)["available"])
        self.assertEqual(self.calls, [])

    def test_completed_live_case_requires_matching_mode_model_and_commitment(self):
        self.enable()
        native = self.g.fetch
        live_doc = {"ok": True, "case": {"case_id": self.live.case, "input": {"environment": "sandbox"}},
                    "decision": {"source": "model", "model": {"mode": "live"}}, "seals": [{"commitment": self.live.job["commitment"]}]}
        def fetch(path, method="GET", body=None):
            if self.live.case in path.replace("%3A", ":"):
                return 200, "application/json", json.dumps(live_doc).encode()
            return native(path, method, body)
        self.g.fetch = fetch
        self.assertEqual(self.call("GET", "/pbp/api/cases/" + self.live.case)[0], 200)
        live_doc["decision"]["model"]["mode"] = "recorded"
        self.assertEqual(self.call("GET", "/pbp/api/cases/" + self.live.case)[0], 502)
        live_doc["decision"]["model"]["mode"] = "live"
        live_doc["seals"][0]["commitment"] = "e" * 64
        self.assertEqual(self.call("GET", "/pbp/api/cases/" + self.live.case)[0], 502)
        self.assertEqual(self.call("GET", "/pbp/api/cases/public-live:" + "z" * 16)[0], 404)

    def test_panel_has_in_page_fallbacks_and_no_native_dialog_calls(self):
        self.enable()
        status, _, raw = self.call("GET", "/pbp/ui/")
        self.assertEqual(status, 200)
        for required in (b"pbp-live-result", b"role=\"status\"", b"Recorded mode", b"randomUUID", b"No request was replayed"):
            self.assertIn(required, raw)
        for forbidden in (b"alert(", b"confirm(", b"prompt("):
            self.assertNotIn(forbidden, raw)


if __name__ == "__main__":
    unittest.main()
