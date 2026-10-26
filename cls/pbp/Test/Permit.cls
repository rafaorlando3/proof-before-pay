/// Permit, test ledger and reconciliation, through the real Witness and ProofBeforePay.Ledger:
/// a sealed decision cannot get a permit without a sealed approval; ten identical ledger requests yield one
/// effect; expired or mismatched permits never execute; an uncertain answer is reconciled, never re-executed.
/// Runs as the test user ($USERNAME needs PBPReview:U or %All for Ledger.Approve).
Class pbp.Test.Permit Extends %UnitTest.TestCase
{

/// Policy in the catalogue the records refer to.
Method Policy() As pbp.Data.Policy
{
    Set json = "{""id"":""unit-store"",""version"":""1"",""limits"":{""autonomous_minor"":""0"",""currency"":""BRL""},""allowed_actions"":[""refund_duplicate""],""forbidden"":[""change_policy""],""rules"":{}}"
    Quit ##class(pbp.Data.Policy).Load(json, .reason)
}

/// A valid money decision record in the ledger contract shape, for a fresh synthetic case.
Method Record(caseId As %String, amount As %String, pol As pbp.Data.Policy) As %DynamicObject
{
    Set refA = "pix:" _ caseId _ "A", refB = "pix:" _ caseId _ "B"
    Set inputs = {"case_id": (caseId), "store": "unit-store", "exception": "duplicate_payment", "environment": "sandbox", "currency": "BRL", "order": {"id": "o", "amount_minor": (amount), "currency": "BRL", "status": "paid"}, "order_amount_minor": (amount), "payments": [{"payment_ref": (refA), "amount_minor": (amount), "payer": "test:unit-payer"}, {"payment_ref": (refB), "amount_minor": (amount), "payer": "test:unit-payer"}], "recipient_ref": "test:unit-payer", "refund_payment_ref": (refB), "evidence": {}}
    Set r = {"v": "pbp.seal/1", "kind": "decision", "at": (##class(pbp.Util).NowISO()), "case": {"id": (caseId), "exception": "duplicate_payment", "store": "unit-store"}, "saw": {"inputs": (inputs), "tools": []}, "missing": {}, "rules": {"engine": "pbp.Rules", "version": "2", "result": "R1:refund_duplicate"}, "decision": {"action": "refund_duplicate", "moves_money": true, "amount_minor": (amount), "requires_human": true, "confidence": 0.99, "rationale": "Unit test duplicate refund proposal.", "evidence_refs": ["order", (refA), (refB)]}, "forbidden": ["change_policy"], "limits": {"autonomous_minor": "0", "currency": "BRL"}}
    Set r.policy = {"id": (pol.PolicyId), "version": (pol.Version), "sha256": (pol.Sha256)}
    Do r.%Set("model", "", "null")
    Do r.%Set("prev", "", "null")
    Quit r
}

/// Stage through the ledger and store the workflow copy, like pbp.Operation.Witness does.
Method StageSeal(rec As %DynamicObject) As pbp.Data.Seal
{
    Set staged = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Stage(rec.%ToJSON()), .r)
    Do $$$AssertTrue($ISOBJECT(staged) && staged.ok, "ledger stage ok: " _ $SELECT($ISOBJECT(staged): staged.reason, 1: r))
    Set env = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Envelope(staged.commitment), .r)
    Set s = ##class(pbp.Data.Seal).%New()
    Set s.Commitment = staged.commitment, s.CaseId = rec.case.id, s.Kind = "decision", s.RecordJSON = rec.%ToJSON(), s.Salt = env.salt
    Set s.Source = "ledger", s.LedgerState = staged.state, s.SealedAt = rec.at, s.Memo = "pbp1:" _ staged.commitment
    Do $$$AssertStatusOK(s.%Save(), "seal copy saved")
    Quit s
}

/// Seal an approval record (through the Witness) by the current user for a decision seal.
Method ApprovalSeal(seal As pbp.Data.Seal, outcome As %String) As pbp.Data.Seal
{
    Set op = ##class(pbp.Process.Decide).SafeId($USERNAME)
    Set r = {"v": "pbp.seal/1", "kind": "approval", "at": (##class(pbp.Util).NowISO()), "case": {"id": (seal.CaseId), "exception": "duplicate_payment", "store": "unit-store"}, "human": {"operator": (op), "outcome": (outcome), "approves": (seal.Commitment)}, "prev": (seal.Commitment)}
    Set reply = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Witness).Seal(r.%ToJSON()), .x)
    Do $$$AssertTrue($ISOBJECT(reply) && reply.ok, "approval sealed: " _ $SELECT($ISOBJECT(reply): reply.reason, 1: x))
    Set a = ##class(pbp.Data.Seal).%New()
    Set a.Commitment = reply.commitment, a.CaseId = seal.CaseId, a.Kind = "approval", a.RecordJSON = r.%ToJSON(), a.Salt = reply.salt, a.Prev = seal.Commitment, a.SealedAt = r.at, a.Memo = reply.memo
    Do $$$AssertStatusOK(a.%Save(), "approval copy saved")
    Quit a
}

Method NewCase(amount As %String, Output seal As pbp.Data.Seal) As %String
{
    Set caseId = "unit-" _ ##class(pbp.Util).RandomHex(4)
    Set pol = ..Policy()
    Set rec = ..Record(caseId, amount, pol)
    Set seal = ..StageSeal(rec)
    Quit caseId
}

Method Request(p As pbp.Data.Permit) As pbp.Msg.LedgerRequest
{
    Set r = ##class(pbp.Msg.LedgerRequest).%New()
    Set r.PermitId = p.PermitId, r.Commitment = p.Commitment, r.CaseId = p.CaseId, r.Recipient = p.Recipient, r.AmountMinor = p.AmountMinor, r.Currency = p.Currency
    Quit r
}

Method TestNoPermitWithoutApproval()
{
    Set caseId = ..NewCase("1500", .seal)
    // v1 contract: "policy" can never authorize; the ledger must be authorized by a human first; then a sealed approval is required.
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", "policy", "", 600, .reason)
    Do $$$AssertTrue('$ISOBJECT(p) && (reason '= ""), "policy cannot issue in v1: " _ reason)
    Set op = ##class(pbp.Process.Decide).SafeId($USERNAME)
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, "", 600, .reason)
    Do $$$AssertTrue('$ISOBJECT(p) && (reason '= ""), "ledger not authorized and no approval seal: " _ reason)
    Do ##class(ProofBeforePay.Ledger).Approve(seal.Commitment)
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, "", 600, .reason)
    Do $$$AssertTrue('$ISOBJECT(p) && (reason [ "approval"), "ledger authorized but no sealed approval: " _ reason)
}

Method TestTenRequestsOneEffect()
{
    Set caseId = ..NewCase("1500", .seal)
    Set led = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Approve(seal.Commitment), .r)
    Do $$$AssertTrue($ISOBJECT(led) && led.ok && (led.state = "authorized"), "ledger approve in this session: " _ $SELECT($ISOBJECT(led): led.reason, 1: r))
    Set appr = ..ApprovalSeal(seal, "approved")
    Set op = ##class(pbp.Process.Decide).SafeId($USERNAME)
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, appr.Commitment, 600, .reason)
    Do $$$AssertTrue($ISOBJECT(p), "permit issued after sealed approval: " _ reason)
    Set receipts = ""
    For i = 1:1:10 {
        Do ##class(pbp.Operation.TestLedger).Apply(..Request(p), "none", .resp)
        Do $$$AssertTrue(resp.Ok, "request " _ i _ " ok: " _ resp.Reason)
        If i = 1 { Do $$$AssertTrue('resp.Duplicate, "first is the effect") Set receipts = resp.ReceiptId }
        Else { Do $$$AssertTrue(resp.Duplicate && (resp.ReceiptId = receipts), "request " _ i _ " is a duplicate with the original receipt") }
    }
    Set read = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Read(seal.Commitment), .r)
    Do $$$AssertTrue(read.ok && (read.state = "confirmed") && (read."effect_count" = 1), "ledger shows one confirmed effect")
    Do $$$AssertEquals(##class(pbp.Data.Permit).Find(p.PermitId).Status, "consumed", "permit consumed")
    Set q = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, appr.Commitment, 600, .reason)
    Do $$$AssertTrue('$ISOBJECT(q) && (reason = "authenticated_review_required"), "second permit for the same seal refused")
}

Method TestRejectedApprovalGivesNoPermit()
{
    Set caseId = ..NewCase("1500", .seal)
    Set appr = ..ApprovalSeal(seal, "rejected")
    Set op = ##class(pbp.Process.Decide).SafeId($USERNAME)
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, appr.Commitment, 600, .reason)
    Do $$$AssertTrue('$ISOBJECT(p) && (reason = "authenticated_review_required"), "rejected approval gives no permit: " _ reason)
}

Method TestBindingMismatchAndExpiry()
{
    Set caseId = ..NewCase("1500", .seal)
    Do ##class(ProofBeforePay.Ledger).Approve(seal.Commitment)
    Set appr = ..ApprovalSeal(seal, "approved")
    Set op = ##class(pbp.Process.Decide).SafeId($USERNAME)
    // TTL contract: 1..600 seconds; out-of-range validity is refused at issue time.
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, appr.Commitment, -5, .reason)
    Do $$$AssertTrue('$ISOBJECT(p) && (reason '= ""), "validity -5 refused at issue: " _ reason)
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, appr.Commitment, 601, .reason)
    Do $$$AssertTrue('$ISOBJECT(p) && (reason '= ""), "validity 601 refused at issue: " _ reason)
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, appr.Commitment, 1, .reason)
    Do $$$AssertTrue($ISOBJECT(p), "permit issued with 1 s validity: " _ reason)
    Set r = ..Request(p)
    Set r.AmountMinor = "1501"
    Do ##class(pbp.Operation.TestLedger).Apply(r, "none", .resp)
    Do $$$AssertTrue('resp.Ok && (resp.Reason = "permit_binding_mismatch"), "changed amount refused: " _ resp.Reason)
    Hang 2
    Do ##class(pbp.Operation.TestLedger).Apply(..Request(p), "none", .resp)
    Do $$$AssertTrue('resp.Ok && (resp.Reason = "permit_expired"), "expired permit refused: " _ resp.Reason)
    Set read = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Read(seal.Commitment), .x)
    Do $$$AssertTrue(read.ok && (read.state = "authorized") && 'read."test_effect", "no effect recorded")
}

Method TestUncertainIsReconciledNotReexecuted()
{
    Set caseId = ..NewCase("1500", .seal)
    Do ##class(ProofBeforePay.Ledger).Approve(seal.Commitment)
    Set appr = ..ApprovalSeal(seal, "approved")
    Set op = ##class(pbp.Process.Decide).SafeId($USERNAME)
    Set p = ##class(pbp.Data.Permit).Issue(seal, "test:unit-payer", "1500", "BRL", "unit-store", "1", op, appr.Commitment, 600, .reason)
    Do ##class(pbp.Operation.TestLedger).Apply(..Request(p), "uncertain", .resp)
    Do $$$AssertTrue('resp.Ok && resp.Uncertain, "uncertain before any write")
    Do ##class(pbp.Operation.TestLedger).Reconcile(p.PermitId, .rec)
    Do $$$AssertTrue('rec.Ok && (rec.Reason [ "no_effect_recorded"), "reconcile finds no effect: " _ rec.Reason)
    Do ##class(pbp.Operation.TestLedger).Apply(..Request(p), "uncertain_after_commit", .resp)
    Do $$$AssertTrue('resp.Ok && resp.Uncertain, "reply lost after execute")
    Do ##class(pbp.Operation.TestLedger).Reconcile(p.PermitId, .rec)
    Do $$$AssertTrue(rec.Ok && rec.Duplicate && (rec.ReceiptId '= ""), "reconcile finds the one effect: " _ rec.Reason)
    Do ##class(pbp.Operation.TestLedger).Apply(..Request(p), "none", .resp)
    Do $$$AssertTrue(resp.Ok && resp.Duplicate && (resp.ReceiptId = rec.ReceiptId), "a later retry is a duplicate of the same receipt")
    Set read = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Read(seal.Commitment), .x)
    Do $$$AssertTrue(read.ok && (read."effect_count" = 1), "exactly one effect in the ledger")
    Do ##class(pbp.Operation.TestLedger).Apply(..Request(p), "down", .resp)
    Do $$$AssertTrue('resp.Ok && 'resp.Uncertain && (resp.Reason = "ledger_unavailable"), "down reply")
}

Method TestSameDuplicatePixCannotPayTwiceAcrossCases()
{
    // Two different cases pointing at the same refund_payment_ref: the ledger BLOCKS the second stage
    // (payment_already_staged) and never binds a projection to another case's hash. Same JSON again is idempotent.
    Set pol = ..Policy()
    Set a = ..Record("unit-x" _ ##class(pbp.Util).RandomHex(3), "700", pol)
    Set b = ..Record("unit-y" _ ##class(pbp.Util).RandomHex(3), "700", pol)
    Set b.saw.inputs."refund_payment_ref" = a.saw.inputs."refund_payment_ref"
    Set b.saw.inputs.payments = a.saw.inputs.payments
    Set b.decision."evidence_refs" = a.decision."evidence_refs"
    Set sa = ..StageSeal(a)
    Set staged = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Stage(b.%ToJSON()), .r)
    Do $$$AssertTrue($ISOBJECT(staged) && 'staged.ok && (staged.state = "blocked") && (staged.reason = "payment_already_staged"), "second case with the same Pix is blocked: " _ $SELECT($ISOBJECT(staged): staged.reason, 1: r))
    Set again = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Stage(a.%ToJSON()), .r)
    Do $$$AssertTrue($ISOBJECT(again) && again.ok && (again.commitment = sa.Commitment), "same record staged again is idempotent (same commitment)")
}

Method TestReceiptProjectionTamperIsVisible()
{
    Set cid=..NewCase("1500",.seal)
    Do ##class(ProofBeforePay.Ledger).Approve(seal.Commitment)
    Set appr=..ApprovalSeal(seal,"approved")
    Set p=##class(pbp.Data.Permit).Issue(seal,"test:unit-payer","1500","BRL","unit-store","1",$USERNAME,appr.Commitment,600,.reason)
    Do $$$AssertTrue($ISOBJECT(p),"permit issued: "_reason)
    Do ##class(pbp.Operation.TestLedger).Apply(..Request(p),"none",.resp)
    Do $$$AssertTrue(resp.Ok,"first effect confirmed")
    Set row=##class(pbp.Data.Receipt).PermitIdxOpen(p.PermitId)
    Set row.Currency="USD"
    Do $$$AssertStatusOK(row.%Save(),"alter only the synthetic readable receipt copy")
    Set view=##class(pbp.API).ReceiptObj(cid)
    Do $$$AssertEquals(view.verification,"tampered","dashboard refuses misleading receipt currency")
    Do ##class(pbp.Operation.TestLedger).Apply(..Request(p),"none",.resp)
    Do $$$AssertTrue('resp.Ok && (resp.Reason="projection_binding_mismatch"),"retry refuses tampered receipt projection")
    Set row.Currency="BRL"
    Do row.%Save()
    Set read=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Audit(seal.Commitment),.r)
    Do $$$AssertTrue(read.ok && read."receipt_integrity_verified" && (read."effect_count"=1),"authoritative receipt still verifies and effect count remains one")
}

}
