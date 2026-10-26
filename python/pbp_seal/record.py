"""Proof Before Pay: sealed decision records (spec pbp.seal/1).

A record says what an agent saw, what was missing, what it was not allowed to do and what it decided.
It is validated strictly, canonicalized with RFC 8785 (JCS) and committed with a random salt:

    commitment = sha256( b"pbp.seal/1\n" + salt_hex + b"\n" + JCS(record) )

Only the commitment goes on chain (Solana Memo "pbp1:<hex>"). Record and salt stay private (IRIS / PixSettle DB)
and are revealed to whoever needs to verify. Every rejection carries a stable reason code and a JSON path,
never the offending value (so errors never leak data).
"""
from __future__ import annotations

import hashlib
import re
import secrets
from typing import Any

import rfc8785

from .pii import scan_pii

SPEC = "pbp.seal/1"
MEMO_PREFIX = "pbp1:"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
_ID = re.compile(r"^[A-Za-z0-9_\-:.]{1,64}$")
_DIGITS = re.compile(r"^(0|[1-9]\d{0,17})$")
_CUR = re.compile(r"^[A-Z]{3}$")
MAX_SAFE_INT = 2**53 - 1
# Only these paths may hold non-integer numbers (JCS number formatting is exact for them; amounts are strings).
FLOAT_PATHS = {"$.decision.confidence", "$.model.temperature"}
KINDS = {"decision", "approval", "rule_change"}


class SealError(ValueError):
    """Validation failure. `reason` is a stable code, `path` a JSON path. The value itself is never included."""

    def __init__(self, reason: str, path: str = "$", findings: list[dict] | None = None):
        self.reason, self.path, self.findings = reason, path, findings or []
        super().__init__(f"{reason} at {path}")


def _need(obj: dict, key: str, typ, path: str):
    if key not in obj:
        raise SealError("missing_field", f"{path}.{key}")
    if not isinstance(obj[key], typ) or (typ is int and isinstance(obj[key], bool)):
        raise SealError("wrong_type", f"{path}.{key}")
    return obj[key]


def _only(obj: dict, allowed: set[str], path: str):
    extra = sorted(set(obj) - allowed)
    if extra:
        raise SealError("unknown_field", f"{path}.{extra[0]}")


def _walk_numbers(v: Any, path: str = "$"):
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return
    if isinstance(v, float):
        if path not in FLOAT_PATHS:
            raise SealError("float_not_allowed", path)
        if v != v or v in (float("inf"), float("-inf")):
            raise SealError("number_not_finite", path)
        return
    if isinstance(v, int):
        if abs(v) > MAX_SAFE_INT:
            raise SealError("int_out_of_safe_range", path)
        return
    if isinstance(v, dict):
        for k, x in v.items():
            if not isinstance(k, str):
                raise SealError("non_string_key", path)
            _walk_numbers(x, f"{path}.{k}")
        return
    if isinstance(v, list):
        for i, x in enumerate(v):
            _walk_numbers(x, f"{path}[{i}]")
        return
    raise SealError("unsupported_type", path)


def _sorted_unique_strings(v: Any, path: str):
    if not isinstance(v, list) or any(not isinstance(x, str) or not x for x in v):
        raise SealError("wrong_type", path)
    if v != sorted(set(v)):
        raise SealError("not_sorted_unique", path)


def _common(r: dict):
    if r.get("v") != SPEC:
        raise SealError("bad_spec_version", "$.v")
    if r.get("kind") not in KINDS:
        raise SealError("bad_kind", "$.kind")
    at = _need(r, "at", str, "$")
    if not _AT.match(at):
        raise SealError("bad_timestamp", "$.at")
    case = _need(r, "case", dict, "$")
    _only(case, {"id", "exception", "store"}, "$.case")
    if not _ID.match(_need(case, "id", str, "$.case")):
        raise SealError("bad_case_id", "$.case.id")
    _need(case, "exception", str, "$.case")
    if "store" in case and not isinstance(case["store"], str):
        raise SealError("wrong_type", "$.case.store")
    prev = r.get("prev", "absent")
    if prev == "absent":
        raise SealError("missing_field", "$.prev")
    if prev is not None and (not isinstance(prev, str) or not _HEX64.match(prev)):
        raise SealError("bad_prev", "$.prev")


def _decision(r: dict):
    _only(r, {"v", "kind", "case", "at", "saw", "missing", "policy", "rules", "model", "decision", "forbidden", "limits", "prev"}, "$")
    saw = _need(r, "saw", dict, "$")
    _only(saw, {"inputs", "tools"}, "$.saw")
    _need(saw, "inputs", dict, "$.saw")
    tools = _need(saw, "tools", list, "$.saw")
    for i, t in enumerate(tools):
        p = f"$.saw.tools[{i}]"
        if not isinstance(t, dict):
            raise SealError("wrong_type", p)
        _only(t, {"name", "args", "output"}, p)
        _need(t, "name", str, p)
        _need(t, "args", dict, p)
        if "output" not in t:  # the tool OUTPUT is sealed, not only the fact that a tool was called
            raise SealError("missing_field", f"{p}.output")
    missing = _need(r, "missing", dict, "$")  # sealed ignorance: evidence the agent did NOT have
    for k, v in missing.items():
        if v is not None:
            raise SealError("missing_value_must_be_null", f"$.missing.{k}")
    pol = _need(r, "policy", dict, "$")
    _only(pol, {"id", "version", "sha256"}, "$.policy")
    _need(pol, "id", str, "$.policy"); _need(pol, "version", str, "$.policy")
    if not _HEX64.match(_need(pol, "sha256", str, "$.policy")):
        raise SealError("bad_hash", "$.policy.sha256")
    if "rules" in r and r["rules"] is not None:
        _need(r, "rules", dict, "$")
        _only(r["rules"], {"engine", "version", "result"}, "$.rules")
    if "model" in r and r["model"] is not None:
        m = _need(r, "model", dict, "$")
        _only(m, {"provider", "id", "temperature", "mode"}, "$.model")
        _need(m, "provider", str, "$.model"); _need(m, "id", str, "$.model")
        if m.get("mode") not in ("live", "recorded"):
            raise SealError("bad_model_mode", "$.model.mode")
        t = m.get("temperature")
        if not isinstance(t, (int, float)) or isinstance(t, bool):
            raise SealError("wrong_type", "$.model.temperature")
    d = _need(r, "decision", dict, "$")
    _only(d, {"action", "moves_money", "amount_minor", "requires_human", "confidence", "rationale", "evidence_refs"}, "$.decision")
    _need(d, "action", str, "$.decision")
    moves = _need(d, "moves_money", bool, "$.decision")
    human = _need(d, "requires_human", bool, "$.decision")
    rat = _need(d, "rationale", str, "$.decision")
    if not 8 <= len(rat.strip()) <= 800:
        raise SealError("rationale_length", "$.decision.rationale")
    refs = _need(d, "evidence_refs", list, "$.decision")
    if not refs or any(not isinstance(x, str) for x in refs):
        raise SealError("evidence_refs_missing", "$.decision.evidence_refs")
    if "confidence" in d:
        c = d["confidence"]
        if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0 <= c <= 1:
            raise SealError("confidence_out_of_range", "$.decision.confidence")
    _sorted_unique_strings(_need(r, "forbidden", list, "$"), "$.forbidden")  # what the agent was NOT allowed to do
    if d["action"] in r["forbidden"]:
        raise SealError("action_is_forbidden", "$.decision.action")
    lim = _need(r, "limits", dict, "$")
    _only(lim, {"autonomous_minor", "currency"}, "$.limits")
    if not _DIGITS.match(_need(lim, "autonomous_minor", str, "$.limits")):
        raise SealError("bad_amount", "$.limits.autonomous_minor")
    if not _CUR.match(_need(lim, "currency", str, "$.limits")):
        raise SealError("bad_currency", "$.limits.currency")
    # Bounded autonomy: money moves without a person only if the amount is known and within the policy limit.
    if moves:
        amt = d.get("amount_minor")
        if amt is not None and (not isinstance(amt, str) or not _DIGITS.match(amt)):
            raise SealError("bad_amount", "$.decision.amount_minor")
        within = amt is not None and int(amt) <= int(lim["autonomous_minor"]) and lim["autonomous_minor"] != "0"
        if not within and not human:
            raise SealError("money_above_limit_without_human", "$.decision.requires_human")


def _approval(r: dict):
    _only(r, {"v", "kind", "case", "at", "human", "prev"}, "$")
    h = _need(r, "human", dict, "$")
    _only(h, {"operator", "outcome", "approves", "note"}, "$.human")
    if not _ID.match(_need(h, "operator", str, "$.human")):
        raise SealError("bad_operator_id", "$.human.operator")
    if h.get("outcome") not in ("approved", "rejected"):
        raise SealError("bad_outcome", "$.human.outcome")
    if not _HEX64.match(_need(h, "approves", str, "$.human")):
        raise SealError("bad_hash", "$.human.approves")
    if "note" in h and not isinstance(h["note"], str):
        raise SealError("wrong_type", "$.human.note")


def _rule_change(r: dict):
    _only(r, {"v", "kind", "case", "at", "rule", "author", "from_decision", "prev"}, "$")
    rule = _need(r, "rule", dict, "$")
    _only(rule, {"id", "version_from", "version_to", "diff_sha256"}, "$.rule")
    for k in ("id", "version_from", "version_to"):
        _need(rule, k, str, "$.rule")
    if not _HEX64.match(_need(rule, "diff_sha256", str, "$.rule")):
        raise SealError("bad_hash", "$.rule.diff_sha256")
    if not _ID.match(_need(r, "author", str, "$")):
        raise SealError("bad_operator_id", "$.author")
    if not _HEX64.match(_need(r, "from_decision", str, "$")):
        raise SealError("bad_hash", "$.from_decision")


def validate(record: Any) -> None:
    """Raise SealError (reason + path) if the record is not a valid pbp.seal/1 record or contains personal data."""
    if not isinstance(record, dict):
        raise SealError("record_not_object", "$")
    _walk_numbers(record)
    _common(record)
    {"decision": _decision, "approval": _approval, "rule_change": _rule_change}[record["kind"]](record)
    findings = scan_pii(record)
    if findings:
        raise SealError("personal_data_found", findings[0]["path"], findings)


def canonical(record: dict) -> bytes:
    return rfc8785.dumps(record)


def new_salt() -> str:
    return secrets.token_hex(32)


def commitment(record: dict, salt_hex: str, *, check: bool = True) -> str:
    if not isinstance(salt_hex, str) or not _HEX64.match(salt_hex):
        raise SealError("bad_salt", "$salt")
    if check:
        validate(record)
    pre = SPEC.encode() + b"\n" + salt_hex.encode() + b"\n" + canonical(record)
    return hashlib.sha256(pre).hexdigest()


def memo_for(c: str) -> str:
    if not _HEX64.match(c):
        raise SealError("bad_hash", "$commitment")
    return MEMO_PREFIX + c


def parse_memo(memo: str) -> str | None:
    """Return the commitment inside a pbp1 memo, or None if the memo is not ours."""
    if isinstance(memo, str) and memo.startswith(MEMO_PREFIX) and _HEX64.match(memo[len(MEMO_PREFIX):]):
        return memo[len(MEMO_PREFIX):]
    return None


def seal(record: dict, salt_hex: str | None = None) -> dict:
    """Validate and commit. Returns {commitment, salt, memo}. The caller stores record + salt privately."""
    s = salt_hex or new_salt()
    c = commitment(record, s)
    return {"commitment": c, "salt": s, "memo": memo_for(c)}
