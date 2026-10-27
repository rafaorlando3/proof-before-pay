/// Unit tests for the deterministic rules and the policy loader. Run: do ##class(%UnitTest.Manager).RunTest("pbp/Test") or via tests/iris/production_smoke.py.
Class pbp.Test.Rules Extends %UnitTest.TestCase
{

Method Policy() As %DynamicObject
{
    Quit {"id": "t", "version": "1", "limits": {"autonomous_minor": "5000", "currency": "BRL"}, "allowed_actions": ["refund_duplicate", "accept_order", "accept_order_keep_credit", "release_order", "escalate_to_human"], "forbidden": ["delete_evidence", "change_policy"], "rules": {"small_diff_minor": "200", "late_grace_hours": "48"}}
}

Method Dup(amount As %String, recipient As %String = "test:p1") As %DynamicObject
{
    Set c = {"case_id": "t1", "store": "t", "exception": "duplicate_payment", "environment": "sandbox", "currency": "BRL", "order": {"id": "o", "amount_minor": (amount), "currency": "BRL", "status": "paid"}, "order_amount_minor": (amount), "payments": [{"payment_ref": "pix:E1", "amount_minor": (amount), "payer": "test:p1", "received_at": "2026-10-20T14:02:00.000Z"}, {"payment_ref": "pix:E2", "amount_minor": (amount), "payer": "test:p1", "received_at": "2026-10-20T14:03:00.000Z"}], "payer_history": {"orders_90d": 1}, "evidence": {"delivery_proof": null}}
    If recipient '= "" Set c."recipient_ref" = recipient
    Quit c
}

Method TestDuplicateWithinLimit()
{
    Set r = ##class(pbp.Rules).Evaluate(..Dup("1890"), ..Policy())
    Do $$$AssertTrue(r.decided, "rule decided")
    Do $$$AssertEquals(r.action, "refund_duplicate", "refund_duplicate")
    Do $$$AssertTrue(r."moves_money", "moves money")
    Do $$$AssertEquals(r."amount_minor", "1890", "amount is the duplicate")
    Do $$$AssertTrue(r."requires_human", "v1: every refund needs a reviewer")
    Do $$$AssertEquals(r."refund_payment_ref", "pix:E2", "the later payment is the duplicate")
    Do $$$AssertEquals(r."evidence_refs".%ToJSON(), "[""order"",""pix:E1"",""pix:E2""]", "evidence refs carry both payment refs")
    Do $$$AssertEquals(r.missing.%GetTypeOf("evidence.delivery_proof"), "null", "missing delivery proof sealed as null")
}

Method TestDuplicateAboveLimit()
{
    Set r = ##class(pbp.Rules).Evaluate(..Dup("129900"), ..Policy())
    Do $$$AssertTrue(r.decided && r."requires_human", "above limit requires human")
}

Method TestDuplicateOffsetsSelectTheSameInstantRegardlessOfArrayOrder()
{
    Set c=..Dup("8400")
    Set a=c.payments.%Get(0),b=c.payments.%Get(1)
    Set a."received_at"="2026-10-20T13:00:00+02:00"
    Set b."received_at"="2026-10-20T12:00:00Z"
    Set r=##class(pbp.Rules).Evaluate(c,..Policy())
    Do $$$AssertEquals(r."refund_payment_ref","pix:E2","UTC later payment, not lexical timestamp")
    Set c.payments=[(b),(a)]
    Set r=##class(pbp.Rules).Evaluate(c,..Policy())
    Do $$$AssertEquals(r."refund_payment_ref","pix:E2","array permutation preserves target")
}

Method TestDuplicateAmbiguousTimeDoesNotInventATarget()
{
    Set c=..Dup("8400")
    Set a=c.payments.%Get(0),b=c.payments.%Get(1)
    Set b."received_at"=a."received_at"
    Set r=##class(pbp.Rules).Evaluate(c,..Policy())
    Do $$$AssertEquals(r.action,"escalate_to_human","tie requires resolution")
    Do $$$AssertTrue('r."moves_money" && r."requires_human","no financial proposal for ambiguous time")
    Do $$$AssertEquals(r.missing.%GetTypeOf("refund_target"),"null","ambiguous target stays missing")
    Set b."received_at"="not-a-time"
    Set r=##class(pbp.Rules).Evaluate(c,..Policy())
    Do $$$AssertEquals(r.action,"escalate_to_human","malformed time fails closed")
}

Method TestDuplicateRecipientUnknown()
{
    Set r = ##class(pbp.Rules).Evaluate(..Dup("1890", ""), ..Policy())
    Do $$$AssertTrue(r.decided && r."requires_human", "unknown recipient requires human")
    Do $$$AssertEquals(r.missing.%GetTypeOf("refund_target"), "null", "refund target listed as missing (ledger blocks it)")
}

Method TestSmallOverpayment()
{
    Set c = {"exception": "amount_mismatch", "order": {"amount_minor": "4990", "status": "awaiting_payment"}, "payments": [{"payment_ref": "pix:A", "amount_minor": "5000", "payer": "test:p"}], "evidence": {}}
    Set r = ##class(pbp.Rules).Evaluate(c, ..Policy())
    Do $$$AssertEquals(r.action, "accept_order_keep_credit", "small overpayment accepted")
    Do $$$AssertTrue('r."moves_money", "no money")
    Do $$$AssertEquals(r.missing.%GetTypeOf("payer_history"), "null", "absent payer history is sealed as missing")
}

Method TestLargeMismatchGoesToAgent()
{
    Set c = {"exception": "amount_mismatch", "order": {"amount_minor": "8900", "status": "awaiting_payment"}, "payments": [{"payment_ref": "pix:A", "amount_minor": "12900", "payer": "test:p"}], "evidence": {}}
    Set r = ##class(pbp.Rules).Evaluate(c, ..Policy())
    Do $$$AssertTrue('r.decided, "rules do not close a large mismatch")
}

Method TestLatePaymentInsideGrace()
{
    Set c = {"exception": "late_payment", "order": {"amount_minor": "100", "status": "awaiting_payment", "expires_at": "2026-10-22T09:00:00.000Z"}, "payments": [{"payment_ref": "pix:A", "amount_minor": "100", "received_at": "2026-10-22T20:30:00.000Z", "payer": "test:p"}], "evidence": {}}
    Set r = ##class(pbp.Rules).Evaluate(c, ..Policy())
    Do $$$AssertEquals(r.action, "release_order", "late inside grace releases")
}

Method TestLatePaymentOutsideGrace()
{
    Set c = {"exception": "late_payment", "order": {"amount_minor": "100", "status": "awaiting_payment", "expires_at": "2026-10-20T09:00:00.000Z"}, "payments": [{"payment_ref": "pix:A", "amount_minor": "100", "received_at": "2026-10-25T20:30:00.000Z", "payer": "test:p"}], "evidence": {}}
    Set r = ##class(pbp.Rules).Evaluate(c, ..Policy())
    Do $$$AssertTrue('r.decided, "late outside grace goes to the agent")
}

Method TestPolicyLoadAndHash()
{
    Set json = "{""id"":""unit-store"",""version"":""9"",""limits"":{""autonomous_minor"":""100"",""currency"":""BRL""},""allowed_actions"":[""accept_order""],""forbidden"":[""b"",""a"",""b""],""rules"":{}}"
    Set pol = ##class(pbp.Data.Policy).Load(json, .reason)
    Do $$$AssertTrue($ISOBJECT(pol), "policy loads: " _ reason)
    Do $$$AssertEquals(pol.Sha256, ##class(pbp.Util).SHA256Hex(json), "hash is sha256 of the JSON text")
    Do $$$AssertEquals(pol.ForbiddenSorted().%ToJSON(), "[""a"",""b""]", "forbidden sorted unique")
    Set bad = ##class(pbp.Data.Policy).Load("{""id"":""x"",""version"":""1"",""limits"":{""autonomous_minor"":""01"",""currency"":""BRL""},""forbidden"":[]}", .reason)
    Do $$$AssertEquals(reason, "policy_limits_invalid", "leading zero amount refused")
    Do pol.%DeleteId(pol.%Id())
}

Method TestUtil()
{
    Set iso = ##class(pbp.Util).NowISO()
    Do $$$AssertTrue($MATCH(iso, "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z"), "ISO timestamp with 3 decimals: " _ iso)
    Do $$$AssertEquals(##class(pbp.Util).SHA256Hex("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "sha256 abc")
    Do $$$AssertTrue(##class(pbp.Util).IsMinorAmount("0") && ##class(pbp.Util).IsMinorAmount("18990") && '##class(pbp.Util).IsMinorAmount("01") && '##class(pbp.Util).IsMinorAmount("-5"), "minor amount pattern")
    Do $$$AssertTrue(##class(pbp.Util).ISOToSeconds("2026-10-22T20:30:00.000Z") - ##class(pbp.Util).ISOToSeconds("2026-10-22T09:00:00.000Z") = 41400, "ISO difference in seconds")
    Do $$$AssertEquals(##class(pbp.Util).GuardJSON("{""a"":1,""a"":2}"), "duplicate_field", "duplicate keys refused before persisting")
    Do $$$AssertEquals(##class(pbp.Util).GuardJSON("{""who"":""x@example.invalid""}"), "personal_data_found", "e-mail refused before persisting")
    Do $$$AssertEquals(##class(pbp.Util).GuardJSON("{""a"":1}"), "", "clean JSON accepted")
    Set san = ##class(pbp.Util).Sanitize("api_key=sk-abcdefghijklmnopqrstuvwxyz0123456789 mail x@example.invalid cpf 123.456.789-09")
    Do $$$AssertTrue((san '[ "sk-abc") && (san '[ "x@example") && (san '[ "123.456.789"), "sanitized diagnostics keep no key, mail or digit run: " _ san)
}

}
