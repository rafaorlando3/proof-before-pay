import copy
import datetime as dt
from decimal import Decimal
import json
import hashlib
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from live_budget import BudgetDenied, LiveBudget, MODEL, PHASE, CAP_APPROVAL_REF, LEGACY_MODEL, RESPONSE_MODEL_IDS


class LiveBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "budget.json"
        self.case = "public-live:" + "a" * 16
        self.now = dt.datetime(2026, 11, 3, 22, tzinfo=dt.timezone.utc).timestamp()
        self.state = {
            "schema": "pbp.inference-budget/1", "cap_usd": "5.00", "spent_usd": ".02",
            "estimated_spent_usd": ".32", "reserved": {"old-uncertain": ".114858"},
            "forwarded_calls": 203, "gemini_forwarded_calls": 196,
            "calls": [{"call_id": "historical", "phase": "historical", "opaque": {"keep": True}}],
            "estimated_settlement_policy": {"active": True, "approval_ref": "prior-test-approval"},
            "benchmark_v7_phase": {"enabled": False, "frozen": "unchanged"},
            "unrelated_history": [1, {"nested": "preserved"}],
            PHASE: {"schema": "pbp.public-live-budget/1", "enabled": True,
                    "cap_approval_ref": CAP_APPROVAL_REF,
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
        for change in ({"cap_usd": "10"}, {"cap_usd": "2"}, {"cap_usd": "1"}, {"estimated_spent_usd": "4.8"}, {"estimated_settlement_policy": {"active": False}}):
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
        state["estimated_spent_usd"] = "4.50"
        self.save(state)
        # Accounted 4.634858 leaves .365142: more than .35, less than .384064.
        self.assertEqual(self.budget.public_status()["reason"], "cumulative_budget_headroom_required")
        state["estimated_spent_usd"] = "4.48"
        self.save(state)
        self.assertTrue(self.budget.public_status()["available"])

    def test_no_http_finish_identifies_no_provider_request_and_preserves_holds(self):
        state = copy.deepcopy(self.state)
        state["estimated_spent_usd"] = "4.7"
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

    def test_two_dollar_cap_needs_explicit_persisted_approval_reference(self):
        state = copy.deepcopy(self.state)
        del state[PHASE]["cap_approval_ref"]
        self.save(state)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(BudgetDenied, "approval_reference"):
            self.budget.admit(self.body(), self.case)
        self.assertEqual(self.path.read_bytes(), before)


    def test_old_model_is_not_an_automatic_fallback_or_new_request(self):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(BudgetDenied, "model_or_stream_denied"):
            self.budget.admit(dict(self.body(), model="gemini-3.8-flash"), self.case)
        self.assertEqual(before, self.path.read_bytes())

    def test_new_model_admission_keeps_original_model_history_and_holds(self):
        state = self.read()
        state["calls"][0]["requested_model"] = "gemini-3.8-flash"
        self.save(state)
        call, _ = self.budget.admit(self.body(), self.case)
        after = self.read()
        self.assertEqual(after["calls"], state["calls"])
        self.assertEqual(after[PHASE]["model"], "gemini-3.6-flash")
        for old, value in state["reserved"].items():
            self.assertEqual(after["reserved"][old], value)
        self.assertIn(call, after["reserved"])


    def legacy_disabled_fixture(self):
        state = copy.deepcopy(self.state)
        old = "public-live:" + "x" * 32
        call = "c" * 32
        state[PHASE].update(model=LEGACY_MODEL, enabled=False, active_case=None,
                            case_http={old: 1}, day_http={"2026-11-03": 1}, last_http_at=self.now - 100)
        state["reserved"][call] = ".349237"
        state["calls"].append({"call_id": call, "phase": PHASE, "case_id": old,
                               "requested_model": LEGACY_MODEL, "reservation_disposition": "retained_uncertain"})
        self.save(state)
        self.path.write_text(json.dumps(state, separators=(",", ":")))
        return state

    def migration_args(self, **override):
        return {"expected_ledger_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
                "source_revision": "b" * 40, "approval_ref": "synthetic reviewed migration",
                "migration_id": "d" * 32, **override}

    def test_actual_legacy_phase_refused_before_explicit_migration_and_admitted_only_after_explicit_enable(self):
        state = self.legacy_disabled_fixture()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(BudgetDenied, "phase_configuration_invalid"):
            self.budget.admit(self.body(), self.case)
        self.assertEqual(self.path.read_bytes(), before)
        receipt = self.budget.migrate_disabled_model(**self.migration_args())
        migrated = self.read()
        self.assertFalse(migrated[PHASE]["enabled"])
        with self.assertRaisesRegex(BudgetDenied, "disabled"):
            self.budget.admit(self.body(), self.case)
        reconstructed = copy.deepcopy(migrated)
        reconstructed[PHASE]["model"] = LEGACY_MODEL
        del reconstructed[PHASE]["model_migration_history"]
        self.assertEqual(json.dumps(reconstructed, separators=(",", ":")).encode(),
                         json.dumps(state, separators=(",", ":")).encode())
        self.assertEqual(receipt["before_ledger_sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(receipt["after_ledger_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        journal = self.root / ("model-migration-" + "d" * 32 + ".json")
        self.assertEqual(json.loads(journal.read_text()), receipt)
        self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
        with self.budget.transaction() as current:
            current[PHASE]["enabled"] = True
        self.budget.arm_case(self.case)
        call, _ = self.budget.admit(self.body(), self.case)
        after = self.read()
        self.assertEqual(after["calls"], state["calls"])
        for prior, value in state["reserved"].items():
            self.assertEqual(after["reserved"][prior], value)
        self.assertIn(call, after["reserved"])
        self.assertEqual(after[PHASE]["case_http"]["public-live:" + "x" * 32], 1)

    def test_model_migration_refuses_enabled_armed_or_inflight_legacy_state_without_writes(self):
        for scenario in ("enabled", "armed", "inflight"):
            state = self.legacy_disabled_fixture()
            if scenario == "enabled":
                state[PHASE]["enabled"] = True
            else:
                state[PHASE]["active_case"] = "public-live:" + "x" * 32
                if scenario == "inflight":
                    state["calls"] = state["calls"][:-1]
                    state[PHASE]["in_flight"] = {"c" * 32: "public-live:" + "x" * 32}
            self.save(state)
            before = self.path.read_bytes()
            with self.assertRaisesRegex(BudgetDenied, "disable_and_reconcile"):
                self.budget.migrate_disabled_model(**self.migration_args())
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(list(self.root.glob("model-migration-*")), [])

    def test_model_migration_rejects_stale_digest_or_missing_review_reference(self):
        self.legacy_disabled_fixture()
        before = self.path.read_bytes()
        for change in ({"expected_ledger_sha256": "e" * 64}, {"approval_ref": ""},
                       {"source_revision": "not-a-source"}, {"migration_id": "not-an-id"}):
            with self.assertRaises(BudgetDenied):
                self.budget.migrate_disabled_model(**self.migration_args(**change))
            self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("model-migration-*")), [])

    def test_model_migration_refuses_encoding_drift_instead_of_reformatting_protected_bytes(self):
        state = self.legacy_disabled_fixture()
        self.save(state)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(BudgetDenied, "protected_ledger_bytes_or_encoding_changed"):
            self.budget.migrate_disabled_model(**self.migration_args())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("model-migration-*")), [])

    def test_prepared_journal_after_precommit_crash_blocks_blind_replay(self):
        self.legacy_disabled_fixture()
        before = self.path.read_bytes()
        args = self.migration_args()
        with patch.object(self.budget, "save_bytes", side_effect=OSError("synthetic interrupted commit")):
            with self.assertRaises(OSError):
                self.budget.migrate_disabled_model(**args)
        self.assertEqual(self.path.read_bytes(), before)
        journal = self.root / ("model-migration-" + "d" * 32 + ".json")
        self.assertEqual(json.loads(journal.read_text())["state"], "prepared")
        saved = journal.read_bytes()
        with self.assertRaisesRegex(BudgetDenied, "journal_exists_reconcile"):
            self.budget.migrate_disabled_model(**args)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(journal.read_bytes(), saved)

    def test_postcommit_journal_failure_retains_disabled_new_model_and_exact_prepared_receipt(self):
        self.legacy_disabled_fixture()
        before = self.path.read_bytes()
        args = self.migration_args()
        original = self.budget.sync_directory
        calls = []
        def interrupted():
            calls.append(1)
            if len(calls) == 3:
                raise OSError("synthetic directory fsync interruption")
            original()
        with patch.object(self.budget, "sync_directory", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.budget.migrate_disabled_model(**args)
        after = self.path.read_bytes()
        self.assertNotEqual(before, after)
        self.assertFalse(self.read()[PHASE]["enabled"])
        journal = json.loads((self.root / ("model-migration-" + "d" * 32 + ".json")).read_text())
        self.assertEqual(journal["after_ledger_sha256"], hashlib.sha256(after).hexdigest())
        # The mutation is reconciled from exact hashes; another call cannot recreate it.
        with self.assertRaises(BudgetDenied):
            self.budget.migrate_disabled_model(**args)
        self.assertEqual(self.path.read_bytes(), after)

    def test_concurrent_operator_migrations_apply_once_without_resetting_history(self):
        state = self.legacy_disabled_fixture()
        args = self.migration_args()
        code = ('import sys,json;from live_budget import LiveBudget,BudgetDenied;'
                'b=LiveBudget(sys.argv[1],clock=lambda:float(sys.argv[3]));'
                '\ntry:b.migrate_disabled_model(**json.loads(sys.argv[2]));print("applied")'
                '\nexcept BudgetDenied:print("denied")')
        processes = [subprocess.Popen([sys.executable, "-c", code, str(self.root), json.dumps(dict(args, migration_id=str(i) * 32)), str(self.now)],
                     cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in (1, 2)]
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(stdout.strip())
        self.assertEqual(sorted(results), ["applied", "denied"])
        self.assertEqual(len(self.read()[PHASE]["model_migration_history"]), 1)
        self.assertEqual(len(list(self.root.glob("model-migration-*.json"))), 1)
        self.assertEqual(self.read()["calls"], state["calls"])
        self.assertEqual(self.read()["reserved"], state["reserved"])

    def test_exact_approved_response_model_aliases_settle_without_releasing_old_holds(self):
        for alias in RESPONSE_MODEL_IDS:
            self.save(copy.deepcopy(self.state))
            call, _ = self.budget.admit(self.body(), self.case)
            data = {"model": alias, "usage": {"prompt_tokens": 500, "completion_tokens": 100}}
            self.assertTrue(self.settle(call, data=data))
            self.assertEqual(self.read()["calls"][-1]["returned_model"], alias)
            self.assertEqual(self.read()["reserved"], self.state["reserved"])

    def test_different_or_unreviewed_model_or_malformed_model_retains_own_hold(self):
        for alias in (LEGACY_MODEL, "gemini-3.6-flash-unreviewed", "models/gemini-3.6-flash-future", {}, [], None):
            self.save(copy.deepcopy(self.state))
            call, _ = self.budget.admit(self.body(), self.case)
            data = {"model": alias, "usage": {"prompt_tokens": 500, "completion_tokens": 100}}
            self.assertFalse(self.settle(call, data=data))
            self.assertIn(call, self.read()["reserved"])
            self.assertFalse(self.read()[PHASE]["enabled"])
            self.assertIsNone(self.read()["calls"][-1]["returned_model"])


if __name__ == "__main__":
    unittest.main()
