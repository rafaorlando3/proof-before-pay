/// Interoperability wrapper around the single authoritative sandbox effect boundary.
/// pbp.Data.Receipt/LedgerEntry are projections for review; they never authorize effects.
Class pbp.Operation.TestLedger Extends Ens.BusinessOperation
{
Parameter INVOCATION = "Queue";
Property FailureMode As %String(VALUELIST = ",none,uncertain,down,uncertain_after_commit") [ InitialExpression = "none" ];
Parameter SETTINGS = "FailureMode:Basic";
XData MessageMap
{
<MapItems><MapItem MessageType="pbp.Msg.LedgerRequest"><Method>Effect</Method></MapItem></MapItems>
}
Method Effect(pRequest As pbp.Msg.LedgerRequest, Output pResponse As pbp.Msg.LedgerResponse) As %Status
{
    Quit ..Apply(pRequest,..FailureMode,.pResponse)
}

ClassMethod Apply(pRequest As pbp.Msg.LedgerRequest, failureMode As %String, Output pResponse As pbp.Msg.LedgerResponse) As %Status
{
    Set pResponse=##class(pbp.Msg.LedgerResponse).%New(),pResponse.Ok=0
    Set locked=0
    If $TLEVEL { Set pResponse.Reason="nested_transaction" Quit $$$OK }
    Try {
        If failureMode="down" { Set pResponse.Reason="ledger_unavailable" Quit }
        If failureMode="uncertain" { Set pResponse.Uncertain=1,pResponse.Reason="ledger_result_unknown" Quit }
        If '$MATCH(pRequest.PermitId,"pmt_[a-f0-9]{24}") { Set pResponse.Reason="invalid_permit" Quit }
        Lock +^pbp.ledger.permit(pRequest.PermitId):5
        If '$TEST { Set pResponse.Uncertain=1,pResponse.Reason="permit_lock_timeout" Quit }
        Set locked=1
        Set permit=##class(pbp.Data.Permit).Find(pRequest.PermitId)
        If '$ISOBJECT(permit) { Set pResponse.Reason="permit_not_found" Quit }
        If (permit.Commitment'=pRequest.Commitment)||(permit.CaseId'=pRequest.CaseId)||(permit.AmountMinor'=pRequest.AmountMinor)||(permit.Currency'=pRequest.Currency)||(permit.Recipient'=pRequest.Recipient) {
            Set pResponse.Reason="permit_binding_mismatch" Quit
        }
        Set seal=##class(pbp.Data.Seal).Find(permit.Commitment)
        If '$ISOBJECT(seal) { Set pResponse.Reason="sealed_decision_not_found" Quit }
        Set verified=seal.Verify()
        If 'verified.ok { Set pResponse.Reason="proof_invalid" Quit }
        Set existing=##class(pbp.Data.Receipt).PermitIdxOpen(permit.PermitId)
        If '$ISOBJECT(existing),'permit.IsValidNow(.why) { Set pResponse.Reason=why Quit }
        // This call is the only effect. It rechecks the stored envelope and review,
        // deduplicates by payment reference, and returns the original on retry.
        Set authoritative=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Execute(permit.Commitment),.why)
        If '$ISOBJECT(authoritative) { Set pResponse.Uncertain=1,pResponse.Reason="ledger_reply_invalid" Quit }
        If 'authoritative.ok { Set pResponse.Reason=authoritative.reason Quit }
        If failureMode="uncertain_after_commit" {
            Set pResponse.Uncertain=1,pResponse.Reason="response_lost_after_commit" Quit
        }
        Set confirmed=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Confirm(permit.Commitment),.why)
        If '$ISOBJECT(confirmed) { Set pResponse.Uncertain=1,pResponse.Reason="readback_unavailable" Quit }
        If 'confirmed.ok { Set pResponse.Uncertain=1,pResponse.Reason=confirmed.reason Quit }
        Set receipt=confirmed.receipt
        If $ISOBJECT(existing) {
            If ('existing.Matches(receipt))||(existing.PermitId'=permit.PermitId) {
                Set pResponse.Reason="projection_binding_mismatch" Quit
            }
        } Else {
            // A projection failure can never roll back an already committed effect.
            // A retry reads the same authoritative receipt and rebuilds this view.
            TStart
            Set existing=##class(pbp.Data.Receipt).%New()
            Set existing.ReceiptId=receipt."receipt_id",existing.PermitId=permit.PermitId
            Set existing.CaseId=permit.CaseId,existing.Commitment=permit.Commitment
            Set existing.AmountMinor=receipt."amount_minor",existing.Currency=receipt.currency
            Set existing.Recipient=receipt."recipient_ref",existing.Status="effected"
            Set existing.LedgerRef="sandbox:"_receipt."receipt_id",existing.EffectAt=receipt."executed_at"
            Set existing.EffectSeq=receipt."executed_seq"
            Set sc=existing.%Save()
            If $$$ISOK(sc) {
                Set permit.Status="consumed",permit.ConsumedAt=existing.EffectAt,permit.ReceiptId=existing.ReceiptId
                Set sc=permit.%Save()
            }
            If $$$ISERR(sc) {
                TRollback
                Set pResponse.Uncertain=1,pResponse.Reason="projection_write_failed" Quit
            }
            TCommit
        }
        Set pResponse.Ok=1,pResponse.Duplicate=authoritative.replayed
        Set pResponse.Reason=$SELECT(pResponse.Duplicate:"effect_already_confirmed",1:"test_effect_confirmed")
        Set pResponse.ReceiptId=existing.ReceiptId,pResponse.LedgerRef=existing.LedgerRef,pResponse.EffectAt=existing.EffectAt
    } Catch ex {
        If $TLEVEL TRollback
        Set pResponse.Ok=0,pResponse.Uncertain=1,pResponse.Reason="ledger_exception"
        Do ##class(pbp.Util).Log("error","pbp.Operation.TestLedger","ledger_exception",pRequest.CaseId)
    }
    If locked Lock -^pbp.ledger.permit(pRequest.PermitId)
    Quit $$$OK
}

/// Reconciliation only reads and confirms an existing effect; it never executes.
ClassMethod Reconcile(permitId As %String, Output pResponse As pbp.Msg.LedgerResponse) As %Status
{
    Set pResponse=##class(pbp.Msg.LedgerResponse).%New(),pResponse.Ok=0
    Try {
        Set permit=##class(pbp.Data.Permit).Find(permitId)
        If '$ISOBJECT(permit) { Set pResponse.Reason="permit_not_found" Quit }
        Set read=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Read(permit.Commitment),.why)
        If '$ISOBJECT(read) { Set pResponse.Uncertain=1,pResponse.Reason="readback_unavailable" Quit }
        If ('read.ok)||('read."test_effect") {
            Set pResponse.Reason="no_effect_recorded" Quit
        }
        // Apply is safe here only after the read proved a committed effect.
        // Its Execute is idempotent and revalidates the bound receipt.
        Set req=##class(pbp.Msg.LedgerRequest).%New()
        Set req.PermitId=permit.PermitId,req.Commitment=permit.Commitment,req.CaseId=permit.CaseId
        Set req.AmountMinor=permit.AmountMinor,req.Currency=permit.Currency,req.Recipient=permit.Recipient
        Do ..Apply(req,"none",.pResponse)
        If pResponse.Ok Set pResponse.Duplicate=1,pResponse.Reason="effect_found_on_reconcile"
    } Catch ex {
        Set pResponse.Uncertain=1,pResponse.Reason="reconciliation_failed"
        Do ##class(pbp.Util).LogEx("pbp.Operation.TestLedger.Reconcile",ex)
    }
    Quit $$$OK
}
}
