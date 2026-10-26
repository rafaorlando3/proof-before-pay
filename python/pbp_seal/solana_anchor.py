"""Anchor a commitment on Solana with the SPL Memo program and read it back.

Only `pbp1:<commitment>` goes on chain. Works with a local `solana-test-validator`, devnet or mainnet (the demo
never uses mainnet). No durable nonce: a fresh blockhash per transaction (durable nonces are scheduled for
removal, see solana.com/upgrades/durable-nonce-deprecation). Every RPC error is returned with the body it sent.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any

from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction

from .record import parse_memo

MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
DEVNET = "https://api.devnet.solana.com"
LOCAL = "http://127.0.0.1:8899"


class RpcError(RuntimeError):
    def __init__(self, reason: str, body: Any = None):
        self.reason, self.body = reason, body
        super().__init__(f"{reason}: {json.dumps(body)[:500] if body is not None else ''}")


class Rpc:
    def __init__(self, url: str, timeout: float = 20.0):
        self.url, self.timeout = url, timeout

    def call(self, method: str, params: list | None = None) -> Any:
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
        req = urllib.request.Request(self.url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = json.loads(r.read(2_000_000))
        except urllib.error.HTTPError as e:
            raw = e.read(4000).decode("utf-8", "replace")
            raise RpcError(f"http_{e.code}:{method}", raw) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RpcError(f"network:{method}", str(e)) from e
        if "error" in body:
            raise RpcError(f"rpc_error:{method}", body["error"])
        return body.get("result")


def airdrop(rpc: Rpc, pubkey: Pubkey, lamports: int = 100_000_000, wait_s: float = 45) -> str:
    sig = rpc.call("requestAirdrop", [str(pubkey), lamports, {"commitment": "confirmed"}])
    _wait(rpc, sig, wait_s)
    return sig


def _wait(rpc: Rpc, sig: str, wait_s: float) -> dict:
    t0 = time.time()
    while time.time() - t0 < wait_s:
        st = rpc.call("getSignatureStatuses", [[sig], {"searchTransactionHistory": True}])["value"][0]
        if st:
            if st.get("err"):
                raise RpcError("tx_failed", st)
            if st.get("confirmationStatus") in ("confirmed", "finalized"):
                return st
        time.sleep(1.0)
    raise RpcError("confirm_timeout", {"signature": sig, "waited_s": wait_s})


def anchor(rpc: Rpc, payer: Keypair, memo: str, wait_s: float = 60) -> dict:
    """Send one Memo transaction. Returns {signature, slot, block_time, memo, cluster_url}."""
    if parse_memo(memo) is None:
        raise RpcError("not_a_pbp_memo", memo[:12])
    bh = rpc.call("getLatestBlockhash", [{"commitment": "confirmed"}])["value"]["blockhash"]
    ix = Instruction(MEMO_PROGRAM_ID, memo.encode(), [AccountMeta(payer.pubkey(), is_signer=True, is_writable=True)])
    msg = Message.new_with_blockhash([ix], payer.pubkey(), Hash.from_string(bh))
    tx = Transaction([payer], msg, Hash.from_string(bh))
    raw = base64.b64encode(bytes(tx)).decode()
    sig = rpc.call("sendTransaction", [raw, {"encoding": "base64", "preflightCommitment": "confirmed"}])
    st = _wait(rpc, sig, wait_s)
    got = fetch_memo(rpc, sig)
    if got["memo"] != memo:  # read back what the chain really holds
        raise RpcError("memo_readback_mismatch", {"signature": sig})
    return {"signature": sig, "slot": st.get("slot"), "block_time": got["block_time"], "memo": memo, "cluster_url": rpc.url}


def fetch_memo(rpc: Rpc, signature: str) -> dict:
    """Read the pbp memo of a transaction. Returns {memo, slot, block_time, signer}."""
    Signature.from_string(signature)  # raises on a malformed signature
    tx = rpc.call("getTransaction", [signature, {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}])
    if tx is None:
        raise RpcError("anchor_tx_not_found", {"signature": signature})
    if tx.get("meta", {}).get("err"):
        raise RpcError("anchor_tx_failed", tx["meta"]["err"])
    memo = None
    for ix in tx["transaction"]["message"]["instructions"]:
        if ix.get("programId") == str(MEMO_PROGRAM_ID):
            memo = ix.get("parsed") if isinstance(ix.get("parsed"), str) else None
    keys = tx["transaction"]["message"].get("accountKeys", [])
    signer = next((k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")), None)
    return {"memo": memo, "slot": tx.get("slot"), "block_time": tx.get("blockTime"), "signer": signer}
