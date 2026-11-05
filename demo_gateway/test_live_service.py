import json
from pathlib import Path
import unittest

from live_budget import MODEL, PHASE
from live_provider import PrivateProvider
from live_queue import LiveQueue, QueueUnavailable
from live_service import LiveService
import test_live_budget as budget_tests


class LiveServiceTests(unittest.TestCase):
    setUp = budget_tests.LiveBudgetTests.setUp
    save = budget_tests.LiveBudgetTests.save
    read = budget_tests.LiveBudgetTests.read

    def service(self, *, enabled=True, ready=True, runner=None):
        with self.budget.transaction() as state:
            state[PHASE]["active_case"] = None
        queue = LiveQueue(self.root / "queue", {"missing_evidence", "amount_conflict"}, enabled=enabled, clock=lambda: self.now)
        self.requests = []
        provider = PrivateProvider(self.budget, "not-a-real-key-" + "x" * 32, send=self.fake_provider)
        def native(scenario, token):
            case_id = "public-live:" + token
            status, _ = provider.complete({"model": MODEL, "messages": [{"role": "user", "content": case_id}]})
            if status != 200:
                raise ValueError("test transport refused")
            return {"mode": "live", "case_id": case_id, "commitment": "a" * 64, "session_id": "123", "private": "not exposed"}
        return LiveService(queue, self.budget, runner or native, lambda: ready, enabled=enabled)

    def fake_provider(self, body):
        self.requests.append(body)
        return 200, json.dumps({"model": MODEL, "usage": {"prompt_tokens": 500, "completion_tokens": 100}, "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}).encode()

    def test_fixed_admission_budgeted_worker_and_read_only_completion(self):
        service = self.service()
        token = "a" * 16
        request = {"scenario": "missing_evidence", "request_id": token}
        self.assertTrue(service.status()["available"])
        self.assertTrue(service.submit(request)["ok"])
        self.assertEqual(self.requests, [])
        self.assertEqual(service.status(token)["job"]["status"], "queued")
        self.assertTrue(service.run_one())
        job = service.status(token)["job"]
        self.assertEqual(job["status"], "complete")
        self.assertEqual(job["case_id"], "public-live:" + token)
        self.assertNotIn("private", job)
        self.assertTrue(service.submit(request)["duplicate"])
        self.assertFalse(service.run_one())
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.read()["reserved"], self.state["reserved"])
        self.assertIsNone(self.read()[PHASE]["active_case"])

    def test_fake_live_result_without_observed_provider_call_is_not_published(self):
        service = self.service(runner=lambda scenario, token: {"mode": "live", "case_id": "public-live:" + token,
                                                            "commitment": "a" * 64, "session_id": "123"})
        service.submit({"scenario": "missing_evidence", "request_id": "a" * 16})
        service.run_one()
        self.assertEqual(service.status("a" * 16)["job"]["status"], "failed")
        self.assertEqual(service.completed_cases(), {})
        self.assertFalse(self.read()[PHASE]["enabled"])
        self.assertEqual(self.read()["forwarded_calls"], 203)

    def test_missing_native_seal_disables_public_phase_without_clearing_history(self):
        service = self.service(runner=lambda *_: {"mode": "recorded"})
        service.submit({"scenario": "amount_conflict", "request_id": "a" * 16})
        service.run_one()
        self.assertEqual(service.status("a" * 16)["job"]["status"], "failed")
        self.assertFalse(service.status()["available"])
        self.assertEqual(self.read()["reserved"], self.state["reserved"])
        self.assertEqual(self.read()["benchmark_v7_phase"], self.state["benchmark_v7_phase"])

    def test_native_crash_keeps_queue_running_and_does_not_retry(self):
        def crash(*_):
            raise KeyboardInterrupt()
        service = self.service(runner=crash)
        service.submit({"scenario": "missing_evidence", "request_id": "a" * 16})
        with self.assertRaises(KeyboardInterrupt):
            service.run_one()
        self.assertEqual(service.status("a" * 16)["job"]["status"], "running")
        self.assertFalse(service.run_one())
        self.assertFalse(service.status()["available"])
        self.assertEqual(service.completed_cases(), {})

    def test_arbitrary_prompt_case_and_unknown_scenario_do_not_create_job(self):
        service = self.service()
        for request in ({"scenario": "unknown", "request_id": "a" * 16},
                        {"scenario": "missing_evidence", "request_id": "a" * 16, "prompt": "send money"},
                        {"scenario": "missing_evidence", "request_id": "a" * 16, "case_id": "private"}):
            self.assertFalse(service.submit(request)["ok"])
        self.assertFalse((self.root / "queue/queue.json").exists())
        self.assertEqual(self.read()["forwarded_calls"], 203)

    def test_disabled_or_unready_native_route_never_admits(self):
        for enabled, ready in ((False, True), (True, False)):
            service = self.service(enabled=enabled, ready=ready)
            self.assertFalse(service.status()["available"])
            self.assertFalse(service.submit({"scenario": "missing_evidence", "request_id": "a" * 16})["ok"])
            self.assertFalse((self.root / "queue/queue.json").exists())

    def test_corrupt_completed_case_binding_is_not_exposed(self):
        service = self.service()
        token = "a" * 16
        service.submit({"scenario": "missing_evidence", "request_id": token})
        service.run_one()
        path = self.root / "queue/queue.json"
        state = json.loads(path.read_text())
        state["jobs"][token]["case_id"] = "private-benchmark-case"
        path.write_text(json.dumps(state))
        self.assertEqual(service.completed_cases(), {})
        self.assertFalse(service.status()["available"])
        self.assertEqual(json.loads(path.read_text()), state)


if __name__ == "__main__":
    unittest.main()
