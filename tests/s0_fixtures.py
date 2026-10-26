"""Fictitious, pseudonymized records shaped like real PixSettle exceptions (no personal data)."""
import copy

POLICY_SHA = "3f1c2a9b0d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8"


def decision(**over):
    r = {
        "v": "pbp.seal/1",
        "kind": "decision",
        "case": {"id": "case:01JA7Q3M2Z0K8V5R", "exception": "duplicate_payment", "store": "store-2"},
        "at": "2026-10-14T03:12:45.120Z",
        "saw": {
            "inputs": {"order_ref": "ord:7f3a", "order_amount_minor": "15990", "payments": [
                {"payment_ref": "pix:a1", "amount_minor": "15990", "payer": "payer:h9c2"},
                {"payment_ref": "pix:a2", "amount_minor": "15990", "payer": "payer:h9c2"}]},
            "tools": [
                {"name": "order.lookup", "args": {"order_ref": "ord:7f3a"}, "output": {"status": "paid", "delivered": False}},
                {"name": "payer.history", "args": {"payer": "payer:h9c2"}, "output": {"orders_90d": 4, "disputes_90d": 0}},
            ],
        },
        "missing": {"delivery_photo": None, "payer_message": None},
        "policy": {"id": "refunds", "version": "2026-10-01", "sha256": POLICY_SHA},
        "rules": {"engine": "iris-business-rules", "version": "r12", "result": None},
        "model": {"provider": "ai-hub", "id": "recorded-demo", "temperature": 0, "mode": "recorded"},
        "decision": {
            "action": "refund_duplicate", "moves_money": True, "amount_minor": "15990", "requires_human": True,
            "confidence": 0.92, "rationale": "Two identical Pix for one order from the same payer within 40 s.",
            "evidence_refs": ["pix:a1", "pix:a2"],
        },
        "forbidden": ["accept_as_paid", "credit_customer"],
        "limits": {"autonomous_minor": "0", "currency": "BRL"},
        "prev": None,
    }
    out = copy.deepcopy(r)
    for k, v in over.items():
        out[k] = v
    return out


def approval(approves: str, prev: str):
    return {"v": "pbp.seal/1", "kind": "approval", "case": {"id": "case:01JA7Q3M2Z0K8V5R", "exception": "duplicate_payment"},
            "at": "2026-10-14T03:13:10.004Z", "human": {"operator": "op:7", "outcome": "approved", "approves": approves}, "prev": prev}


def rule_change(from_decision: str, prev: str):
    return {"v": "pbp.seal/1", "kind": "rule_change", "case": {"id": "case:01JA7Q3M2Z0K8V5R", "exception": "duplicate_payment"},
            "at": "2026-10-14T03:14:00.000Z", "rule": {"id": "dup-same-payer-60s", "version_from": "r12", "version_to": "r13",
            "diff_sha256": "aa" * 32}, "author": "op:7", "from_decision": from_decision, "prev": prev}
