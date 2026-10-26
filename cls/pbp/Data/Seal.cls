/// A sealed pbp.seal/1 record: the private record and salt stay here; only the commitment is shared.
/// Chain: Prev points to the previous commitment of the same case (decision -> approval -> ...).
Class pbp.Data.Seal Extends %Persistent
{

Property Commitment As %String(MAXLEN = 64) [ Required ];

Property CaseId As %String(MAXLEN = 64) [ Required ];

/// decision, approval, rule_change
Property Kind As %String(MAXLEN = 16);

Property RecordJSON As %String(MAXLEN = "") [ Required ];

Property Salt As %String(MAXLEN = 64) [ Required ];

Property Memo As %String(MAXLEN = 80);

Property Prev As %String(MAXLEN = 64);

/// pending (local only), anchored (independent anchor verified), tampered (detected on verify)
Property State As %String(MAXLEN = 16) [ InitialExpression = "pending" ];

Property SealedAt As %String(MAXLEN = 32);

/// Set when an anchor (e.g. Solana Memo) is confirmed; empty in the default local mode.
Property AnchorRef As %String(MAXLEN = 128);

/// witness (sealed directly) or ledger (staged through ProofBeforePay.Ledger, which holds the authoritative envelope).
Property Source As %String(MAXLEN = 16) [ InitialExpression = "witness" ];

/// Ledger state at sealing time for money decisions, or "blocked:<reason>".
Property LedgerState As %String(MAXLEN = 128);

Index CommitIdx On Commitment [ Unique ];

Index CaseIdx On CaseId;

ClassMethod Find(commitment As %String) As pbp.Data.Seal
{
    Quit ..CommitIdxOpen(commitment)
}

/// Verify this seal. Ledger-sourced seals are verified by the ledger's own envelope (authoritative copy);
/// an edited copy ("try to tamper") is checked against the stored commitment through the Witness.
/// Returns the bridge reply object (never throws).
Method Verify(tamperedRecordJSON As %String = "") As %DynamicObject
{
    Set recJson = $SELECT(tamperedRecordJSON = "": ..RecordJSON, 1: tamperedRecordJSON)
    Set rec = ##class(pbp.Util).ParseJSON(recJson, .reason)
    If rec = "" Quit {"ok": false, "state": "unverifiable", "reason": "stored_record_invalid_json"}
    Set env = {}
    Do env.%Set("record", rec)
    Do env.%Set("salt", ..Salt)
    Do env.%Set("commitment", ..Commitment)
    Set raw = ##class(ProofBeforePay.Witness).VerifyLocal(env.%ToJSON())
    Set reply = ##class(pbp.Util).ParseJSON(raw, .reason)
    If reply = "" Quit {"ok": false, "state": "unverifiable", "reason": "bridge_reply_invalid_json"}
    If reply.ok,(..Source="ledger"),(tamperedRecordJSON="") {
        Set authority=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Verify(..Commitment),.reason)
        If '$ISOBJECT(authority) Quit {"ok":false,"state":"unverifiable","reason":"ledger_reply_invalid_json"}
        If 'authority.ok Quit authority
    }
    Quit reply
}

/// Ordering check: did money move before this seal existed? Returns 1 when a receipt for the case
/// has an effect time earlier than SealedAt (that is the "sealed after the money moved" red state).
Method MoneyMovedBefore() As %Boolean
{
    Set sealed = ##class(pbp.Util).ISOToSeconds(..SealedAt)
    Set found = 0
    Set rid = ""
    &sql(DECLARE rc CURSOR FOR SELECT EffectAt INTO :effectAt FROM pbp_Data.Receipt WHERE CaseId = :caseId AND Status = 'effected')
    Set caseId = ..CaseId
    &sql(OPEN rc)
    For {
        &sql(FETCH rc)
        Quit:SQLCODE'=0
        If ##class(pbp.Util).ISOToSeconds(effectAt) < sealed Set found = 1
    }
    &sql(CLOSE rc)
    Quit found
}

}
