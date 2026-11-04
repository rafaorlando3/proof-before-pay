"""Devnet Memo only: durable signature before one send, then read-only reconciliation.

No transfer instruction, mainnet endpoint, airdrop, implicit key creation or retry
is available here. The optional solders dependency is loaded only when enabled.
"""
from pathlib import Path
import base64
import fcntl
import json
import os
import re
import stat
import time
import urllib.error
import urllib.request
import uuid

DEVNET = "https://api.devnet.solana.com"
MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("devnet_redirect_denied")


def rpc_call(method, params):
    request = urllib.request.Request(DEVNET, data=json.dumps({"jsonrpc": "2.0", "id": 1,
        "method": method, "params": params}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=10) as response:
        raw = response.read(200001)
    if len(raw) > 200000:
        raise ValueError("devnet_response_bound")
    body = json.loads(raw)
    if not isinstance(body, dict) or "error" in body or "result" not in body:
        raise ValueError("devnet_rpc_unconfirmed")
    return body["result"]


def private_file(path):
    source = Path(path)
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        meta = os.fstat(stream.fileno())
        if not stat.S_ISREG(meta.st_mode) or meta.st_mode & 0o077 or meta.st_size > 8192:
            raise ValueError("private_regular_file_required")
        return stream.read()


def save(directory, path, value):
    temporary = directory / (".memo-" + uuid.uuid4().hex)
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "w") as stream:
        json.dump(value, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def build_transaction(key_bytes, memo, blockhash):
    from solders.hash import Hash
    from solders.instruction import AccountMeta, Instruction
    from solders.keypair import Keypair
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    numbers = json.loads(key_bytes)
    if not isinstance(numbers, list) or len(numbers) != 64 or any(type(x) is not int or not 0 <= x <= 255 for x in numbers):
        raise ValueError("devnet_keypair_shape")
    payer = Keypair.from_bytes(bytes(numbers))
    recent = Hash.from_string(blockhash)
    instruction = Instruction(Pubkey.from_string(MEMO_PROGRAM), memo.encode(),
                              [AccountMeta(payer.pubkey(), is_signer=True, is_writable=True)])
    message = Message.new_with_blockhash([instruction], payer.pubkey(), recent)
    transaction = Transaction([payer], message, recent)
    return base64.b64encode(bytes(transaction)).decode(), str(transaction.signatures[0])


def reconcile(state, rpc):
    result = rpc("getTransaction", [state["signature"], {"encoding": "jsonParsed",
                  "commitment": "confirmed", "maxSupportedTransactionVersion": 0}])
    if result is None:
        return False
    if not isinstance(result, dict) or not isinstance(result.get("meta"), dict) or result["meta"].get("err") is not None:
        raise ValueError("devnet_transaction_not_verified")
    transaction = result.get("transaction", {})
    if transaction.get("signatures", [None])[0] != state["signature"]:
        raise ValueError("devnet_readback_signature_mismatch")
    instructions = result.get("transaction", {}).get("message", {}).get("instructions", [])
    # The signed transaction created here contains exactly one Memo instruction.
    if len(instructions) != 1 or instructions[0].get("programId") != MEMO_PROGRAM or instructions[0].get("parsed") != state["memo"]:
        raise ValueError("devnet_memo_readback_mismatch")
    state.update(state="confirmed", slot=result.get("slot"), confirmed_at=time.time())
    return True


def anchor(commitment, key_file, state_directory, enabled=False, *, rpc=rpc_call, build=build_transaction, wait=time.sleep, polls=15):
    if not (enabled is True or type(enabled) is int and enabled == 1):
        return {"ok": False, "state": "disabled", "reason": "devnet_adapter_not_configured", "cluster": "devnet"}
    if not isinstance(commitment, str) or not re.fullmatch(r"[0-9a-f]{64}", commitment):
        raise ValueError("commitment_required")
    directory = Path(state_directory)
    meta = directory.lstat()
    if directory.is_symlink() or not stat.S_ISDIR(meta.st_mode) or meta.st_mode & 0o077:
        raise ValueError("private_state_directory_required")
    lock = os.open(directory / "memo.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(lock).st_mode & 0o077:
            raise ValueError("private_state_lock_required")
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = directory / (commitment + ".json")
        try:
            state = json.loads(private_file(path))
        except FileNotFoundError:
            state = None
        memo = "pbp1:" + commitment
        if state is not None:
            if (state.get("commitment") != commitment or state.get("memo") != memo or state.get("cluster_url") != DEVNET
                    or state.get("state") not in {"prepared", "submitted", "uncertain", "confirmed"}
                    or not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{80,90}", state.get("signature", ""))):
                raise ValueError("existing_anchor_intent_invalid_no_reset")
        else:
            key = private_file(key_file)
            latest = rpc("getLatestBlockhash", [{"commitment": "confirmed"}])
            encoded, signature = build(key, memo, latest["value"]["blockhash"])
            key = None
            if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{80,90}", signature):
                raise ValueError("transaction_signature_required")
            state = {"commitment": commitment, "memo": memo, "signature": signature,
                     "cluster_url": DEVNET, "state": "prepared", "created_at": time.time()}
            save(directory, path, state)  # BEFORE the only sendTransaction.
            try:
                returned = rpc("sendTransaction", [encoded, {"encoding": "base64", "skipPreflight": False,
                         "preflightCommitment": "confirmed", "maxRetries": 0}])
                if returned != signature:
                    raise ValueError("returned_signature_mismatch")
                state["state"] = "submitted"
            except Exception:
                state["state"] = "uncertain"
            save(directory, path, state)
        for index in range(polls):
            try:
                if reconcile(state, rpc):
                    save(directory, path, state)
                    return {"ok": True, "state": "confirmed", "cluster": "devnet", "commitment": commitment,
                            "signature": state["signature"], "memo": memo, "slot": state.get("slot"),
                            "on_chain_verified": True, "authorizes_payment": False,
                            "explorer": "https://explorer.solana.com/tx/" + state["signature"] + "?cluster=devnet"}
            except Exception:
                break
            if index + 1 < polls:
                wait(1)
        return {"ok": False, "state": state["state"], "cluster": "devnet", "signature": state["signature"],
                "reason": "reconcile_existing_signature_no_resend", "authorizes_payment": False}
    finally:
        os.close(lock)


def anchor_json(commitment, key_file, state_directory, enabled=False):
    try:
        result = anchor(commitment, key_file, state_directory, enabled)
    except Exception:
        result = {"ok": False, "state": "unavailable", "cluster": "devnet",
                  "reason": "devnet_adapter_configuration_or_state_unavailable", "authorizes_payment": False}
    return json.dumps(result, allow_nan=False)
