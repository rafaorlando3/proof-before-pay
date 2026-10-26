import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from pbp_seal import SealError, SealStore, commitment, memo_for, parse_memo, seal, validate, verify  # noqa: E402
from fixtures import approval, decision, rule_change  # noqa: E402

SALT = "11" * 32
SALT2 = "22" * 32


def reason(fn):
    with pytest.raises(SealError) as e:
        fn()
    return e.value.reason, e.value.path


def test_valid_decision_seals_and_memo_roundtrip():
    s = seal(decision(), SALT)
    assert len(s["commitment"]) == 64 and s["memo"] == "pbp1:" + s["commitment"]
    assert parse_memo(s["memo"]) == s["commitment"]
    assert parse_memo("hello") is None and parse_memo("pbp1:XYZ") is None


def test_key_order_does_not_change_commitment():
    a = decision()
    b = json.loads(json.dumps(a, sort_keys=True))
    b = dict(reversed(list(b.items())))
    assert commitment(a, SALT) == commitment(b, SALT)


def test_salt_changes_commitment():
    assert commitment(decision(), SALT) != commitment(decision(), SALT2)


@pytest.mark.parametrize("mutate", [
    lambda r: r["decision"].__setitem__("rationale", r["decision"]["rationale"] + "!"),
    lambda r: r["saw"]["tools"][0]["output"].__setitem__("delivered", True),
    lambda r: r.__setitem__("missing", {"payer_message": None}),  # someone "completes" the dossier later
    lambda r: r["decision"].__setitem__("amount_minor", "15991"),
])
def test_any_edit_changes_commitment(mutate):
    r = decision()
    c = commitment(r, SALT)
    r2 = copy.deepcopy(r)
    mutate(r2)
    assert commitment(r2, SALT) != c


def test_sealed_ignorance_values_must_be_null():
    r = decision(missing={"delivery_photo": "photo:123"})
    assert reason(lambda: validate(r)) == ("missing_value_must_be_null", "$.missing.delivery_photo")


def test_tool_output_is_required():
    r = decision()
    del r["saw"]["tools"][0]["output"]
    assert reason(lambda: validate(r)) == ("missing_field", "$.saw.tools[0].output")


def test_floats_only_where_allowed():
    r = decision()
    r["saw"]["inputs"]["order_amount"] = 159.9
    assert reason(lambda: validate(r)) == ("float_not_allowed", "$.saw.inputs.order_amount")


def test_money_above_limit_needs_human():
    r = decision()
    r["decision"]["requires_human"] = False
    assert reason(lambda: validate(r)) == ("money_above_limit_without_human", "$.decision.requires_human")


def test_bounded_autonomy_within_limit_is_allowed():
    r = decision(limits={"autonomous_minor": "20000", "currency": "BRL"})
    r["decision"]["requires_human"] = False
    validate(r)  # 159,90 <= 200,00: the agent may pay alone, and the seal comes first
    r["decision"]["amount_minor"] = "20001"
    assert reason(lambda: validate(r))[0] == "money_above_limit_without_human"
    del r["decision"]["amount_minor"]
    assert reason(lambda: validate(r))[0] == "money_above_limit_without_human"  # unknown amount = above limit


def test_forbidden_must_be_sorted_unique_and_not_chosen():
    assert reason(lambda: validate(decision(forbidden=["credit_customer", "accept_as_paid"])))[0] == "not_sorted_unique"
    r = decision(forbidden=["accept_as_paid", "refund_duplicate"])
    assert reason(lambda: validate(r)) == ("action_is_forbidden", "$.decision.action")


def test_unknown_fields_rejected():
    assert reason(lambda: validate(decision(extra=1)))[0] == "unknown_field"


@pytest.mark.parametrize("value,kind", [
    ("cliente 529.982.247-25 pagou", "cpf"),
    ("CNPJ 11.222.333/0001-81", "cnpj"),
    ("mail fulano@example.com", "email"),
    ("tel +55 11 98765-4321", "phone"),
    ("tel +595 981 123 456", "phone"),
])
def test_personal_data_blocks_sealing(value, kind):
    r = decision()
    r["saw"]["tools"][1]["output"]["note"] = value
    with pytest.raises(SealError) as e:
        seal(r, SALT)
    assert e.value.reason == "personal_data_found"
    assert any(f["kind"] == kind for f in e.value.findings)
    assert value not in str(e.value) and value not in json.dumps(e.value.findings)


def test_invalid_cpf_digits_are_not_flagged():
    r = decision()
    r["saw"]["tools"][1]["output"]["note"] = "ref 529.982.247-26"  # wrong check digit
    validate(r)


def test_pix_random_key_flagged_only_under_pix_keys():
    r = decision()
    r["saw"]["inputs"]["pix_key"] = "123e4567-e89b-42d3-a456-426614174000"
    assert reason(lambda: validate(r))[0] == "personal_data_found"
    r2 = decision()
    r2["saw"]["inputs"]["trace_id"] = "123e4567-e89b-42d3-a456-426614174000"
    validate(r2)


def test_approval_and_rule_change_kinds():
    d = seal(decision(), SALT)["commitment"]
    a = seal(approval(d, d), SALT2)["commitment"]
    seal(rule_change(d, a), SALT)
    bad = approval(d, d)
    bad["human"]["outcome"] = "maybe"
    assert reason(lambda: validate(bad))[0] == "bad_outcome"


def test_chain_detects_edit_and_bad_link(tmp_path):
    st = SealStore(str(tmp_path / "seals.jsonl"))
    e1 = st.append(decision())
    e2 = st.append(approval(e1["commitment"], e1["commitment"]))
    st.append(rule_change(e1["commitment"], e2["commitment"]))
    assert st.verify_chain() == {"ok": True, "checked": 3}
    with pytest.raises(SealError):
        st.append(decision())  # prev must be the head
    lines = (tmp_path / "seals.jsonl").read_text().splitlines()
    ent = json.loads(lines[1])
    ent["record"]["human"]["outcome"] = "rejected"
    lines[1] = json.dumps(ent, sort_keys=True)
    (tmp_path / "seals.jsonl").write_text("\n".join(lines) + "\n")
    res = st.verify_chain()
    assert res["ok"] is False and res["broken_at"] == 1 and res["reason"] == "commitment_mismatch"


def test_verify_four_states():
    r = decision()
    c = commitment(r, SALT)
    ok = lambda sig: {"memo": memo_for(c), "slot": 10, "block_time": 1_000}  # noqa: E731
    assert verify(r, SALT, None)["state"] == "pending"
    assert verify(r, SALT, "sig", fetch=ok)["state"] == "sealed"
    assert verify(r, SALT, "sig", fetch=ok, money_moved_at=1_001)["state"] == "sealed"
    late = verify(r, SALT, "sig", fetch=ok, money_moved_at=999)
    assert (late["state"], late["reason"]) == ("tampered", "sealed_after_money_moved")
    r2 = copy.deepcopy(r)
    r2["decision"]["rationale"] = "Edited after the fact to look better."
    t = verify(r2, SALT, "sig", fetch=ok)
    assert (t["state"], t["reason"]) == ("tampered", "commitment_mismatch")
    other = verify(r, SALT, "sig", fetch=lambda s: {"memo": "gm", "slot": 1, "block_time": 1})
    assert (other["state"], other["reason"]) == ("unverifiable", "anchor_memo_not_pbp")
