"""Private Gemini transport. Not started by the viewer or imported as a service.

Deployment requires an explicit budget phase and an operator-only credential
file. The real key stays on this host. The native SDK uses a non-secret local
placeholder; peer allowlisting, case arming and budget admission are mandatory.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import ipaddress
import json
import os
import stat
import threading
import time
import urllib.error
import urllib.request

from live_budget import BudgetDenied, LiveBudget, MODEL, require

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
LOCAL_TOKEN = "pbp-public-live-local-placeholder-not-a-provider-key"
MAX_RESPONSE = 1_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise BudgetDenied("provider_redirect_denied")


class PrivateProvider:
    def __init__(self, budget, provider_key, *, send=None, wait=time.sleep):
        require(isinstance(provider_key, str) and len(provider_key) >= 32, "private_provider_credential_required")
        self.budget, self.key = budget, provider_key
        self.send = send or self._send
        self.wait = wait
        self.slot = threading.Lock()
        self.archive = budget.directory / "public-live-responses"
        self.archive.mkdir(mode=0o700, exist_ok=True)
        require(not self.archive.is_symlink() and not self.archive.stat().st_mode & 0o077, "private_response_archive_required")

    def _send(self, raw):
        request = urllib.request.Request(ENDPOINT, data=raw, method="POST",
                  headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
        opener = urllib.request.build_opener(NoRedirect())
        try:
            response = opener.open(request, timeout=55)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(MAX_RESPONSE + 1)
            require(len(body) <= MAX_RESPONSE, "provider_response_bound")
            return response.status, body

    def archive_response(self, call, case_id, status, raw):
        require(isinstance(raw, bytes) and len(raw) <= MAX_RESPONSE, "provider_response_bound")
        require(self.key.encode() not in raw, "provider_secret_in_response")
        path = self.archive / (call + ".json")
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(self.archive, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return {"call_id": call, "case_id": case_id, "http_status": status,
                "path": "public-live-responses/" + path.name,
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

    @staticmethod
    def failure(reason, status=503):
        # Never forward exception text, keys, upstream errors or historical data.
        return status, json.dumps({"error": {"message": reason, "type": "public_live_unavailable"}}).encode()

    def complete(self, body):
        if not self.slot.acquire(blocking=False):
            return self.failure("one_live_HTTP_at_a_time", 429)
        call = None
        try:
            # Arming is an operator/worker action under the authoritative lock,
            # never a case_id or URL accepted from the HTTP caller.
            case_id = self.budget.armed_case()
            try:
                call, raw = self.budget.admit(body, case_id)
            except BudgetDenied as error:
                if str(error) != "HTTP_rate_limit_wait":
                    raise
                # Pace before admission. This is NOT a retry of a provider call.
                self.wait(15)
                call, raw = self.budget.admit(body, case_id)
            try:
                status, response = self.send(raw)
                archive = self.archive_response(call, case_id, status, response)
                data = json.loads(response)
            except Exception:
                self.budget.settle(call)
                return self.failure("provider_result_uncertain_reservation_retained", 502)
            accepted = self.budget.settle(call, status=status, data=data, archive=archive)
            if not accepted:
                return self.failure("provider_evidence_or_usage_uncertain_reservation_retained", 502)
            return 200, response
        except BudgetDenied as error:
            # All BudgetDenied reasons are local fixed constants, not provider text.
            return self.failure(str(error), 429 if str(error) == "HTTP_quota_reached" else 503)
        except Exception:
            # A crash/failed accounting write retains any admitted in-flight hold.
            return self.failure("accounting_unavailable_reconcile_before_retry", 503)
        finally:
            self.slot.release()


def create_server(directory, credential_path, bind, port, clients, *, send=None, wait=time.sleep):
    address = ipaddress.ip_address(bind)
    require(address.is_private and not address.is_unspecified, "explicit_private_bind_required")
    allowed = frozenset(str(ipaddress.ip_address(x)) for x in clients)
    require(bool(allowed) and all(ipaddress.ip_address(x).is_private for x in allowed), "private_peer_allowlist_required")
    path = Path(credential_path)
    require(not path.is_symlink(), "private_credential_file_required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "r") as stream:
        metadata = os.fstat(stream.fileno())
        require(stat.S_ISREG(metadata.st_mode) and not metadata.st_mode & 0o077 and metadata.st_size < 4096, "private_credential_file_required")
        key = stream.read().strip()
    provider = PrivateProvider(LiveBudget(directory), key, send=send, wait=wait)
    key = None

    class Handler(BaseHTTPRequestHandler):
        timeout = 10

        def log_message(self, *args):
            pass

        def reply(self, status, body):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if (self.client_address[0] not in allowed or self.path not in {"/chat/completions", "/v1/chat/completions"}
                    or self.headers.get("Authorization") != "Bearer " + LOCAL_TOKEN
                    or self.headers.get("Content-Type", "").split(";")[0] != "application/json"
                    or self.headers.get("Transfer-Encoding")):
                return self.reply(*provider.failure("private_route_denied", 403))
            try:
                size = int(self.headers.get("Content-Length", "-1"))
                require(0 < size <= 40000, "bounded_JSON_required")
                raw = self.rfile.read(size)
                require(len(raw) == size, "complete_JSON_required")
                body = json.loads(raw)
            except Exception:
                return self.reply(*provider.failure("invalid_bounded_JSON", 400))
            self.reply(*provider.complete(body))

        def do_GET(self):
            if self.client_address[0] not in allowed:
                return self.reply(*provider.failure("private_route_denied", 403))
            # Build154 discovers its configured model before inference. These
            # static local allow-list facts neither contact Google nor assert
            # upstream availability; no key, usage or budget data is returned.
            model = {"id": MODEL, "object": "model", "created": 0,
                     "owned_by": "local-allowlist-not-provider-observation"}
            if self.path in {"/models", "/v1/models"}:
                return self.reply(200, json.dumps({"object": "list", "data": [model]}).encode())
            if self.path in {"/models/" + MODEL, "/v1/models/" + MODEL}:
                return self.reply(200, json.dumps(model).encode())
            self.reply(*provider.failure("private_route_denied", 404))

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        slots = threading.BoundedSemaphore(2)

        def process_request(self, request, address):
            if not self.slots.acquire(blocking=False):
                request.close()
                return
            try:
                super().process_request(request, address)
            except BaseException:
                self.slots.release()
                raise

        def process_request_thread(self, request, address):
            try:
                super().process_request_thread(request, address)
            finally:
                self.slots.release()

    return Server((bind, port), Handler)


def serve(directory, credential_path, bind, port, clients):
    create_server(directory, credential_path, bind, port, clients).serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Private, budget-controlled public-demo provider bridge")
    parser.add_argument("--budget-directory", required=True)
    parser.add_argument("--credential-file", required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18881)
    parser.add_argument("--client", action="append", required=True)
    args = parser.parse_args()
    serve(args.budget_directory, args.credential_file, args.bind, args.port, args.client)
