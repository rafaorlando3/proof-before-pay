/// RECORDED decisions for demos, tests and judges without a provider key. Labelled mode=recorded,
/// provider=replay in every sealed record; never presented as live inference. The replay still runs the
/// real read-only tools so the sealed record carries real tool outputs. Also hosts the decision contract
/// (ParseDecision/Fill) shared with the live operation.
Class pbp.Operation.Replay Extends Ens.BusinessOperation
{

Parameter INVOCATION = "Queue";

XData MessageMap
{
<MapItems>
  <MapItem MessageType="pbp.Msg.DecisionRequest">
    <Method>Decide</Method>
  </MapItem>
</MapItems>
}

Method Decide(pRequest As pbp.Msg.DecisionRequest, Output pResponse As pbp.Msg.DecisionResponse) As %Status
{
    Set pResponse = ##class(pbp.Msg.DecisionResponse).%New()
    Set pResponse.Ok = 0, pResponse.Temperature = 0
    Try {
        Do ..RunRecorded(pRequest, pResponse)
    } Catch ex {
        Set pResponse.Ok = 0, pResponse.Reason = "replay_exception"
        Do ##class(pbp.Util).LogEx("pbp.Operation.Replay", ex, pRequest.CaseId)
    }
    Do ##class(pbp.ToolsImpl).SetSessionCase("")
    If 'pResponse.Ok Do ##class(pbp.Util).Log("warn", "pbp.Operation.Replay", "decision not produced: " _ pResponse.Reason, pRequest.CaseId)
    Quit $$$OK
}

ClassMethod RunRecorded(pRequest As pbp.Msg.DecisionRequest, pResponse As pbp.Msg.DecisionResponse)
{
    Set caseId = pRequest.CaseId
    Set pResponse.Mode = "recorded"
    Set pResponse.ModelProvider = "replay"
    Set pResponse.ModelId = "fixtures/replay/decisions.json"
    Set pResponse.PromptTokens = 0, pResponse.CompletionTokens = 0, pResponse.CostMicroUSD = 0
    Set t0 = $ZHOROLOG
    Set json = $GET(^pbp.replay(caseId))
    If json = "" {
        Set pResponse.Reason = "no_recorded_decision_for_case"
        Quit
    }
    Do ##class(pbp.ToolsImpl).SetSessionCase(caseId)
    Set startSeq = ..LastToolSeq(caseId)
    Do ##class(pbp.Tools).GetOrder(caseId)
    Do ##class(pbp.Tools).GetPixEvents(caseId)
    Do ##class(pbp.Tools).GetPayerHistory(caseId)
    Do ##class(pbp.Tools).GetEvidence(caseId)
    Do ##class(pbp.Tools).GetStorePolicy(caseId)
    Set decision = ..ParseDecision(json, .reason)
    Set pResponse.DurationMs = (($ZHOROLOG - t0) * 1000) \ 1
    Set pResponse.ToolsJSON = ..ToolsSince(caseId, startSeq).%ToJSON()
    If decision = "" {
        Set pResponse.Reason = "recorded_decision_invalid:" _ reason
        Quit
    }
    Do ..Fill(pResponse, decision)
    Do ..ValidateContext(pResponse)
}

/// A valid JSON shape is insufficient: references must come from actual tool outputs and flags must
/// agree with the v1 action contract. A failure becomes a sealed human escalation in the process.
ClassMethod ValidateContext(response As pbp.Msg.DecisionResponse)
{
    Set reason="decision_context_check_failed"
    Try {
        Set guard=##class(%SYS.Python).Import("pbp_guard.decision")
        Set response.MissingJSON=guard."merge_missing"(response.MissingJSON,response.ToolsJSON)
        Set d={"action":(response.Action),"moves_money":(response.MovesMoney),"requires_human":(response.RequiresHuman)}
        Do d.%Set("moves_money",response.MovesMoney,"boolean")
        Do d.%Set("requires_human",response.RequiresHuman,"boolean")
        Set d."evidence_refs"=##class(pbp.Util).ParseJSON(response.EvidenceRefsJSON,.r)
        Set d.missing=##class(pbp.Util).ParseJSON(response.MissingJSON,.r)
        Set reason=guard."check_context"(d.%ToJSON(),response.ToolsJSON)
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Operation.Replay.ValidateContext",ex)
    }
    If reason'="" Set response.Ok=0,response.Reason="decision_context_invalid:"_reason
}

/// Copy a validated decision object into the response.
ClassMethod Fill(pResponse As pbp.Msg.DecisionResponse, d As %DynamicObject)
{
    Set pResponse.ProposalJSON=d.%ToJSON()
    Set pResponse.Action = d.action
    Set pResponse.MovesMoney = d."moves_money"
    Set pResponse.AmountMinor = $SELECT(d."amount_minor" = "": "", 1: d."amount_minor")
    Set pResponse.RequiresHuman = d."requires_human"
    Set pResponse.Confidence = d.confidence
    Set pResponse.Rationale = d.rationale
    Set pResponse.EvidenceRefsJSON = d."evidence_refs".%ToJSON()
    Set missing = d.missing
    If '$ISOBJECT(missing) Set missing = {}
    Set pResponse.MissingJSON = missing.%ToJSON()
    Set pResponse.Ok = 1
    Set pResponse.Reason = ""
}

/// Parse and validate the model's JSON. Returns "" with a stable reason on any problem.
ClassMethod ParseDecision(text As %String, Output reason As %String) As %DynamicObject
{
    Set reason = ""
    Set t = $ZSTRIP(text, "<>WC")
    // Tolerate code fences and leading prose: take the outermost {...}.
    Set i = $FIND(t, "{") - 1, j = $LENGTH(t)
    While (j > 0) && ($EXTRACT(t, j) '= "}") { Set j = j - 1 }
    If (i < 1) || (j <= i) { Set reason = "no_json_object" Quit "" }
    Set json = $EXTRACT(t, i, j)
    Set reason=##class(pbp.Util).GuardJSON(json)
    If reason'= "" Quit ""
    Set d = ##class(pbp.Util).ParseJSON(json, .reason)
    If d = "" Quit ""
    If (d.%GetTypeOf("action")'="string") || (d.action = "") { Set reason = "action_missing" Quit "" }
    If d.%GetTypeOf("moves_money") '= "boolean" { Set reason = "moves_money_not_boolean" Quit "" }
    If d.%GetTypeOf("requires_human") '= "boolean" { Set reason = "requires_human_not_boolean" Quit "" }
    If d."moves_money" {
        If (d."amount_minor" = "") || '##class(pbp.Util).IsMinorAmount(d."amount_minor") { Set reason = "amount_minor_invalid" Quit "" }
    } Else {
        Do d.%Remove("amount_minor")
    }
    If (d.%GetTypeOf("confidence") '= "number") || (d.confidence < 0) || (d.confidence > 1) { Set reason = "confidence_out_of_range" Quit "" }
    If d.%GetTypeOf("rationale")'="string" { Set reason="rationale_not_string" Quit "" }
    Set r = $ZSTRIP(d.rationale, "<>W")
    If ($LENGTH(r) < 8) || ($LENGTH(r) > 800) { Set reason = "rationale_length" Quit "" }
    Set d.rationale = r
    If (d.%GetTypeOf("evidence_refs") '= "array") || (d."evidence_refs".%Size() = 0) { Set reason = "evidence_refs_missing" Quit "" }
    Set refs=d."evidence_refs"
    For n=0:1:refs.%Size()-1 {
        If (refs.%GetTypeOf(n)'="string") || ($LENGTH(refs.%Get(n))=0) { Set reason="evidence_refs_invalid" Quit }
    }
    If reason'="" Quit ""
    If $LENGTH(refs.%ToJSON())>1024 { Set reason="evidence_refs_too_large" Quit "" }
    If d.%GetTypeOf("missing") = "unassigned" Set d.missing = {}
    If d.%GetTypeOf("missing") '= "object" { Set reason = "missing_not_object" Quit "" }
    // Normalize: every value under missing is null.
    Set m = {}
    Set it = d.missing.%GetIterator()
    While it.%GetNext(.k, .v) {
        If d.missing.%GetTypeOf(k)'="null" { Set reason="missing_value_must_be_null" Quit }
        Do m.%Set(k, "", "null")
    }
    If reason'="" Quit ""
    Set d.missing = m
    If $LENGTH(m.%ToJSON())>4000 { Set reason="missing_too_large" Quit "" }
    Quit d
}

ClassMethod LastToolSeq(caseId As %String) As %Integer
{
    &sql(SELECT MAX(Seq) INTO :mx FROM pbp_Data.ToolCall WHERE CaseId = :caseId)
    Quit $SELECT((SQLCODE = 0) && (mx '= ""): mx, 1: 0)
}

/// Tool calls made after startSeq, as the sealed "saw.tools" array (name, args, output).
ClassMethod ToolsSince(caseId As %String, startSeq As %Integer) As %DynamicArray
{
    Set arr = []
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT Name, ArgsJSON, OutputJSON FROM pbp_Data.ToolCall WHERE CaseId = ? AND Seq > ? ORDER BY Seq", caseId, startSeq)
    While rs.%Next() {
        Set t = {}
        Set t.name = rs.%Get("Name")
        Set a = ##class(pbp.Util).ParseJSON(rs.%Get("ArgsJSON"), .r)
        Set t.args = $SELECT($ISOBJECT(a): a, 1: {})
        Set o = ##class(pbp.Util).ParseJSON(rs.%Get("OutputJSON"), .r)
        If $ISOBJECT(o) { Do t.%Set("output", o) } Else { Do t.%Set("output", rs.%Get("OutputJSON")) }
        Do arr.%Push(t)
    }
    Quit arr
}

}
