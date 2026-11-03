"""Durable admission for the optional live demo; no provider or financial API.

This controller is not connected to the public viewer yet. A private worker must
enforce the existing inference budget before every provider request. Admission
here limits decisions, not HTTP calls or billed cost. In-flight work is never
retried automatically after a worker crash.
"""
from contextlib import contextmanager
from pathlib import Path
import datetime as dt
import fcntl
import json
import math
import os
import re
import secrets
import stat
import time
from zoneinfo import ZoneInfo


# The native pbp.Data.Case.CaseId is limited to 64 characters. Keep the
# public-live: prefix and request identifier within that persisted boundary.
REQUEST_ID_PATTERN = r"[a-zA-Z0-9_-]{16,48}"


class QueueUnavailable(Exception):
    pass


class LiveQueue:
    def __init__(self, directory, scenarios, *, enabled=False, daily_cap=5,
                 interval_seconds=10, clock=time.time):
        self.directory = Path(directory)
        self.scenarios = frozenset(scenarios)
        if not self.scenarios or any(not re.fullmatch(r"[a-z0-9_-]{1,40}", x) for x in self.scenarios):
            raise ValueError("fixed_scenarios_required")
        if (type(enabled) is not bool or type(daily_cap) is not int or not 1 <= daily_cap <= 5
                or type(interval_seconds) not in (int, float)
                or not math.isfinite(interval_seconds) or interval_seconds < 10):
            raise ValueError("live_demo_limits_exceeded")
        self.enabled, self.daily_cap = enabled, daily_cap
        self.interval, self.clock = interval_seconds, clock
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        s = self.directory.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_mode & 0o077 or s.st_uid != os.getuid():
            raise QueueUnavailable("private_state_directory_required")

    @staticmethod
    def fallback(reason, **extra):
        return {"ok": False, "mode": "recorded", "reason": reason, **extra}

    @contextmanager
    def locked(self):
        fd = os.open(self.directory / "queue.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            s = os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077 or s.st_uid != os.getuid():
                raise QueueUnavailable("private_state_lock_required")
            fcntl.flock(fd, fcntl.LOCK_EX)
            path = self.directory / "queue.json"
            try:
                sf = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            except FileNotFoundError:
                state = {"schema": 1, "days": {}, "jobs": {}, "active": None, "last_start": None}
            else:
                try:
                    s = os.fstat(sf)
                    if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077 or s.st_uid != os.getuid() or s.st_size > 1_000_000:
                        raise QueueUnavailable("private_state_file_required")
                    with os.fdopen(sf, "r") as stream:
                        sf = None
                        state = json.load(stream)
                except (ValueError, OSError) as ex:
                    raise QueueUnavailable("state_unreadable_no_reset") from ex
                finally:
                    if sf is not None:
                        os.close(sf)
            self.validate(state)
            yield state
        finally:
            os.close(fd)

    @staticmethod
    def validate(state):
        def require(condition):
            if not condition:
                raise QueueUnavailable("state_invalid_no_reset")
        try:
            require(set(state) == {"schema", "days", "jobs", "active", "last_start"})
            require(state["schema"] == 1 and isinstance(state["days"], dict) and isinstance(state["jobs"], dict))
            require(all(type(n) is int and n >= 0 for n in state["days"].values()))
            require(state["last_start"] is None or (type(state["last_start"]) in (int, float) and math.isfinite(state["last_start"])))
            active = []
            days = {}
            for token, job in state["jobs"].items():
                require(re.fullmatch(REQUEST_ID_PATTERN, token))
                require(job["status"] in {"queued", "running", "complete", "failed"})
                require(isinstance(job["scenario"], str))
                require(dt.date.fromisoformat(job["day"]).isoformat() == job["day"])
                days[job["day"]] = days.get(job["day"], 0) + 1
                if job["status"] in {"queued", "running"}:
                    active.append(token)
            require(days == state["days"])
            require(active == ([] if state["active"] is None else [state["active"]]))
        except (KeyError, TypeError, ValueError) as ex:
            raise QueueUnavailable("state_invalid_no_reset") from ex

    def save(self, state):
        self.validate(state)
        data = json.dumps(state, allow_nan=False, separators=(",", ":")).encode()
        if len(data) > 1_000_000:
            raise QueueUnavailable("state_archive_required")
        tmp = self.directory / (".queue-" + secrets.token_hex(12))
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.directory / "queue.json")
            df = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(df)
            finally:
                os.close(df)
        finally:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def projection(job):
        return {k: job[k] for k in ("status", "scenario", "day", "case_id", "commitment", "session_id") if k in job}

    def submit(self, scenario, request_id):
        if not self.enabled:
            return self.fallback("live_disabled")
        if not isinstance(scenario, str) or scenario not in self.scenarios or not isinstance(request_id, str) or not re.fullmatch(REQUEST_ID_PATTERN, request_id):
            return self.fallback("fixed_scenario_and_request_id_required")
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            return self.fallback("clock_unavailable")
        # Google's free-tier RPD resets at midnight Pacific, including DST.
        day = dt.datetime.fromtimestamp(now, ZoneInfo("America/Los_Angeles")).date().isoformat()
        with self.locked() as state:
            if request_id in state["jobs"]:
                job = state["jobs"][request_id]
                if job["scenario"] != scenario:
                    return self.fallback("request_id_conflict")
                return {"ok": True, "duplicate": True, "job": self.projection(job)}
            if state["active"] is not None:
                return self.fallback("live_queue_busy")
            if state["days"].get(day, 0) >= self.daily_cap:
                return self.fallback("daily_cap_reached")
            last = state["last_start"]
            if last is not None and now < last + self.interval:
                return self.fallback("live_interval", retry_after=max(1, math.ceil(last + self.interval - now)))
            state["jobs"][request_id] = {"status": "queued", "scenario": scenario, "day": day}
            state["active"] = request_id
            state["days"][day] = state["days"].get(day, 0) + 1
            self.save(state)
            return {"ok": True, "duplicate": False, "job": self.projection(state["jobs"][request_id])}

    def run_one(self, runner):
        """Claim durably before calling the private, budget-controlled runner once."""
        if not self.enabled:
            return False
        with self.locked() as state:
            token = state["active"]
            if token is None or state["jobs"][token]["status"] != "queued":
                return False
            now = self.clock()
            last = state["last_start"]
            if (type(now) not in (int, float) or not math.isfinite(now)
                    or (last is not None and now < last + self.interval)):
                return False
            state["jobs"][token]["status"] = "running"
            state["last_start"] = now
            scenario = state["jobs"][token]["scenario"]
            if scenario not in self.scenarios:
                raise QueueUnavailable("queued_scenario_no_longer_configured")
            self.save(state)
        try:
            result = runner(scenario, token)
            if not isinstance(result, dict) or result.get("mode") != "live":
                raise ValueError("live_result_required")
            if result.get("case_id") != "public-live:" + token:
                raise ValueError("native_case_required")
            if not re.fullmatch(r"[0-9a-f]{64}", result.get("commitment", "")):
                raise ValueError("decision_seal_required")
            if not isinstance(result.get("session_id"), str) or not result["session_id"].isdigit():
                raise ValueError("native_session_required")
            outcome = {k: result[k] for k in ("case_id", "commitment", "session_id")}
        except Exception:
            # No exception text, provider reply, key or arbitrary runner fields are stored.
            outcome = None
        with self.locked() as state:
            job = state["jobs"][token]
            if job["status"] != "running" or state["active"] != token:
                raise QueueUnavailable("worker_state_changed")
            job["status"] = "complete" if outcome is not None else "failed"
            if outcome is not None:
                job.update(outcome)
            state["active"] = None
            self.save(state)
        return True
