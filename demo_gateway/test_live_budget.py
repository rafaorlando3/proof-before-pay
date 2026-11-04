import copy
import datetime as dt
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from live_budget import BudgetDenied, LiveBudget, MODEL, PHASE


class LiveBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "budget.json"
        self.case = "public-live:" + "a" * 16
        self.now = dt.datetime(2026, 11, 3, 22, tzinfo=dt.timezone.utc).timestamp()
        self.state = {
            "schema": "pbp.inference-budget/1", "cap_usd": "1.00", "spent_usd": ".02",
            "estimated_spent_usd": ".32", "reserved": {"old-uncertain": ".114858"},
            "forwarded_calls": 203, "gemini_forwarded_calls": 196,
            "calls": [{"call_id": "historical", "phase": "historical", "opaque": {"keep": True}}],
            "estimated_settlement_policy": {"active": True, "approval_ref": "prior-test-approval"},
            "benchmark_v7_phase": {"enabled": False, "frozen": "unchanged"},
            "unrelated_history": [1, {"nested": "preserved"}],
            PHASE: {"schema": "pbp.public-live-budget/1", "enabled": True,
                    "approval_ref": "synthetic-test-only", "model": MODEL,
                    "expires_at": self.now + 86400 * 3, "active_case": self.case,
                    "case_http": {}, "day_http": {}, "in_flight": {}, "last_http_at": None},
        }
        self.save(self.state)
        (self.root / "budget.lock").touch(mode=0o600)
        self.budget = LiveBudget(self.root, clock=lambda: self.now)

    def save(self, data):
        self.path.write_text(json.dumps(data))
        self.path.chmod(0o600)

    def read(self):
        return json.loads(self.path.read_text())

    def body(self):
        return {"model": MODEL, "messages": [{"role": "user", "content": "Case id: " + self.case}],
                "tools": [{"type": "function", "function": {"name": "GetOrder", "parameters": {"type": "object"}}}],
                "temperature": 0}

    def settle(self, call, **overrides):
        args = {"status": 200, "data": {"model": MODEL, "usage": {"prompt_tokens": 500, "completion_tokens": 100, "total_tokens": 600}},
                "archive": {"call_id": call, "case_id": self.case, "sha256": "a" * 64, "http_status": 200}}
        args.update(overrides)
        return self.budget.settle(call, **args)

    def test_estimate_changes_only_own_hold_and_preserves_all_history(self):
        call, raw = self.budget.admit(self.body(), self.case)
        self.assertNotIn(b'"temperature"', raw)
        self.assertIn(call, self.read()["reserved"])
        self.assertTrue(self.settle(call))
        after = self.read()
        self.assertEqual(after["reserved"], self.state["reserved"])
        self.assertEqual(after["spent_usd"], self.state["spent_usd"])
        self.assertEqual(Decimal(after["estimated_spent_usd"]), Decimal(".32075000"))
        for key in ("unrelated_history", "benchmark_v7_phase"):
            self.assertEqual(after[key], self.state[key])
        self.assertEqual(after["calls"][0], self.state["calls"][0])
        self.assertFalse(after["calls"][-1]["billing_receipt_available"])
        before = self.path.read_bytes()
        with self.assertRaises(BudgetDenied):
            self.settle(call)
        self.assertEqual(before, self.path.read_bytes())

    def test_ambiguous_failure_keeps_both_holds_and_disables_only_public_phase(self):
        call, _ = self.budget.admit(self.body(), self.case)
        reserved = self.read()["reserved"]
        self.assertFalse(self.settle(call, status=404, data={"error": "not a receipt"}, archive=None))
        after = self.read()
        self.assertEqual(after["reserved"], reserved)
        self.assertEqual(after["estimated_spent_usd"], ".32")
        self.assertFalse(after[PHASE]["enabled"])
        self.assertEqual(after["benchmark_v7_phase"], self.state["benchmark_v7_phase"])
        self.now += 86400
        with self.assertRaisesRegex(BudgetDenied, "disabled"):
            self.budget.admit(self.body(), self.case)
        self.assertEqual(self.read()["reserved"], reserved)

    def test_crash_after_admission_never_retries_even_after_restart_and_new_day(self):
        call, _ = self.budget.admit(self.body(), self.case)
        before = self.path.read_bytes()
        self.now += 86400
        restarted = LiveBudget(self.root, clock=lambda: self.now)
        with self.assertRaisesRegex(BudgetDenied, "inflight"):
            restarted.admit(self.body(), self.case)
        self.assertEqual(before, self.path.read_bytes())
        self.assertIn(call, self.read()["reserved"])

    def test_concurrent_processes_reserve_exactly_one_attempt(self):
        request = json.dumps(self.body())
        code = ('import sys,json;from live_budget import LiveBudget,BudgetDenied;'
                'b=LiveBudget(sys.argv[1],clock=lambda:float(sys.argv[4]));'
                '\ntry:b.admit(json.loads(sys.argv[2]),sys.argv[3]);print("admitted")'
                '\nexcept BudgetDenied:print("denied")')
        processes = [subprocess.Popen([sys.executable, "-c", code, str(self.root), request, self.case, str(self.now)],
                     cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(8)]
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(stdout.strip())
        self.assertEqual(results.count("admitted"), 1)
        after = self.read()
        self.assertEqual(len(after["reserved"]), 2)
        self.assertEqual(after["forwarded_calls"], 204)

    def test_rate_case_cap_and_provider_day_cap_survive_restarts(self):
        for group in range(5):
            self.case = "public-live:" + str(group) * 16
            with self.budget.transaction() as state:
                state[PHASE]["active_case"] = self.case
            for _ in range(3):
                call, _ = self.budget.admit(self.body(), self.case)
                self.assertTrue(self.settle(call))
                with self.assertRaises(BudgetDenied):
                    self.budget.admit(self.body(), self.case)
                self.now += 15
            with self.assertRaisesRegex(BudgetDenied, "quota"):
                self.budget.admit(self.body(), self.case)
        self.case = "public-live:" + "z" * 16
        with self.budget.transaction() as state:
            state[PHASE]["active_case"] = self.case
        restarted = LiveBudget(self.root, clock=lambda: self.now)
        self.now = dt.datetime(2026, 11, 4, 0, 1, tzinfo=dt.timezone.utc).timestamp()
        with self.assertRaisesRegex(BudgetDenied, "quota"):
            restarted.admit(self.body(), self.case)
        self.now = dt.datetime(2026, 11, 4, 8, 1, tzinfo=dt.timezone.utc).timestamp()
        self.assertIsNotNone(restarted.admit(self.body(), self.case))

    def test_cap_cannot_expand_and_denied_requests_do_not_write(self):
        for change in ({"cap_usd": "5"}, {"estimated_spent_usd": ".8"}, {"estimated_settlement_policy": {"active": False}}):
            state = copy.deepcopy(self.state)
            state.update(change)
            self.save(state)
            before = self.path.read_bytes()
            with self.assertRaises(BudgetDenied):
                self.budget.admit(self.body(), self.case)
            self.assertEqual(before, self.path.read_bytes())

    def test_disabled_expired_missing_phase_and_partial_save_fail_closed(self):
        for key, value in (("enabled", False), ("expires_at", self.now - 1), ("active_case", "other")):
            state = copy.deepcopy(self.state)
            state[PHASE][key] = value
            self.save(state)
            with self.assertRaises(BudgetDenied):
                self.budget.admit(self.body(), self.case)
        self.save(self.state)
        partial = self.root / "budget-v7-interrupted.tmp"
        partial.write_text("reconcile, do not reset")
        with self.assertRaisesRegex(BudgetDenied, "partial"):
            self.budget.admit(self.body(), self.case)
        self.assertEqual(partial.read_text(), "reconcile, do not reset")

    def test_missing_or_symlinked_state_is_not_recreated_or_followed(self):
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.budget.admit(self.body(), self.case)
        self.assertFalse(self.path.exists())
        other = self.root / "other.json"
        other.write_text("untouched")
        self.path.symlink_to(other)
        with self.assertRaises(OSError):
            self.budget.admit(self.body(), self.case)
        self.assertEqual(other.read_text(), "untouched")

    def test_unsafe_provider_options_never_reserve(self):
        bodies = [dict(self.body(), stream=True), dict(self.body(), model="another"),
                  dict(self.body(), max_tokens=99999), dict(self.body(), plugins=[]),
                  dict(self.body(), tools=[{"type": "web_search"}]),
                  dict(self.body(), tools=[{"type": "function", "function": {"name": "SendPayment"}}])]
        before = self.path.read_bytes()
        for body in bodies:
            with self.assertRaises(BudgetDenied):
                self.budget.admit(body, self.case)
        self.assertEqual(self.path.read_bytes(), before)

    def test_success_without_archived_matching_model_usage_retains_reserve(self):
        for bad in (dict(archive=None), dict(data={"model": "another", "usage": {"prompt_tokens": 500, "completion_tokens": 100}}),
                    dict(data={"model": MODEL, "usage": {"prompt_tokens": True, "completion_tokens": 100}})):
            self.save(copy.deepcopy(self.state))
            call, _ = self.budget.admit(self.body(), self.case)
            self.assertFalse(self.settle(call, **bad))
            self.assertIn(call, self.read()["reserved"])
            self.assertEqual(self.read()["estimated_spent_usd"], ".32")

    def test_corrupt_count_cannot_reset_quota_or_historical_holds(self):
        call, _ = self.budget.admit(self.body(), self.case)
        self.settle(call)
        state = self.read()
        state[PHASE]["case_http"] = {}
        self.save(state)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(BudgetDenied, "count_mismatch"):
            self.budget.admit(self.body(), self.case)
        self.assertEqual(before, self.path.read_bytes())

    def test_status_reserves_worst_allowed_request_instead_of_fixed_point35(self):
        state = copy.deepcopy(self.state)
        state[PHASE]["active_case"] = None
        state["estimated_spent_usd"] = ".50"
        self.save(state)
        # Accounted .634858 leaves .365142: more than .35, less than .384064.
        self.assertEqual(self.budget.public_status()["reason"], "cumulative_budget_headroom_required")
        state["estimated_spent_usd"] = ".48"
        self.save(state)
        self.assertTrue(self.budget.public_status()["available"])

    def test_no_http_finish_identifies_no_provider_request_and_preserves_holds(self):
        state = copy.deepcopy(self.state)
        state["estimated_spent_usd"] = ".7"
        self.save(state)
        with self.assertRaisesRegex(BudgetDenied, "headroom"):
            self.budget.admit(self.body(), self.case)
        self.assertFalse(self.budget.finish_case(self.case, False))
        after = self.read()
        self.assertFalse(after[PHASE]["enabled"])
        self.assertIsNone(after[PHASE]["active_case"])
        self.assertEqual(after[PHASE]["stop_reason"], "native_result_not_qualified_no_provider_request")
        self.assertEqual(after["reserved"], state["reserved"])
        self.assertEqual(after["calls"], state["calls"])
        self.assertEqual(after["forwarded_calls"], state["forwarded_calls"])

    def test_finish_case_without_http_does_not_reenable_disabled_phase(self):
        state = copy.deepcopy(self.state)
        state[PHASE]["enabled"] = False
        state[PHASE]["stop_reason"] = "preserved_operator_stop"
        self.save(state)
        self.assertFalse(self.budget.finish_case(self.case, False))
        self.assertFalse(self.read()[PHASE]["enabled"])
        self.assertEqual(self.read()[PHASE]["stop_reason"], "native_result_not_qualified_no_provider_request")

    def test_uncertain_inflight_finish_stays_disabled_with_case_and_hold(self):
        call, _ = self.budget.admit(self.body(), self.case)
        self.assertFalse(self.budget.finish_case(self.case, False))
        after = self.read()
        self.assertFalse(after[PHASE]["enabled"])
        self.assertEqual(after[PHASE]["active_case"], self.case)
        self.assertIn(call, after["reserved"])


if __name__ == "__main__":
    unittest.main()
