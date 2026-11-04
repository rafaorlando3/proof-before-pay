import copy
import json
from pathlib import Path
import tempfile
import unittest

from live_budget import BudgetDenied, MODEL
from live_native import FIXTURES, NativeRelay, NativeRunner


class Relay:
    def __init__(self, ready=True):
        self.is_ready = ready
        self.submissions = []
        self.document = None
        self.ambiguous = False

    def ready(self):
        return self.is_ready

    def lookup(self, case_id):
        return self.document if self.submissions else None

    def submit(self, payload):
        self.submissions.append(payload)
        if self.ambiguous:
            raise TimeoutError("an intake might already exist")
        return {"ok": True, "case_id": payload["case_id"], "status": "received"}


class NativeRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixtures = Path(__file__).resolve().parents[1] / "fixtures/cases"
        self.token = "a" * 32
        self.case = "public-live:" + self.token
        self.now = 1000.0
        self.relay = Relay()
        self.runner = NativeRunner(self.fixtures, self.tmp.name, self.relay, timeout=2,
                                   clock=lambda: self.now, wait=lambda seconds: setattr(self, "now", self.now + seconds))

    def document(self):
        return {"ok": True, "case": {"case_id": self.case, "input": {"environment": "sandbox"},
                                     "session_id": "1499", "status": "awaiting_human"},
                "decision": {"source": "model", "moves_money": False, "model": {"mode": "live", "id": MODEL}, "commitment": "a" * 64,
                             "proposal_refused":False,"proposal_reason":"","proposal":{"action":"hold_for_evidence"},"usage":{"tool_calls":5}},
                "seals": [{"kind": "decision", "commitment": "a" * 64, "verification": {"state": "intact"}, "money_moved_before_seal": False}],
                "receipt": None, "permit": None}

    def test_fixture_is_pinned_and_only_identifiers_change_not_data_history(self):
        before = (self.fixtures / "pix-0005.json").read_bytes()
        payload, name, digest = self.runner.payload("amount_conflict", self.token)
        original = json.loads(before)
        self.assertEqual(payload["case_id"], self.case)
        self.assertEqual(payload["order"]["amount_minor"], original["order"]["amount_minor"])
        self.assertEqual(payload["order"]["created_at"], original["order"]["created_at"])
        self.assertNotEqual(payload["payments"][0]["payment_ref"], original["payments"][0]["payment_ref"])
        self.assertEqual(payload["evidence"], original["evidence"])
        self.assertEqual((self.fixtures / name).read_bytes(), before)
        altered = Path(self.tmp.name) / "fixtures"
        altered.mkdir()
        (altered / name).write_bytes(before + b"\n")
        self.runner.fixtures = altered
        with self.assertRaisesRegex(BudgetDenied, "revision_changed"):
            self.runner.payload("amount_conflict", self.token)

    def test_one_native_intake_and_intact_live_seal_with_actual_session(self):
        self.relay.document = self.document()
        result = self.runner("missing_evidence", self.token)
        self.assertEqual(result, {"mode": "live", "case_id": self.case, "commitment": "a" * 64, "session_id": "1499"})
        self.assertEqual(len(self.relay.submissions), 1)
        marker = Path(self.tmp.name) / (self.token + ".json")
        self.assertEqual(json.loads(marker.read_text())["state"], "sealed_live_result_observed")
        self.assertEqual(marker.stat().st_mode & 0o777, 0o600)

    def test_ambiguous_intake_keeps_durable_intent_and_never_resubmits(self):
        self.relay.ambiguous = True
        with self.assertRaises(TimeoutError):
            self.runner("missing_evidence", self.token)
        marker = Path(self.tmp.name) / (self.token + ".json")
        before = marker.read_bytes()
        self.relay.ambiguous = False
        with self.assertRaises(FileExistsError):
            self.runner("missing_evidence", self.token)
        self.assertEqual(len(self.relay.submissions), 1)
        self.assertEqual(marker.read_bytes(), before)

    def test_unready_route_and_arbitrary_scenarios_never_submit(self):
        self.relay.is_ready = False
        with self.assertRaisesRegex(BudgetDenied, "not_ready"):
            self.runner("missing_evidence", self.token)
        with self.assertRaises(BudgetDenied):
            self.runner("a customer supplied prompt", self.token)
        self.assertEqual(self.relay.submissions, [])
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_no_seal_or_tampered_seal_times_out_without_retry(self):
        self.relay.document = self.document()
        self.relay.document["seals"][0]["verification"]["state"] = "tampered"
        with self.assertRaisesRegex(ValueError, "unconfirmed"):
            self.runner("missing_evidence", self.token)
        self.assertEqual(len(self.relay.submissions), 1)
        self.assertEqual(json.loads((Path(self.tmp.name) / (self.token + ".json")).read_text())["state"], "submission_attempt_recorded")

    def test_recorded_rules_and_financial_results_cannot_be_claimed_live(self):
        changes = [lambda d: d["decision"]["model"].update(mode="recorded"),
                   lambda d: d["decision"].update(source="rules"),
                   lambda d: d["decision"].update(proposal_refused=True,proposal_reason="llm_call_failed"),
                   lambda d: d["decision"]["usage"].update(tool_calls=0),
                   lambda d: d["decision"].update(moves_money=True),
                   lambda d: d.update(receipt={"status": "effected"}),
                   lambda d: d.update(permit={"state": "issued"})]
        for change in changes:
            data = self.document()
            change(data)
            with self.assertRaises(BudgetDenied):
                self.runner.sealed_result(data, self.case)

    def test_readiness_requires_pinned_revision_private_route_and_no_autonomous_effects(self):
        relay = NativeRelay(expected_revision="a" * 40)
        health = {"ok": True, "production_running": True, "public_live_demo": {
                  "enabled": True, "model": MODEL, "case_prefix": "public-live:", "transport": "private_budget_bridge",
                  "autonomous_effects": False, "source_revision": "a" * 40}}
        relay.request = lambda path: health
        self.assertTrue(relay.ready())
        health["public_live_demo"]["source_revision"] = "b" * 40
        self.assertFalse(relay.ready())
        health["public_live_demo"]["source_revision"] = "a" * 40
        health["public_live_demo"]["autonomous_effects"] = True
        self.assertFalse(relay.ready())
        with self.assertRaises(BudgetDenied):
            NativeRelay("https://an-external-backend.example", expected_revision="a" * 40)


if __name__ == "__main__":
    unittest.main()
