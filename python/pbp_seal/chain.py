"""Local hash chain: the default seal when no blockchain is configured (README opens here; no wallet needed).

Each entry links to the previous commitment ($.prev). Editing any stored record or salt breaks the chain at
that entry, and verify_chain() says where and why. Entries can later get a Solana anchor (signature).
"""
from __future__ import annotations

import json
import os
from typing import Any

from .record import SealError, commitment, memo_for, seal


class SealStore:
    def __init__(self, path: str):
        self.path = path

    def entries(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as e:  # report the line, never guess
                    raise SealError("store_line_not_json", f"line:{n}") from e
        return out

    def head(self) -> str | None:
        e = self.entries()
        return e[-1]["commitment"] if e else None

    def append(self, record: dict, salt_hex: str | None = None) -> dict:
        if record.get("prev") != self.head():
            raise SealError("prev_is_not_head", "$.prev")
        s = seal(record, salt_hex)
        entry = {"commitment": s["commitment"], "salt": s["salt"], "record": record, "anchor": None}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        return entry

    def set_anchor(self, c: str, anchor: dict[str, Any]) -> None:
        es = self.entries()
        hit = [e for e in es if e["commitment"] == c]
        if not hit:
            raise SealError("commitment_not_in_store", "$commitment")
        hit[0]["anchor"] = anchor
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for e in es:
                f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(tmp, self.path)

    def verify_chain(self) -> dict:
        """Recompute every commitment and link. Returns {ok, checked, broken_at?, reason?}."""
        prev = None
        es = self.entries()
        for i, e in enumerate(es):
            try:
                c = commitment(e["record"], e["salt"])
            except SealError as err:
                return {"ok": False, "checked": i, "broken_at": i, "reason": f"invalid_record:{err.reason}"}
            if c != e["commitment"]:
                return {"ok": False, "checked": i, "broken_at": i, "reason": "commitment_mismatch"}
            if e["record"].get("prev") != prev:
                return {"ok": False, "checked": i, "broken_at": i, "reason": "prev_link_broken"}
            if e.get("anchor") and e["anchor"].get("memo") not in (None, memo_for(c)):
                return {"ok": False, "checked": i, "broken_at": i, "reason": "anchor_memo_mismatch"}
            prev = c
        return {"ok": True, "checked": len(es)}
