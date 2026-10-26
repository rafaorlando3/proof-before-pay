/// Seals a pbp.seal/1 record BEFORE any effect. Two paths, one Witness:
///  - decisions that move money go through ProofBeforePay.Ledger.Stage (which calls the Witness and keeps the
///    authoritative envelope for the test effect); if the ledger refuses the plan, the decision is still sealed
///    through the Witness so the refusal itself is on record (LedgerState = blocked:<reason>);
///  - decisions without money and approval records are sealed through ProofBeforePay.Witness directly.
/// pbp.Data.Seal keeps the workflow copy (record, salt, chain). Failures carry stable reason codes only.
Class pbp.Operation.Witness Extends Ens.BusinessOperation
{

Parameter INVOCATION = "Queue";

XData MessageMap
{
<MapItems>
  <MapItem MessageType="pbp.Msg.SealRequest">
    <Method>Seal</Method>
  </MapItem>
</MapItems>
}

Method Seal(pRequest As pbp.Msg.SealRequest, Output pResponse As pbp.Msg.SealResponse) As %Status
{
    Set pResponse = ##class(pbp.Msg.SealResponse).%New()
    Set pResponse.Ok = 0
    Set caseId = pRequest.CaseId
    Try {
        Set rec = ##class(pbp.Util).ParseJSON(pRequest.RecordJSON, .reason)
        If rec = "" { Set pResponse.Reason = "record_invalid_json" Quit }
        Set case = ##class(pbp.Data.Case).Find(caseId)
        Set head = $SELECT($ISOBJECT(case): case.HeadCommitment, 1: "")
        Set prev = $SELECT(rec.%GetTypeOf("prev") = "null": "", 1: rec.prev)
        If prev '= head { Set pResponse.Reason = "prev_not_head" Do ##class(pbp.Util).Log("error", "pbp.Operation.Witness", "prev=" _ prev _ " head=" _ head, caseId) Quit }
        Set movesMoney = (pRequest.Kind = "decision") && $ISOBJECT(rec.decision) && rec.decision."moves_money"
        Set source = "witness", ledgerState = "", salt = "", commitment = "", memo = ""
        If movesMoney {
            Set raw = ##class(ProofBeforePay.Ledger).Stage(pRequest.RecordJSON)
            Set staged = ##class(pbp.Util).ParseJSON(raw, .reason)
            If staged = "" { Set pResponse.Reason = "ledger_reply_invalid_json" Quit }
            If staged.ok {
                Set source = "ledger", commitment = staged.commitment, ledgerState = staged.state
                Set env = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Envelope(commitment), .reason)
                If '$ISOBJECT(env) || (env.salt = "") { Set pResponse.Reason = "ledger_envelope_unavailable" Quit }
                Set salt = env.salt
                Set memo = "pbp1:" _ commitment
            } ElseIf (staged.reason = "seal_failed") || (staged.reason = "storage_failed") || (staged.reason = "ledger_busy") || (staged.reason = "validation_unavailable") {
                Set pResponse.Reason = "ledger_" _ staged.reason
                Do ##class(pbp.Util).Log("error", "pbp.Operation.Witness", "ledger stage failed: " _ staged.reason, caseId)
                Quit
            } Else {
                // Plan refused (for example missing refund target): seal the decision anyway so the refusal is on record.
                Set ledgerState = "blocked:" _ staged.reason
                Do ##class(pbp.Util).Log("warn", "pbp.Operation.Witness", "ledger refused plan: " _ staged.reason _ "; sealing through witness", caseId)
            }
        }
        If source = "witness" {
            Set raw = ##class(ProofBeforePay.Witness).Seal(pRequest.RecordJSON)
            Set reply = ##class(pbp.Util).ParseJSON(raw, .reason)
            If reply = "" { Set pResponse.Reason = "bridge_reply_invalid_json" Quit }
            If 'reply.ok {
                Set pResponse.Reason = reply.reason
                Do ##class(pbp.Util).Log("error", "pbp.Operation.Witness", "seal refused: " _ reply.reason, caseId)
                Quit
            }
            Set commitment = reply.commitment, salt = reply.salt, memo = reply.memo
        }
        If $ISOBJECT(##class(pbp.Data.Seal).Find(commitment)) { Set pResponse.Reason = "commitment_already_stored" Quit }
        Set seal = ##class(pbp.Data.Seal).%New()
        Set seal.Commitment = commitment
        Set seal.CaseId = caseId
        Set seal.Kind = pRequest.Kind
        Set seal.RecordJSON = pRequest.RecordJSON
        Set seal.Salt = salt
        Set seal.Memo = memo
        Set seal.Prev = prev
        Set seal.State = "pending"
        Set seal.Source = source
        Set seal.LedgerState = ledgerState
        Set seal.SealedAt = rec.at
        Set sc = seal.%Save()
        If $$$ISERR(sc) { Set pResponse.Reason = "seal_save_failed" Do ##class(pbp.Util).Log("error", "pbp.Operation.Witness", ##class(pbp.Util).StatusText(sc), caseId) Quit }
        If $ISOBJECT(case) {
            Set case.HeadCommitment = seal.Commitment
            Do case.SetStatus("sealed", pRequest.Kind _ " sealed (" _ source _ $SELECT(ledgerState = "": "", 1: ", ledger " _ ledgerState) _ ")", seal.Commitment)
        }
        Set pResponse.Ok = 1
        Set pResponse.Commitment = seal.Commitment
        Set pResponse.Memo = seal.Memo
        Set pResponse.State = seal.State
        Set pResponse.SealedAt = seal.SealedAt
        Set pResponse.LedgerState = ledgerState
    } Catch ex {
        Set pResponse.Ok = 0
        Set pResponse.Reason = "witness_exception"
        Do ##class(pbp.Util).LogEx("pbp.Operation.Witness", ex, caseId)
    }
    Quit $$$OK
}

}
