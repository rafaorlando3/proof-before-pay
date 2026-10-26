/// Single-use permit: the only thing the ledger accepts. Bound to one commitment, case, policy version,
/// recipient, amount, currency and validity. Anything different is a different permit; a consumed permit
/// cannot be consumed again. Ten identical requests produce one effect.
Class pbp.Data.Permit Extends %Persistent
{

Property PermitId As %String(MAXLEN = 64) [ Required ];

Property Commitment As %String(MAXLEN = 64) [ Required ];

Property CaseId As %String(MAXLEN = 64) [ Required ];

Property PolicyId As %String(MAXLEN = 64);

Property PolicyVersion As %String(MAXLEN = 32);

/// Pseudonymous recipient account id inside the test ledger.
Property Recipient As %String(MAXLEN = 64);

Property AmountMinor As %String(MAXLEN = 20);

Property Currency As %String(MAXLEN = 3);

Property IssuedAt As %String(MAXLEN = 32);

Property ExpiresAt As %String(MAXLEN = 32);

/// issued, consumed, expired, revoked
Property Status As %String(MAXLEN = 16) [ InitialExpression = "issued" ];

Property ConsumedAt As %String(MAXLEN = 32);

Property ReceiptId As %String(MAXLEN = 64);

/// Who authorized: "policy" (within autonomous limit) or the operator id of the human approval.
Property AuthorizedBy As %String(MAXLEN = 64);

/// Commitment of the sealed approval record (when a human approved).
Property ApprovalCommitment As %String(MAXLEN = 64);

Index PermitIdx On PermitId [ Unique ];

/// One permit per sealed decision.
Index CommitIdx On Commitment [ Unique ];

Index CaseIdx On CaseId;

ClassMethod Find(permitId As %String) As pbp.Data.Permit
{
    Quit ..PermitIdxOpen(permitId)
}

/// Issue a permit for a sealed decision. Fails (with reason) if one already exists for the commitment.
ClassMethod Issue(seal As pbp.Data.Seal, recipient As %String, amountMinor As %String, currency As %String, policyId As %String, policyVersion As %String, authorizedBy As %String, approvalCommitment As %String, validitySeconds As %Integer, Output reason As %String) As pbp.Data.Permit
{
    Set reason = ""
    If '$ISOBJECT(seal) { Set reason="sealed_decision_not_found" Quit "" }
    Set proof=seal.Verify()
    If 'proof.ok { Set reason="proof_invalid" Quit "" }
    Set record=##class(pbp.Util).ParseJSON(seal.RecordJSON,.why)
    If '$ISOBJECT(record) { Set reason="record_invalid" Quit "" }
    If record.kind'="decision" { Set reason="decision_required" Quit "" }
    If (record.decision.action'="refund_duplicate")||('record.decision."moves_money") {
        Set reason="unsupported_financial_action" Quit ""
    }
    If (record.case.id'=seal.CaseId)||(record.policy.id'=policyId)||(record.policy.version'=policyVersion)||(record.decision."amount_minor"'=amountMinor)||(record.limits.currency'=currency)||(record.saw.inputs."recipient_ref"'=recipient) {
        Set reason="sealed_binding_mismatch" Quit ""
    }
    Set policy=##class(pbp.Data.Policy).IdVerOpen(policyId,policyVersion)
    If '$ISOBJECT(policy) { Set reason="policy_not_found" Quit "" }
    If ('policy.Active)||(policy.Sha256'=record.policy.sha256)||(policy.Sha256'=##class(pbp.Util).SHA256Hex(policy.JSON)) {
        Set reason="policy_changed" Quit ""
    }
    Set authority=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Read(seal.Commitment),.why)
    If '$ISOBJECT(authority) { Set reason="authorization_unavailable" Quit "" }
    If ('authority.ok)||(authority.state'="authorized")||(authority."approved_by"'=authorizedBy) {
        Set reason="authenticated_review_required" Quit ""
    }
    Set approval=##class(pbp.Data.Seal).Find(approvalCommitment)
    If '$ISOBJECT(approval) { Set reason="approval_seal_required" Quit "" }
    Set checked=approval.Verify()
    If 'checked.ok { Set reason="approval_proof_invalid" Quit "" }
    Set approved=##class(pbp.Util).ParseJSON(approval.RecordJSON,.why)
    If '$ISOBJECT(approved) { Set reason="approval_record_invalid" Quit "" }
    If (approved.kind'="approval")||(approved.case.id'=seal.CaseId)||(approved.human.approves'=seal.Commitment)||(approved.prev'=seal.Commitment)||(approved.human.outcome'="approved")||(approved.human.operator'=authorizedBy) {
        Set reason="approval_binding_mismatch" Quit ""
    }
    If (validitySeconds<1)||(validitySeconds>600) { Set reason="invalid_permit_validity" Quit "" }
    If $ISOBJECT(..CommitIdxOpen(seal.Commitment)) { Set reason = "permit_already_issued_for_commitment" Quit "" }
    If '##class(pbp.Util).IsMinorAmount(amountMinor) || (amountMinor = "0") { Set reason = "permit_amount_invalid" Quit "" }
    Set p = ..%New()
    Set p.PermitId = "pmt_" _ ##class(pbp.Util).RandomHex(12)
    Set p.Commitment = seal.Commitment
    Set p.CaseId = seal.CaseId
    Set p.PolicyId = policyId
    Set p.PolicyVersion = policyVersion
    Set p.Recipient = recipient
    Set p.AmountMinor = amountMinor
    Set p.Currency = currency
    Set now = $ZTIMESTAMP
    Set p.IssuedAt = ##class(pbp.Util).NowISO()
    Set exp = $PIECE(now, ",", 1) _ "," _ ($PIECE(now, ",", 2) + validitySeconds)
    If $PIECE(exp, ",", 2) >= 86400 Set exp = ($PIECE(exp, ",", 1) + 1) _ "," _ ($PIECE(exp, ",", 2) - 86400)
    Set p.ExpiresAt = $ZDATE(+exp, 3) _ "T" _ $ZTIME($PIECE(exp, ",", 2), 1, 3) _ "Z"
    Set p.AuthorizedBy = authorizedBy
    Set p.ApprovalCommitment = approvalCommitment
    Set sc = p.%Save()
    If $$$ISERR(sc) { Set reason = "permit_save_failed: " _ ##class(pbp.Util).StatusText(sc) Quit "" }
    Do ##class(pbp.Data.Event).Add(seal.CaseId, "permit_issued", amountMinor _ " " _ currency _ " to " _ recipient _ " by " _ authorizedBy, p.PermitId)
    Quit p
}

/// Is the permit still valid right now (issued and not expired)?
Method IsValidNow(Output reason As %String) As %Boolean
{
    Set reason = ""
    If ..Status '= "issued" { Set reason = "permit_" _ ..Status Quit 0 }
    If ##class(pbp.Util).ISOToSeconds(..ExpiresAt) < ##class(pbp.Util).ISOToSeconds(##class(pbp.Util).NowISO()) {
        Set reason = "permit_expired" Quit 0
    }
    Quit 1
}

}
