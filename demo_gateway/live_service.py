"""Connect fixed-scenario admission to an explicitly supplied native runner.

No native runner, credentials or activation are inferred from configuration.
The public viewer cannot arm a case directly or select a provider/prompt.
"""
import re
import threading

from live_budget import BudgetDenied
from live_queue import QueueUnavailable


class LiveService:
    def __init__(self, queue, budget, native_runner, native_ready, *, enabled=False):
        if type(enabled) is not bool or not callable(native_runner) or not callable(native_ready):
            raise ValueError("explicit_native_runner_required")
        self.queue, self.budget = queue, budget
        self.native_runner, self.native_ready = native_runner, native_ready
        self.enabled = enabled
        self.wake = threading.Event()

    @staticmethod
    def fallback(reason):
        return {"ok": False, "mode": "recorded", "available": False, "reason": reason}

    def status(self, request_id=None):
        try:
            if request_id is not None:
                return self.queue.inspect(request_id)
            snapshot = self.queue.inspect()
            if not snapshot.get("ok"):
                return self.fallback("live_state_unavailable")
            budget = self.budget.public_status()
            available = bool(self.enabled and snapshot["enabled"] and not snapshot["busy"]
                             and snapshot["remaining_decisions_today"] > 0
                             and budget["available"] and self.native_ready() is True)
            reason = (None if available else "decision_in_progress" if snapshot["busy"]
                      else "daily_decision_cap_reached" if snapshot["remaining_decisions_today"] == 0
                      else budget.get("reason") or "live_unavailable")
            return {"ok": True, "mode": "live_available" if available else "recorded",
                    "available": available, "reason": reason,
                    "remaining_decisions_today": snapshot["remaining_decisions_today"],
                    "scenarios": snapshot["scenarios"], "completed": snapshot["completed"]}
        except Exception:
            return self.fallback("live_state_unavailable")

    def submit(self, body):
        if not isinstance(body, dict) or set(body) != {"scenario", "request_id"}:
            return self.fallback("fixed_scenario_request_required")
        # Repeat requests only read their existing job, even if the daily cap is
        # now exhausted or a provider failure has disabled further admission.
        prior = self.status(body["request_id"])
        if prior.get("ok"):
            job = prior["job"]
            if job["scenario"] != body["scenario"]:
                return self.fallback("request_id_conflict")
            return {"ok": True, "duplicate": True, "job": job}
        availability = self.status()
        if not availability.get("available"):
            return self.fallback(availability.get("reason") or "live_unavailable")
        try:
            result = self.queue.submit(body["scenario"], body["request_id"])
            if result.get("ok"):
                self.wake.set()
            return result
        except Exception:
            return self.fallback("live_state_unavailable")

    def completed_cases(self):
        try:
            return {job["case_id"]: job for job in self.queue.inspect().get("completed", [])}
        except Exception:
            return {}

    def run_one(self):
        if not self.enabled:
            return False

        def runner(scenario, token):
            case_id = "public-live:" + token
            self.budget.arm_case(case_id)
            successful = False
            try:
                result = self.native_runner(scenario, token)
                successful = (isinstance(result, dict) and result.get("mode") == "live"
                              and result.get("case_id") == case_id
                              and isinstance(result.get("commitment"), str)
                              and re.fullmatch(r"[0-9a-f]{64}", result["commitment"]) is not None
                              and isinstance(result.get("session_id"), str) and result["session_id"].isdigit())
                if not successful:
                    raise ValueError("sealed_native_live_result_required")
                return result
            finally:
                accounted = self.budget.finish_case(case_id, successful)
                if successful and not accounted:
                    raise ValueError("observed_budgeted_live_request_required")

        return self.queue.run_one(runner)

    def work(self, stop):
        while not stop.is_set():
            self.wake.wait(1)
            self.wake.clear()
            if stop.is_set():
                break
            try:
                self.run_one()
            except (OSError, ValueError, BudgetDenied, QueueUnavailable):
                # No reset/retry of in-flight work. Status remains inspectable
                # and falls back to recorded examples if state is unavailable.
                pass
