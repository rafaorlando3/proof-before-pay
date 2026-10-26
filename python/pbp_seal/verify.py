"""Public verification: four states for the verification page.

    sealed      (green)  the record + salt hash to the commitment held on chain
    tampered    (red)    the record or salt changed after sealing, or the seal came after the money moved
    pending     (yellow) sealed locally, not anchored on chain yet
    unverifiable (grey)  the anchor could not be read (reason says why)
"""
from __future__ import annotations

from typing import Any, Callable

from .record import SealError, commitment, parse_memo
from .solana_anchor import Rpc, RpcError, fetch_memo


def verify(record: dict, salt_hex: str, anchor_signature: str | None, rpc: Rpc | None = None,
           money_moved_at: int | None = None, fetch: Callable[[str], dict] | None = None) -> dict[str, Any]:
    try:
        c = commitment(record, salt_hex)
    except SealError as e:
        return {"state": "tampered", "reason": f"invalid_record:{e.reason}", "path": e.path}
    if not anchor_signature:
        return {"state": "pending", "reason": "not_anchored", "commitment": c}
    getter = fetch or (lambda s: fetch_memo(rpc, s))  # type: ignore[arg-type]
    try:
        got = getter(anchor_signature)
    except RpcError as e:
        return {"state": "unverifiable", "reason": e.reason, "commitment": c}
    except ValueError:
        return {"state": "unverifiable", "reason": "bad_signature_format", "commitment": c}
    on_chain = parse_memo(got.get("memo") or "")
    if on_chain is None:
        return {"state": "unverifiable", "reason": "anchor_memo_not_pbp", "commitment": c}
    if on_chain != c:
        return {"state": "tampered", "reason": "commitment_mismatch", "commitment": c, "on_chain": on_chain}
    bt = got.get("block_time")
    if money_moved_at is not None and (bt is None or bt > money_moved_at):
        return {"state": "tampered", "reason": "sealed_after_money_moved", "commitment": c, "block_time": bt}
    return {"state": "sealed", "reason": "ok", "commitment": c, "slot": got.get("slot"), "block_time": bt}
