"""Personal-data scanner. A record with personal data is never sealed: a hash on chain cannot be erased.

Detects valid CPF and CNPJ (check digits), e-mail, Brazilian and Paraguayan phone numbers, and Pix random keys
(UUID v4) under keys that mention pix/key. Findings report the JSON path and the kind, never the value.
"""
from __future__ import annotations

import re
from typing import Any

_CPF = re.compile(r"(?<!\d)(\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)")
_CNPJ = re.compile(r"(?<!\d)(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")
_PHONE = re.compile(r"(\+\s?55\s?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4})|(\(\d{2}\)\s?9?\d{4}-\d{4})|(\+\s?595\s?\(?\d{2,3}\)?\s?\d{3}[-\s]?\d{3,4})")
_UUID4 = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")


def _cpf_ok(s: str) -> bool:
    d = [int(c) for c in s if c.isdigit()]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for n in (9, 10):
        t = sum(d[i] * (n + 1 - i) for i in range(n)) * 10 % 11 % 10
        if t != d[n]:
            return False
    return True


def _cnpj_ok(s: str) -> bool:
    d = [int(c) for c in s if c.isdigit()]
    if len(d) != 14 or len(set(d)) == 1:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    for w, n in ((w1, 12), (w2, 13)):
        r = sum(a * b for a, b in zip(d[:n], w)) % 11
        if (0 if r < 2 else 11 - r) != d[n]:
            return False
    return True


def _scan_text(text: str, key_hint: str) -> list[str]:
    kinds = []
    if any(_cpf_ok(m.group(1)) for m in _CPF.finditer(text)):
        kinds.append("cpf")
    if any(_cnpj_ok(m.group(1)) for m in _CNPJ.finditer(text)):
        kinds.append("cnpj")
    if _EMAIL.search(text):
        kinds.append("email")
    if _PHONE.search(text):
        kinds.append("phone")
    if ("pix" in key_hint or "key" in key_hint or "chave" in key_hint) and _UUID4.search(text):
        kinds.append("pix_random_key")
    return kinds


def scan_pii(v: Any, path: str = "$", key_hint: str = "") -> list[dict]:
    out: list[dict] = []
    if isinstance(v, str):
        out += [{"path": path, "kind": k} for k in _scan_text(v, key_hint)]
    elif isinstance(v, dict):
        for k, x in v.items():
            out += [{"path": f"{path}.{k}", "kind": kk} for kk in _scan_text(str(k), "")]
            out += scan_pii(x, f"{path}.{k}", str(k).lower())
    elif isinstance(v, list):
        for i, x in enumerate(v):
            out += scan_pii(x, f"{path}[{i}]", key_hint)
    return out
