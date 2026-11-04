"""Fixed public fixtures -> one native intake -> an intact LIVE decision seal.

Uses only the operator's existing loopback relay. It never reviews a case,
approves a permit, calls a provider directly or retries intake after ambiguity.
The native production must advertise the dedicated, non-autonomous demo route.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import datetime as dt

from live_budget import MODEL, require

FIXTURES = {
    "amount_conflict": ("pix-0005.json", "c1eea3d5c74967c6aaa83783dd80d1e86f67490c4bfc0c426b9e5dfb1ea33820"),
    "missing_evidence": ("pix-0006.json", "d8ebff2486892ad59766250ea7edbf31a56786537265adac155989c7aee65432"),
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("native_relay_redirect_denied")


class NativeRelay:
    def __init__(self, base="http://127.0.0.1:18878", *, expected_revision):
        url = urllib.parse.urlsplit(base)
        require(url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost"}
                and not (url.username or url.password or url.path or url.query or url.fragment), "existing_loopback_relay_required")
        require(isinstance(expected_revision, str) and re.fullmatch(r"[0-9a-f]{40}", expected_revision), "pinned_native_revision_required")
        self.base, self.revision = base, expected_revision
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, path, body=None, missing=False):
        raw = None if body is None else json.dumps(body, allow_nan=False).encode()
        request = urllib.request.Request(self.base + path, data=raw,
                  headers={"Content-Type": "application/json", "X-PBP-Request": "1"},
                  method="GET" if raw is None else "POST")
        try:
            response = self.opener.open(request, timeout=12)
        except urllib.error.HTTPError as error:
            if missing and error.code == 404:
                error.close()
                return None
            error.close()
            raise ValueError("native_relay_rejected") from None
        with response:
            raw = response.read(2_000_001)
            require(len(raw) <= 2_000_000, "native_response_bound")
            data = json.loads(raw)
            require(isinstance(data, dict) and data.get("ok") is True, "native_response_not_ok")
            return data

    def ready(self):
        health = self.request("/pbp/api/health")
        profile = health.get("public_live_demo") or {}
        return (health.get("production_running") is True and profile.get("enabled") is True
                and profile.get("model") == MODEL and profile.get("case_prefix") == "public-live:"
                and profile.get("transport") == "private_budget_bridge"
                and profile.get("autonomous_effects") is False
                and profile.get("source_revision") == self.revision)

    def lookup(self, case_id):
        return self.request("/pbp/api/cases/" + urllib.parse.quote(case_id, safe=""), missing=True)

    def submit(self, payload):
        return self.request("/pbp/api/cases", payload)


class NativeRunner:
    def __init__(self, fixtures, state, relay, *, timeout=240, clock=time.monotonic, wait=time.sleep):
        require(type(timeout) in (int, float) and math.isfinite(timeout) and 1 <= timeout <= 240, "bounded_native_wait_required")
        self.fixtures, self.state, self.relay = Path(fixtures), Path(state), relay
        self.timeout, self.clock, self.wait = timeout, clock, wait
        self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(not self.state.is_symlink() and not self.state.stat().st_mode & 0o077, "private_native_attempt_directory_required")

    def payload(self, scenario, token):
        require(scenario in FIXTURES and isinstance(token, str) and re.fullmatch(r"[A-Za-z0-9_-]{16,48}", token), "fixed_public_scenario_required")
        name, digest = FIXTURES[scenario]
        source = (self.fixtures / name).read_bytes()
        require(hashlib.sha256(source).hexdigest() == digest, "public_fixture_revision_changed")
        payload = json.loads(source)
        require(payload.get("environment") == "sandbox", "synthetic_fixture_required")
        payload["case_id"] = "public-live:" + token
        payload["order"]["id"] = "public-order:" + token
        for index, payment in enumerate(payload["payments"]):
            payment["payment_ref"] = "pix:public:" + token + ":" + str(index)
        return payload, name, digest

    def marker(self, token, data, *, initial=False):
        target = self.state / (token + ".json")
        path = target if initial else self.state / (".update-" + uuid.uuid4().hex)
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "w") as stream:
            json.dump(data, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        if not initial:
            os.replace(path, target)
        directory = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    @staticmethod
    def sealed_result(document, case_id):
        case, decision = document.get("case"), document.get("decision")
        require(isinstance(case, dict) and case.get("case_id") == case_id
                and case.get("input", {}).get("environment") == "sandbox", "native_case_scope_mismatch")
        if not isinstance(decision, dict) or not decision.get("commitment"):
            require(case.get("status") != "blocked", "native_case_blocked")
            return None
        model = decision.get("model") or {}
        require(decision.get("source") == "model" and model.get("mode") == "live" and model.get("id") == MODEL,
                "fresh_native_live_decision_required")
        require(decision.get("proposal_refused") is False and not decision.get("proposal_reason")
                and isinstance(decision.get("proposal"), dict)
                and type((decision.get("usage") or {}).get("tool_calls")) is int
                and decision["usage"]["tool_calls"] >= 5, "validated_proposal_and_five_observed_tools_required")
        require(decision.get("moves_money") is False and not document.get("receipt") and not document.get("permit"), "nonfinancial_demo_result_required")
        commitment = decision["commitment"]
        require(isinstance(commitment, str) and re.fullmatch(r"[0-9a-f]{64}", commitment), "native_commitment_required")
        seals = document.get("seals") or []
        if not any(seal.get("commitment") == commitment and seal.get("kind") == "decision"
                   and seal.get("verification", {}).get("state") == "intact"
                   and seal.get("money_moved_before_seal") is False for seal in seals):
            return None
        session = case.get("session_id")
        require(type(session) in (str, int) and re.fullmatch(r"[0-9]{1,18}", str(session)), "native_session_required")
        return {"mode": "live", "case_id": case_id, "commitment": commitment, "session_id": str(session)}

    def __call__(self, scenario, token):
        payload, fixture, digest = self.payload(scenario, token)
        case_id = payload["case_id"]
        require(self.relay.ready() is True, "dedicated_native_demo_route_not_ready")
        require(self.relay.lookup(case_id) is None, "native_case_already_exists_reconcile")
        marker = {"case_id": case_id, "scenario": scenario, "fixture": fixture,
                  "fixture_sha256": digest, "state": "submission_attempt_recorded",
                  "at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "payload_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                  "no_automatic_retry": True}
        # Durable exclusive intent BEFORE the sole native intake. Existing intent
        # is never removed or overwritten to manufacture a clean retry.
        self.marker(token, marker, initial=True)
        reply = self.relay.submit(payload)
        require(reply.get("case_id") == case_id, "native_intake_identity_unconfirmed")
        deadline = self.clock() + self.timeout
        for _ in range(math.ceil(self.timeout) + 1):
            if self.clock() > deadline:
                break
            document = self.relay.lookup(case_id)
            if document is not None:
                result = self.sealed_result(document, case_id)
                if result is not None:
                    marker.update(state="sealed_live_result_observed", result=result)
                    self.marker(token, marker)
                    return result
            self.wait(1)
        raise ValueError("native_result_unconfirmed_reconcile_no_retry")
