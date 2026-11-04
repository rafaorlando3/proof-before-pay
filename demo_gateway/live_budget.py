"""Per-HTTP admission against the existing inference ledger, not a new budget.

No provider is contacted here. The operator must stage an explicitly approved
public_live_demo phase in the SAME budget.json used by previous experiments.
This module never creates a budget, enables a phase, clears a historical hold,
or retries an uncertain request. Monetary settlement is a provisional usage
estimate, never a billing receipt or a claim that free-tier usage was charged.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
import datetime as dt
import fcntl
import json
import math
import os
import re
import stat
import time
import uuid

MODEL = "gemini-3.8-flash"
PHASE = "public_live_demo"
CASE_PATTERN = r"public-live:[A-Za-z0-9_-]{16,48}"


class BudgetDenied(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise BudgetDenied(reason)


def money(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise BudgetDenied("invalid_accounting") from None
    require(number.is_finite() and number >= 0, "invalid_accounting")
    return number


def accounted(state):
    require(isinstance(state.get("reserved"), dict), "invalid_reservations")
    return (money(state["spent_usd"]) + money(state.get("estimated_spent_usd", "0"))
            + sum((money(x) for x in state["reserved"].values()), Decimal(0)))


def usage_estimate(usage):
    if not isinstance(usage, dict):
        return None
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if not all(type(x) is int for x in (prompt, completion)) or not 0 < prompt <= 100000 or not 0 <= completion <= 65536:
        return None
    output = completion
    if "total_tokens" in usage:
        total = usage["total_tokens"]
        if type(total) is not int or total < prompt + completion:
            return None
        output = max(output, total - prompt)
    details = usage.get("completion_tokens_details") or {}
    if not isinstance(details, dict):
        return None
    if "reasoning_tokens" in details:
        reasoning = details["reasoning_tokens"]
        if type(reasoning) is not int or not 0 <= reasoning <= 65536:
            return None
        output = max(output, completion + reasoning)
    if output > 65536:
        return None
    return Decimal(prompt) * Decimal(".00000075") + Decimal(output) * Decimal(".00000375")


def prepare_request(body, case_id):
    require(isinstance(case_id, str) and re.fullmatch(CASE_PATTERN, case_id), "public_case_required")
    require(isinstance(body, dict) and body.get("model") == MODEL and not body.get("stream"), "model_or_stream_denied")
    require(not (set(body) - {"model", "messages", "tools", "tool_choice", "parallel_tool_calls", "max_tokens", "temperature", "reasoning_effort", "stream"}), "unsupported_provider_option")
    messages = body.get("messages")
    require(isinstance(messages, list) and 1 <= len(messages) <= 40, "bounded_messages_required")
    for message in messages:
        require(isinstance(message, dict) and message.get("role") in {"system", "user", "assistant", "tool"}, "message_shape")
        content = message.get("content")
        require(content is None or isinstance(content, str), "text_only")
    tools = body.get("tools", [])
    require(isinstance(tools, list) and len(tools) <= 5, "local_tools_only")
    names = set()
    for tool in tools:
        require(isinstance(tool, dict) and tool.get("type") == "function", "local_tools_only")
        function = tool.get("function")
        require(isinstance(function, dict), "local_tools_only")
        name = function.get("name")
        require(isinstance(name, str) and re.fullmatch(r"(?:pbp[._]Tools[._])?Get(?:Order|PixEvents|PayerHistory|Evidence|StorePolicy)", name), "unapproved_tool")
        require(name not in names, "duplicate_tool")
        names.add(name)
    cap = body.get("max_tokens", 2048)
    require(type(cap) is int and 1 <= cap <= 2048, "output_bound")
    forwarded = dict(body, max_tokens=cap, reasoning_effort="low", stream=False)
    # Google 3.8 ignores temperature; do not represent it as temperature-zero sampling.
    forwarded.pop("temperature", None)
    raw = json.dumps(forwarded, allow_nan=False, separators=(",", ":")).encode()
    require(len(raw) <= 40000 and case_id.encode() in raw, "input_bound_or_case_scope")
    reserve = Decimal(len(raw) + 16384) * Decimal(".000001") + Decimal(65536) * Decimal(".000005")
    return raw, reserve


class LiveBudget:
    def __init__(self, directory, *, clock=time.time):
        self.directory, self.clock = Path(directory), clock
        require(self.directory.is_dir() and not self.directory.is_symlink(), "existing_private_budget_required")
        require(not self.directory.stat().st_mode & 0o077, "private_budget_directory_required")

    def private_fd(self, path, flags):
        fd = os.open(path, flags | os.O_NOFOLLOW)
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            os.close(fd)
            raise BudgetDenied("private_regular_budget_file_required")
        return fd

    def load(self):
        require(not list(self.directory.glob("budget*.tmp")), "partial_save_reconcile_first")
        source = self.private_fd(self.directory / "budget.json", os.O_RDONLY)
        with os.fdopen(source, "r") as stream:
            metadata = os.fstat(stream.fileno())
            require(metadata.st_size <= 8_000_000, "budget_archive_required")
            state = json.load(stream)
        self.validate(state)
        return state, metadata

    def armed_case(self):
        fd = self.private_fd(self.directory / "budget.lock", os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            state, _ = self.load()
            return state[PHASE].get("active_case")
        finally:
            os.close(fd)

    def public_status(self):
        fd = self.private_fd(self.directory / "budget.lock", os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            state, _ = self.load()
            phase = state[PHASE]
            now = self.clock()
            require(type(now) in (int, float) and math.isfinite(now), "clock_unavailable")
            day = dt.datetime.fromtimestamp(now, ZoneInfo("America/Los_Angeles")).date().isoformat()
            reason = None
            if not phase["enabled"] or now >= phase["expires_at"]:
                reason = "live_disabled_or_expired"
            elif phase["in_flight"]:
                reason = "model_request_in_progress"
            elif phase.get("active_case") is not None:
                reason = "native_case_in_progress"
            elif phase["day_http"].get(day, 0) >= 15:
                reason = "daily_model_quota_reached"
            elif accounted(state) + Decimal(".35") > Decimal("1"):
                reason = "cumulative_budget_headroom_required"
            return {"available": reason is None, "reason": reason,
                    "remaining_model_calls_today": max(0, 15 - phase["day_http"].get(day, 0))}
        finally:
            os.close(fd)

    def arm_case(self, case_id):
        require(isinstance(case_id, str) and re.fullmatch(CASE_PATTERN, case_id), "public_case_required")
        with self.transaction() as state:
            phase = self.validate(state)
            require(phase["enabled"] and self.clock() < phase["expires_at"], "public_phase_disabled_or_expired")
            require(not phase["in_flight"] and phase.get("active_case") is None, "previous_case_reconcile_first")
            require(case_id not in phase["case_http"], "previous_case_attempt_reconcile_first")
            phase["active_case"] = case_id

    def finish_case(self, case_id, successful):
        with self.transaction() as state:
            phase = self.validate(state)
            require(phase.get("active_case") == case_id, "armed_case_identity_changed")
            entries = [entry for entry in state["calls"] if entry.get("phase") == PHASE and entry.get("case_id") == case_id]
            successful = bool(successful and entries and not phase["in_flight"]
                              and all(entry.get("reservation_disposition") == "settled_provisional_estimate" for entry in entries))
            if not successful or phase["in_flight"]:
                phase["enabled"] = False
                phase["stop_reason"] = "native_result_uncertain_reconcile_before_retry"
            if not phase["in_flight"]:
                phase["active_case"] = None
        return successful

    @contextmanager
    def transaction(self):
        fd = self.private_fd(self.directory / "budget.lock", os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            state, metadata = self.load()
            yield state
            self.validate(state)
            data = json.dumps(state, allow_nan=False, separators=(",", ":")).encode()
            require(len(data) <= 8_000_000, "budget_archive_required")
            tmp = self.directory / ("budget-public-live-" + uuid.uuid4().hex + ".tmp")
            with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
                if os.getuid() == 0:
                    os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.directory / "budget.json")
            directory = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            os.close(fd)

    @staticmethod
    def validate(state):
        require(state.get("schema") == "pbp.inference-budget/1", "existing_budget_schema_required")
        require(money(state["cap_usd"]) == Decimal("1"), "active_one_dollar_cap_required")
        require(accounted(state) <= Decimal("1"), "budget_exhausted_or_inconsistent")
        require((state.get("estimated_settlement_policy") or {}).get("active") is True, "existing_estimate_settlement_policy_required")
        phase = state.get(PHASE)
        require(isinstance(phase, dict) and phase.get("schema") == "pbp.public-live-budget/1", "explicit_public_phase_required")
        require(isinstance(phase.get("approval_ref"), str) and bool(phase["approval_ref"]), "approval_reference_required")
        require(phase.get("model") == MODEL and type(phase.get("enabled")) is bool, "phase_configuration_invalid")
        require(isinstance(phase.get("case_http"), dict) and isinstance(phase.get("day_http"), dict) and isinstance(phase.get("in_flight"), dict), "phase_counters_invalid")
        require(type(phase.get("expires_at")) in (int, float) and math.isfinite(phase["expires_at"]), "phase_expiry_required")
        require(phase.get("last_http_at") is None or (type(phase["last_http_at"]) in (int, float) and math.isfinite(phase["last_http_at"])), "phase_clock_invalid")
        require(all(re.fullmatch(CASE_PATTERN, cid) and type(n) is int and 1 <= n <= 3 for cid, n in phase["case_http"].items()), "case_counter_invalid")
        require(all(dt.date.fromisoformat(day).isoformat() == day and type(n) is int and 1 <= n <= 15 for day, n in phase["day_http"].items()), "day_counter_invalid")
        entries = [x for x in state["calls"] if x.get("phase") == PHASE]
        ids = [x["call_id"] for x in entries]
        require(len(ids) == len(set(ids)) and not set(ids).intersection(phase["in_flight"]), "phase_calls_ambiguous")
        require(len(ids) + len(phase["in_flight"]) == sum(phase["case_http"].values()) == sum(phase["day_http"].values()), "phase_count_mismatch")
        require(len(phase["in_flight"]) <= 1, "phase_parallelism_invalid")
        for call, cid in phase["in_flight"].items():
            require(re.fullmatch(r"[0-9a-f]{32}", call) and cid in phase["case_http"] and call in state["reserved"], "inflight_reservation_missing")
        for entry in entries:
            retained = entry.get("reservation_disposition") == "retained_uncertain"
            require(entry.get("reservation_disposition") in {"retained_uncertain", "settled_provisional_estimate"}, "phase_disposition_unknown")
            require((entry["call_id"] in state["reserved"]) == retained, "phase_hold_inconsistent")
        return phase

    def admit(self, body, case_id):
        raw, reserve = prepare_request(body, case_id)
        now = self.clock()
        require(type(now) in (int, float) and math.isfinite(now), "clock_unavailable")
        day = dt.datetime.fromtimestamp(now, ZoneInfo("America/Los_Angeles")).date().isoformat()
        with self.transaction() as state:
            phase = self.validate(state)
            require(phase["enabled"] and now < phase["expires_at"], "public_phase_disabled_or_expired")
            require(phase.get("active_case") == case_id, "case_not_armed")
            require(not phase["in_flight"], "uncertain_inflight_reconcile_first")
            require(phase["case_http"].get(case_id, 0) < 3 and phase["day_http"].get(day, 0) < 15, "HTTP_quota_reached")
            require(phase["last_http_at"] is None or now >= phase["last_http_at"] + 15, "HTTP_rate_limit_wait")
            require(accounted(state) + reserve <= Decimal("1"), "cumulative_headroom_required")
            call = uuid.uuid4().hex
            state["reserved"][call] = str(reserve)
            state["forwarded_calls"] += 1
            state["gemini_forwarded_calls"] = state.get("gemini_forwarded_calls", 0) + 1
            phase["case_http"][case_id] = phase["case_http"].get(case_id, 0) + 1
            phase["day_http"][day] = phase["day_http"].get(day, 0) + 1
            phase["last_http_at"] = now
            phase["in_flight"][call] = case_id
        return call, raw

    def settle(self, call, *, status=None, data=None, archive=None):
        with self.transaction() as state:
            phase = self.validate(state)
            require(call in phase["in_flight"], "call_already_finished_or_unknown")
            now = self.clock()
            require(type(now) in (int, float) and math.isfinite(now) and now >= phase["last_http_at"], "clock_unavailable")
            # Persist cooldown from completion too. A slow admission fsync before
            # the previous network send must not shorten the next start interval.
            phase["last_http_at"] = now
            case_id = phase["in_flight"][call]
            estimate = usage_estimate(data.get("usage")) if isinstance(data, dict) else None
            archive_ok = (isinstance(archive, dict) and archive.get("call_id") == call
                          and archive.get("case_id") == case_id and archive.get("http_status") == status
                          and re.fullmatch(r"[0-9a-f]{64}", archive.get("sha256", "")))
            accepted = (status == 200 and isinstance(data, dict) and data.get("model") == MODEL
                        and archive_ok and estimate is not None and estimate <= money(state["reserved"][call]))
            entry = {"call_id": call, "case_id": case_id, "phase": PHASE, "http_status": status,
                     "requested_model": MODEL, "billing_receipt_available": False,
                     "estimated_standard_cost_usd": str(estimate) if estimate is not None else None,
                     "estimated_cost_basis": "conservative reported usage x list tariff; not billed",
                     "reservation_disposition": "settled_provisional_estimate" if accepted else "retained_uncertain",
                     "response_archive": archive if archive_ok else None}
            if accepted:
                state["estimated_spent_usd"] = str(money(state.get("estimated_spent_usd", "0")) + estimate)
                del state["reserved"][call]
            else:
                phase["enabled"] = False
                phase["stop_reason"] = "response_or_usage_uncertain_reconcile_no_implicit_retry"
            state["calls"].append(entry)
            del phase["in_flight"][call]
        return accepted
