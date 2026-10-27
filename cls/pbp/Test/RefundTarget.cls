/// pbp.RefundTarget: the refund target on the agent path comes from the normalized input, never from prose.
Class pbp.Test.RefundTarget Extends %UnitTest.TestCase
{

ClassMethod Input(refA As %String, refB As %String, amtA As %String, amtB As %String, payerA As %String, payerB As %String, recipient As %String, atA As %String = "2026-10-22T12:00:00.000Z", atB As %String = "2026-10-22T12:02:00.000Z") As %DynamicObject
{
    Set i = {"currency":"BRL", "order": {"amount_minor": "18990", "currency":"BRL"}, "payments": []}
    Do i.payments.%Push({"payment_ref": (refA), "amount_minor": (amtA), "payer": (payerA), "received_at": (atA)})
    Do i.payments.%Push({"payment_ref": (refB), "amount_minor": (amtB), "payer": (payerB), "received_at": (atB)})
    If recipient '= "" Set i."recipient_ref" = recipient
    Quit i
}

Method TestLaterDistinctPayment()
{
    Set ref = ##class(pbp.RefundTarget).Derive(..Input("pix:A", "pix:B", "18990", "18990", "test:p", "test:p", "test:p"), .reason)
    Do $$$AssertEquals(ref, "pix:B", "later payment is the duplicate")
    Do $$$AssertEquals(reason, "", "no reason on success")
    Set ref = ##class(pbp.RefundTarget).Derive(..Input("pix:A", "pix:B", "18990", "18990", "test:p", "test:p", "test:p", "2026-10-22T12:05:00.000Z", "2026-10-22T12:00:00.000Z"), .reason)
    Do $$$AssertEquals(ref, "pix:A", "order of the array does not matter; received_at does")
}

Method TestRecipientAbsentStillDerives()
{
    // Target derivable; the ledger separately refuses with test_recipient_required and Decide seals refund_target missing.
    Set ref = ##class(pbp.RefundTarget).Derive(..Input("pix:A", "pix:B", "18990", "18990", "test:p", "test:p", ""), .reason)
    Do $$$AssertEquals(ref, "pix:B", "recipient absent does not block derivation")
}

Method TestRepeatedReferenceRefused()
{
    Set ref = ##class(pbp.RefundTarget).Derive(..Input("pix:A", "pix:A", "18990", "18990", "test:p", "test:p", "test:p"), .reason)
    Do $$$AssertEquals(ref, "", "same payment_ref twice is one payment observed twice")
    Do $$$AssertEquals(reason, "payment_refs_not_distinct", "reason code")
}

Method TestAmountPayerRecipientMismatch()
{
    Set ref = ##class(pbp.RefundTarget).Derive(..Input("pix:A", "pix:B", "18990", "19000", "test:p", "test:p", "test:p"), .reason)
    Do $$$AssertEquals(reason, "amount_mismatch", "near-duplicate amount refused")
    Set ref = ##class(pbp.RefundTarget).Derive(..Input("pix:A", "pix:B", "18990", "18990", "test:p1", "test:p2", "test:p1"), .reason)
    Do $$$AssertEquals(reason, "payer_mismatch", "two payers refused")
    Set ref = ##class(pbp.RefundTarget).Derive(..Input("pix:A", "pix:B", "18990", "18990", "test:p", "test:p", "test:other"), .reason)
    Do $$$AssertEquals(reason, "recipient_mismatch", "recipient must be the payer")
}

Method TestCardinality()
{
    Set i = ..Input("pix:A", "pix:B", "18990", "18990", "test:p", "test:p", "test:p")
    Do i.payments.%Push({"payment_ref": "pix:C", "amount_minor": "18990", "payer": "test:p", "received_at": "2026-10-22T12:04:00.000Z"})
    Set ref = ##class(pbp.RefundTarget).Derive(i, .reason)
    Do $$$AssertEquals(reason, "payments_not_two", "three payments are ambiguous")
    Set ref = ##class(pbp.RefundTarget).Derive({"currency":"BRL", "order": {"amount_minor": "18990", "currency":"BRL"}, "payments": []}, .reason)
    Do $$$AssertEquals(reason, "payments_not_two", "no payments")
}

Method TestEqualInstantsAreAmbiguous()
{
    Set i=..Input("pix:A","pix:B","18990","18990","test:p","test:p","test:p","2026-10-22T14:02:00+02:00","2026-10-22T12:02:00Z")
    Set ref=##class(pbp.RefundTarget).Derive(i,.reason)
    Do $$$AssertEquals(ref,"","two equal instants cannot identify the duplicate")
    Do $$$AssertEquals(reason,"received_at_ambiguous","offset-normalized tie is explicit")
}

Method TestOffsetOrdering()
{
    Set i=..Input("pix:A","pix:B","18990","18990","test:p","test:p","test:p","2026-10-22T13:00:00+02:00","2026-10-22T12:00:00Z")
    Set ref=##class(pbp.RefundTarget).Derive(i,.reason)
    Do $$$AssertEquals(ref,"pix:B","timestamps are instants rather than lexically ordered strings")
    Do $$$AssertEquals(reason,"","known distinct instants")
}

Method TestExplicitTargetStillNeedsDistinctEvidence()
{
    Set i=..Input("pix:A","pix:B","18990","18990","test:p","test:p","test:p")
    Set i."refund_payment_ref"="pix:A"
    Set ref=##class(pbp.RefundTarget).Derive(i,.reason)
    Do $$$AssertEquals(ref,"pix:A","explicit observed target is preserved")
    Set second=i.payments.%Get(1)
    Set second."payment_ref"="pix:A"
    Set ref=##class(pbp.RefundTarget).Derive(i,.reason)
    Do $$$AssertEquals(ref,"","an explicit target cannot bypass repeated evidence")
    Do $$$AssertEquals(reason,"payment_refs_not_distinct","independent target defence")
}

}
