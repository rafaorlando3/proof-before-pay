import concurrent.futures
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from live_queue import LiveQueue, QueueUnavailable


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = 1793745000.0

    def queue(self, **kw):
        return LiveQueue(self.tmp.name, {"missing_evidence", "duplicate"},
                         clock=lambda: self.now, **kw)

    @staticmethod
    def result(*args):
        token = args[1] if len(args) > 1 else "a" * 16
        return {"mode": "live", "case_id": "public-live:" + token, "commitment": "a" * 64,
                "session_id": "123", "api_key": "must never be persisted"}

    def test_disabled_never_admits_or_calls_runner(self):
        q = self.queue()
        self.assertEqual(q.submit("duplicate", "a" * 16)["reason"], "live_disabled")
        self.assertFalse(q.run_one(lambda *_: self.fail("runner called")))
        self.assertFalse((Path(self.tmp.name) / "queue.json").exists())

    def test_concurrent_admission_one_slot_and_one_claim(self):
        q = self.queue(enabled=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda i: q.submit("duplicate", f"request_{i:016}"), range(30)))
        self.assertEqual(sum(r["ok"] for r in results), 1)
        calls = []
        def runner(*args):
            calls.append(args)
            return self.result(*args)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            claimed = list(pool.map(lambda _: q.run_one(runner), range(30)))
        self.assertEqual(sum(claimed), 1)
        self.assertEqual(len(calls), 1)

    def test_retry_idempotency_interval_cap_and_restart(self):
        token = "request_0000000001"
        q = self.queue(enabled=True)
        self.assertTrue(q.submit("duplicate", token)["ok"])
        q.run_one(self.result)
        q = self.queue(enabled=True)
        self.assertTrue(q.submit("duplicate", token)["duplicate"])
        self.assertEqual(q.submit("missing_evidence", token)["reason"], "request_id_conflict")
        self.assertEqual(q.submit("duplicate", "b" * 16)["reason"], "live_interval")
        for i in range(4):
            self.now += 10
            self.assertTrue(q.submit("duplicate", f"extra_{i:016}")["ok"])
            q.run_one(self.result)
        self.now += 10
        self.assertEqual(self.queue(enabled=True).submit("duplicate", "c" * 16)["reason"], "daily_cap_reached")
        self.now += 86400
        self.assertTrue(q.submit("duplicate", "d" * 16)["ok"])
        state = json.loads((Path(self.tmp.name) / "queue.json").read_text())
        self.assertEqual(sorted(state["days"].values()), [1, 5])

    def test_crashed_worker_stays_inflight_without_automatic_retry(self):
        q = self.queue(enabled=True)
        q.submit("duplicate", "a" * 16)
        def crash(*_):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            q.run_one(crash)
        q = self.queue(enabled=True)
        self.assertFalse(q.run_one(lambda *_: self.fail("uncertain job retried")))
        self.now += 86400
        self.assertEqual(q.submit("duplicate", "b" * 16)["reason"], "live_queue_busy")

    def test_corruption_does_not_reset_daily_usage(self):
        q = self.queue(enabled=True)
        q.submit("duplicate", "a" * 16)
        path = Path(self.tmp.name) / "queue.json"
        state = json.loads(path.read_text())
        state["days"] = {}
        path.write_text(json.dumps(state))
        before = path.read_bytes()
        with self.assertRaises(QueueUnavailable):
            q.submit("duplicate", "b" * 16)
        self.assertEqual(path.read_bytes(), before)

    def test_runner_failure_counts_and_filters_secrets_and_recorded_output(self):
        q = self.queue(enabled=True)
        q.submit("duplicate", "a" * 16)
        q.run_one(lambda *_: {**self.result(), "mode": "recorded"})
        self.now += 10
        q.submit("duplicate", "b" * 16)
        q.run_one(self.result)
        text = (Path(self.tmp.name) / "queue.json").read_text()
        self.assertNotIn("must never", text)
        self.assertNotIn("api_key", text)
        self.assertEqual([j["status"] for j in json.loads(text)["jobs"].values()], ["failed", "complete"])
        self.assertEqual(sum(json.loads(text)["days"].values()), 2)

    def test_unsafe_state_symlink_is_not_followed(self):
        other = Path(self.tmp.name) / "private-other.json"
        other.write_text("untouched")
        (Path(self.tmp.name) / "queue.json").symlink_to(other)
        with self.assertRaises(OSError):
            self.queue(enabled=True).submit("duplicate", "a" * 16)
        self.assertEqual(other.read_text(), "untouched")

    def test_cooldown_measures_worker_start_after_queued_wait(self):
        q = self.queue(enabled=True)
        q.submit("duplicate", "a" * 16)
        self.now += 60
        q.run_one(self.result)
        self.assertEqual(q.submit("duplicate", "b" * 16)["reason"], "live_interval")
        self.now += 10
        self.assertTrue(q.submit("duplicate", "b" * 16)["ok"])

    def test_invalid_configuration_and_unsafe_result_fail_closed(self):
        for kw in ({"daily_cap": 6}, {"interval_seconds": float("nan")}, {"enabled": "false"}):
            with self.assertRaises(ValueError):
                self.queue(**kw)
        q = self.queue(enabled=True)
        self.assertFalse(q.submit([], "a" * 16)["ok"])
        q.submit("duplicate", "a" * 16)
        q.run_one(lambda *_: {**self.result(), "commitment": "no seal"})
        state = json.loads((Path(self.tmp.name) / "queue.json").read_text())
        self.assertEqual(state["jobs"]["a" * 16]["status"], "failed")

    def test_provider_day_does_not_reset_at_UTC_midnight(self):
        self.now = dt.datetime(2026, 11, 2, 23, 59, 55, tzinfo=dt.timezone.utc).timestamp()
        q = self.queue(enabled=True, daily_cap=1)
        q.submit("duplicate", "a" * 16)
        q.run_one(self.result)
        self.now += 20
        self.assertEqual(q.submit("duplicate", "b" * 16)["reason"], "daily_cap_reached")

    def test_processes_share_the_same_durable_admission_lock(self):
        code = ('import sys,json;from live_queue import LiveQueue;'
                'q=LiveQueue(sys.argv[1],{"duplicate"},enabled=True);'
                'print(json.dumps(q.submit("duplicate",sys.argv[2])))')
        jobs = [subprocess.Popen([sys.executable, "-c", code, self.tmp.name, f"process_{i:016}"],
                                 cwd=Path(__file__).parent, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True) for i in range(8)]
        replies = []
        for job in jobs:
            out, err = job.communicate(timeout=10)
            self.assertEqual(job.returncode, 0, err)
            replies.append(json.loads(out))
        self.assertEqual(sum(x["ok"] for x in replies), 1)

    def test_wrong_case_result_is_not_published(self):
        q = self.queue(enabled=True)
        q.submit("duplicate", "a" * 16)
        q.run_one(lambda *_: {**self.result(), "case_id": "private-case:other"})
        text = (Path(self.tmp.name) / "queue.json").read_text()
        self.assertNotIn("private-case", text)
        self.assertEqual(json.loads(text)["jobs"]["a" * 16]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
