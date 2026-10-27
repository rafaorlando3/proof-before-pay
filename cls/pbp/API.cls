/// REST API for the review UI and the public verifier. Read endpoints expose cases, seals and the time
/// machine; the only write endpoints are intake (POST /cases) and verify-a-copy (POST /seals/:c/verify),
/// which never modifies stored data. Errors always carry a reason code.
Class pbp.API Extends %CSP.REST
{

Parameter HandleCorsRequest = 0;

Parameter CHARSET = "utf-8";

Parameter CONTENTTYPE = "application/json";

XData UrlMap [ XMLNamespace = "http://www.intersystems.com/urlmap" ]
{
<Routes>
  <Route Url="/health" Method="GET" Call="Health"/>
  <Route Url="/cases" Method="GET" Call="Cases"/>
  <Route Url="/cases" Method="POST" Call="Intake"/>
  <Route Url="/cases/:id" Method="GET" Call="CaseDetail"/>
  <Route Url="/cases/:id/replay" Method="GET" Call="Replay"/>
  <Route Url="/seals/:c" Method="GET" Call="SealDetail"/>
  <Route Url="/seals/:c/verify" Method="POST" Call="VerifyCopy"/>
  <Route Url="/stats" Method="GET" Call="Stats"/>
  <Route Url="/ledger/:c" Method="GET" Call="Ledger"/>
  <Route Url="/review" Method="GET" Call="ReviewList"/>
  <Route Url="/review/:id" Method="POST" Call="ReviewAct"/>
  <Route Url="/whoami" Method="GET" Call="WhoAmI"/>
</Routes>
}

ClassMethod Out(obj As %DynamicAbstractObject, status As %String = "200") As %Status
{
    Set %response.Status = status
    Do %response.SetHeader("Cache-Control","no-store")
    Write obj.%ToJSON()
    Quit $$$OK
}

ClassMethod Fail(reason As %String, status As %String = "400") As %Status
{
    Quit ..Out({"ok": false, "reason": (reason)}, status)
}

ClassMethod Health() As %Status
{
    Set running = 0, pn = ""
    Try { Set running = ##class(Ens.Director).IsProductionRunning(.pn) && (pn = "pbp.Production") } Catch ex { Set running = 0 }
    Set out = {}
    Do out.%Set("ok", 1, "boolean")
    Do out.%Set("production_running", running, "boolean")
    Set out.mode = $SELECT(##class(pbp.Agent).HasKey() && (##class(pbp.Util).Env("PBP_LLM_MODE", "auto") '= "recorded"): "live", 1: "recorded")
    Set out.provider = ##class(pbp.Agent).ProviderId()
    Set out.model = ##class(pbp.Agent).ModelId()
    Set out."key_variable" = ##class(pbp.Agent).KeyVariable()
    Set last="",ok=0,success="",model=##class(pbp.Agent).ModelId()
    If model'="" {
        Set last=$GET(^pbp.live(##class(pbp.Agent).ProviderId(),model,"last_attempt_at"))
        Set ok=+$GET(^pbp.live(##class(pbp.Agent).ProviderId(),model,"last_attempt_ok"))
        Set success=$GET(^pbp.live(##class(pbp.Agent).ProviderId(),model,"last_ok"))
    }
    Do out.%Set("last_live_call_ok",ok,"boolean")
    Set out."last_live_call_at"=last
    Set out."last_live_success_at"=success
    Set out.spec = "pbp.seal/1"
    Set out.time = ##class(pbp.Util).NowISO()
    Quit ..Out(out)
}

ClassMethod Cases() As %Status
{
    Set limit = +$GET(%request.Data("limit", 1), 50)
    If (limit < 1) || (limit > 500) Set limit = 50
    Set arr = []
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT TOP " _ limit _ " CaseId, StoreId, ExceptionType, Status, StatusReason, CreatedAt, UpdatedAt, HeadCommitment FROM pbp_Data.""Case"" ORDER BY CreatedAt DESC")
    If rs.%SQLCODE < 0 Quit ..Fail("sql_error:" _ rs.%SQLCODE, "500")
    While rs.%Next() {
        Set c = {}
        Set c."case_id" = rs.%Get("CaseId"), c.store = rs.%Get("StoreId"), c.exception = rs.%Get("ExceptionType"), c.status = rs.%Get("Status")
        Set c.reason = rs.%Get("StatusReason"), c."created_at" = rs.%Get("CreatedAt"), c."updated_at" = rs.%Get("UpdatedAt"), c.commitment = rs.%Get("HeadCommitment")
        Do arr.%Push(c)
    }
    Quit ..Out({"ok": true, "cases": (arr)})
}

ClassMethod ReadJSONBody(Output reason As %String) As %String
{
    Set reason="",body=""
    If %request.GetCgiEnv("HTTP_X_PBP_REQUEST")'="1" { Set reason="same_origin_header_required" Quit "" }
    If $ZCONVERT($PIECE(%request.GetCgiEnv("CONTENT_TYPE"),";"),"L")'="application/json" { Set reason="json_content_type_required" Quit "" }
    If $ISOBJECT(%request.Content) {
        While '%request.Content.AtEnd {
            Set body=body_%request.Content.Read(32000)
            If $LENGTH(body)>32000 { Set reason="input_too_large" Quit }
        }
    }
    If reason="" Set reason=##class(pbp.Util).GuardJSON(body,32000)
    Quit $SELECT(reason="":body,1:"")
}

ClassMethod Intake() As %Status
{
    Set body=..ReadJSONBody(.reason)
    If reason'="" Quit ..Fail(reason)
    If body = "" Quit ..Fail("empty_body")
    Set sc = ##class(Ens.Director).CreateBusinessService("pbp.Service.Intake", .svc)
    If $$$ISERR(sc) Quit ..Fail("intake_service_unavailable", "503")
    Set sc = svc.ProcessInput(##class(Ens.StringContainer).%New(body), .out)
    If $$$ISERR(sc) Quit ..Fail($PIECE(##class(pbp.Util).StatusText(sc), " ", 1, 6))
    Quit ..Out({"ok": true, "case_id": (out.CaseId), "status": "received"}, "202")
}

ClassMethod CaseDetail(id As %String) As %Status
{
    Set case = ##class(pbp.Data.Case).Find(id)
    If '$ISOBJECT(case) Quit ..Fail("case_not_found", "404")
    Set out = {}
    Do out.%Set("ok", 1, "boolean")
    Set out.case = ..CaseObj(case)
    Set out.events = ..Events(id)
    Set out.decision = ..DecisionObj(id)
    If $ISOBJECT(out.decision) {
        Set out.decision."denied_tool_calls"=..DeniedToolCalls(id,out.decision."created_at",.denialsAvailable)
        Set out.decision."denied_tool_calls_source"="unsealed_application_log_excerpt"
        Do out.decision.%Set("denied_tool_calls_authoritative",0,"boolean")
        Do out.decision.%Set("denied_tool_calls_available",denialsAvailable,"boolean")
    }
    Set out.review=..ReviewSnapshot(out.decision)
    Set out.seals = ..Seals(id)
    Set out.permit = ..PermitObj(id)
    Set out.receipt = ..ReceiptObj(id)
    Quit ..Out(out)
}

/// Display facts come from the verified decision seal, never the mutable case projection.
/// Stage timestamps use IRIS UTC/Horolog seconds; only a server-computed duration is exposed.
ClassMethod ReviewSnapshot(decision As %DynamicAbstractObject) As %DynamicObject
{
    Set out={"verified":false,"stage_remaining_seconds":null,"stage_ttl_seconds":600}
    If '$ISOBJECT(decision) Quit out
    Try {
        Set seal=##class(pbp.Data.Seal).Find(decision.commitment)
        If $ISOBJECT(seal) {
            Set v=seal.Verify()
            If v.ok {
                Set rec=##class(pbp.Util).ParseJSON(seal.RecordJSON,.reason)
                If $ISOBJECT(rec) && (rec.kind="decision") {
                    Set helper=##class(%SYS.Python).Import("pbp_review.projection")
                    Set out=##class(%DynamicObject).%FromJSON(helper."financial_json"(seal.RecordJSON))
                    Do out.%Set("verified",1,"boolean")
                    Set out."source_commitment"=decision.commitment,out.source="verified_decision_seal.saw.inputs"
                    Set out."stage_ttl_seconds"=##class(ProofBeforePay.Ledger).#VALIDITYSECONDS
                    Do out.%Set("stage_remaining_seconds","","null")
                    Set audit=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Audit(decision.commitment),.reason)
                    If $ISOBJECT(audit) && audit.ok && (audit.%GetTypeOf("expires_utc_seconds")="number") && (audit."expires_utc_seconds">0) {
                        Set out."stage_remaining_seconds"=..RemainingWindow(audit."expires_utc_seconds")
                    }
                }
            }
        }
    } Catch ex {
        Set out={"verified":false,"stage_remaining_seconds":null,"stage_ttl_seconds":600,"reason":"review_snapshot_unavailable"}
        Do ##class(pbp.Util).LogEx("pbp.API.ReviewSnapshot",ex)
    }
    Quit out
}

/// Compare two timestamps in the same server-side UTC/Horolog epoch.
ClassMethod RemainingWindow(expires As %Numeric) As %Integer
{
    If expires<=0 Quit -1
    Set remaining=expires-##class(ProofBeforePay.Ledger).NowSeconds()
    Quit $SELECT(remaining>0:remaining\1,1:0)
}

/// Sanitized, non-authoritative diagnostic excerpt; never counted as observed tool output.
ClassMethod DeniedToolCalls(caseId As %String, cutoff As %String, Output available As %Boolean) As %DynamicArray
{
    Set out=[],available=0
    If cutoff="" Quit out
    Try {
        Set helper=##class(%SYS.Python).Import("pbp_review.projection")
        Set rs=##class(%SQL.Statement).%ExecDirect(,"SELECT TOP 50 ""At"", Message FROM pbp_Data.Log WHERE CaseId=? AND ""Where""='pbp.AuthPolicy' AND ""At""<=? AND Message LIKE '%denied: case id outside the session' ORDER BY ""At"", ID",caseId,cutoff)
        If rs.%SQLCODE>=0 {
            Set available=1
            While rs.%Next() {
                Set name=helper."denied_tool_name"(rs.%Get("Message"))
                Do out.%Push({"tool":(name),"reason_code":"case_not_in_session","at":(rs.%Get("At"))})
            }
        }
    } Catch ex {
        Set available=0
    }
    Quit out
}

ClassMethod CaseObj(case As pbp.Data.Case) As %DynamicObject
{
    Set c = {}
    Set c."case_id" = case.CaseId, c.store = case.StoreId, c.exception = case.ExceptionType, c.status = case.Status, c.reason = case.StatusReason
    Set c."created_at" = case.CreatedAt, c."updated_at" = case.UpdatedAt, c.commitment = case.HeadCommitment
    Set c."session_id" = case.SessionId, c.policy = {"id": (case.PolicyId), "version": (case.PolicyVersion)}
    Set inp = case.Input()
    If $ISOBJECT(inp) Do c.%Set("input", inp)
    Quit c
}

ClassMethod Events(caseId As %String) As %DynamicArray
{
    Set arr = []
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT ""At"", Kind, Detail, ""Ref"" FROM pbp_Data.Event WHERE CaseId = ? ORDER BY ""At"", ID", caseId)
    While rs.%Next() { Do arr.%Push({"at": (rs.%Get("At")), "kind": (rs.%Get("Kind")), "detail": (rs.%Get("Detail")), "ref": (rs.%Get("Ref"))}) }
    Quit arr
}

ClassMethod DecisionObj(caseId As %String) As %DynamicAbstractObject
{
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT TOP 1 Source, Action, MovesMoney, AmountMinor, RequiresHuman, Confidence, Rationale, EvidenceRefs, MissingJSON, ProposalJSON, ProposalReason, Temperature, ModelProvider, ModelId, Mode, PromptTokens, CompletionTokens, DurationMs, CostMicroUSD, ToolCalls, Commitment, CreatedAt FROM pbp_Data.Decision WHERE CaseId = ? ORDER BY ID DESC", caseId)
    If 'rs.%Next() Quit ""
    Set d = {}
    Set d.source = rs.%Get("Source"), d.action = rs.%Get("Action")
    Do d.%Set("moves_money", rs.%Get("MovesMoney"), "boolean")
    Set d."amount_minor" = rs.%Get("AmountMinor")
    Do d.%Set("requires_human", rs.%Get("RequiresHuman"), "boolean")
    Do d.%Set("confidence", +rs.%Get("Confidence"), "number")
    Set d.rationale = rs.%Get("Rationale")
    Set d."evidence_refs" = ##class(pbp.Util).ParseJSON(rs.%Get("EvidenceRefs"), .r)
    Set d.missing = ##class(pbp.Util).ParseJSON(rs.%Get("MissingJSON"), .r)
    Set proposal=##class(pbp.Util).ParseJSON(rs.%Get("ProposalJSON"),.r)
    If $ISOBJECT(proposal) { Do d.%Set("proposal",proposal) }
    Else { Do d.%Set("proposal","","null") }
    Set d."proposal_reason"=rs.%Get("ProposalReason"),d."proposal_integrity"="unsealed_diagnostic"
    Do d.%Set("proposal_authoritative",0,"boolean")
    Do d.%Set("proposal_refused",(rs.%Get("ProposalReason")'=""),"boolean")
    Set d.model = {"provider": (rs.%Get("ModelProvider")), "id": (rs.%Get("ModelId")), "mode": (rs.%Get("Mode"))}
    Set temp=$SELECT(rs.%Get("Temperature")="":-1,1:+rs.%Get("Temperature"))
    Set d.model.temperature=temp
    Do d.model.%Set("temperature_known",(temp'=-1),"boolean")
    Set d.usage = {"prompt_tokens": (+rs.%Get("PromptTokens")), "completion_tokens": (+rs.%Get("CompletionTokens")), "duration_ms": (+rs.%Get("DurationMs")), "cost_micro_usd": (+rs.%Get("CostMicroUSD")), "tool_calls": (+rs.%Get("ToolCalls"))}
    Set d.commitment = rs.%Get("Commitment"), d."created_at" = rs.%Get("CreatedAt")
    Quit d
}

ClassMethod Seals(caseId As %String) As %DynamicArray
{
    Set arr = []
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT Commitment FROM pbp_Data.Seal WHERE CaseId = ? ORDER BY ID", caseId)
    While rs.%Next() {
        Set seal = ##class(pbp.Data.Seal).Find(rs.%Get("Commitment"))
        If $ISOBJECT(seal) Do arr.%Push(..SealObj(seal, 0))
    }
    Quit arr
}

/// Public view of a seal: commitment, kind, chain, state from a fresh verification, and the ordering check.
/// Salt and record are private; `withRecord` reveals the record (not the salt) for the verifier and the time machine.
ClassMethod SealObj(seal As pbp.Data.Seal, withRecord As %Boolean) As %DynamicObject
{
    Set v = seal.Verify()
    Set s = {}
    Set s.commitment = seal.Commitment, s."case_id" = seal.CaseId, s.kind = seal.Kind, s.memo = seal.Memo
    Do s.%Set("prev", $SELECT(seal.Prev = "": "", 1: seal.Prev), $SELECT(seal.Prev = "": "null", 1: "string"))
    Set s."sealed_at" = seal.SealedAt
    Set s."stored_state" = seal.State, s."anchor_ref" = seal.AnchorRef
    Set s.source=seal.Source,s."ledger_state"=seal.LedgerState
    Set moved = seal.MoneyMovedBefore()
    Do s.%Set("money_moved_before_seal", moved, "boolean")
    Set state = $SELECT('v.ok && (v.state = "tampered"): "tampered", 'v.ok: "unverifiable", moved: "sealed_after_money_moved", 1: "intact")
    Set s.verification = {"state": (state), "bridge_state": (v.state), "reason": (v.reason)}
    Do s.verification.%Set("on_chain_verified", ''v."on_chain_verified", "boolean")
    If withRecord {
        Set rec = ##class(pbp.Util).ParseJSON(seal.RecordJSON, .r)
        If $ISOBJECT(rec) Do s.%Set("record", rec)
    }
    Quit s
}

ClassMethod PermitObj(caseId As %String) As %DynamicAbstractObject
{
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT TOP 1 PermitId FROM pbp_Data.Permit WHERE CaseId = ? ORDER BY ID DESC", caseId)
    If 'rs.%Next() Quit ""
    Set p = ##class(pbp.Data.Permit).Find(rs.%Get("PermitId"))
    If '$ISOBJECT(p) Quit ""
    Set out={"permit_id": (p.PermitId), "commitment": (p.Commitment), "amount_minor": (p.AmountMinor), "currency": (p.Currency), "recipient": (p.Recipient), "status": (p.Status), "issued_at": (p.IssuedAt), "expires_at": (p.ExpiresAt), "consumed_at": (p.ConsumedAt), "authorized_by": (p.AuthorizedBy), "approval_commitment": (p.ApprovalCommitment), "receipt_id": (p.ReceiptId)}
    Do out.%Set("remaining_seconds","","null")
    Set expires=##class(pbp.Util).ISOToSeconds(p.ExpiresAt)
    If expires>0 {
        Set out."remaining_seconds"=..RemainingWindow(expires)
    }
    Quit out
}

ClassMethod ReceiptObj(caseId As %String) As %DynamicAbstractObject
{
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT TOP 1 ReceiptId, PermitId, Commitment, AmountMinor, Currency, Recipient, Status, LedgerRef, EffectAt FROM pbp_Data.Receipt WHERE CaseId = ? ORDER BY ID DESC", caseId)
    If 'rs.%Next() Quit ""
    Set out={"receipt_id": (rs.%Get("ReceiptId")), "permit_id": (rs.%Get("PermitId")), "commitment": (rs.%Get("Commitment")), "amount_minor": (rs.%Get("AmountMinor")), "currency": (rs.%Get("Currency")), "recipient": (rs.%Get("Recipient")), "status": (rs.%Get("Status")), "ledger_ref": (rs.%Get("LedgerRef")), "effect_at": (rs.%Get("EffectAt"))}
    Set row=##class(pbp.Data.Receipt).ReceiptIdxOpen(rs.%Get("ReceiptId"))
    Set authority=##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Audit(row.Commitment),.r)
    Set out.verification="unverifiable"
    If $ISOBJECT(authority) && authority.ok && authority."receipt_integrity_verified" {
        Set out.verification=$SELECT(row.Matches(authority.receipt):"intact",1:"tampered")
    }
    Quit out
}

ClassMethod SealDetail(c As %String) As %Status
{
    Set seal = ##class(pbp.Data.Seal).Find(c)
    If '$ISOBJECT(seal) Quit ..Fail("seal_not_found", "404")
    Set out = ..SealObj(seal, 1)
    Do out.%Set("ok", 1, "boolean")
    Quit ..Out(out)
}

/// "Try to tamper": verify an edited copy of the record against the stored commitment. Nothing is stored.
ClassMethod VerifyCopy(c As %String) As %Status
{
    Set seal = ##class(pbp.Data.Seal).Find(c)
    If '$ISOBJECT(seal) Quit ..Fail("seal_not_found", "404")
    Set body=..ReadJSONBody(.reason)
    If reason'="" Quit ..Fail(reason)
    Set obj = ##class(pbp.Util).ParseJSON(body, .reason)
    If (obj = "") || '$ISOBJECT(obj.record) Quit ..Fail("body_must_contain_record")
    Set v = seal.Verify(obj.record.%ToJSON())
    Set out = {}
    Do out.%Set("ok", 1, "boolean")
    Set out.commitment = seal.Commitment
    Set out.state = $SELECT(v.ok: "intact", v.state = "tampered": "tampered", 1: "unverifiable")
    Set out.reason = v.reason
    Quit ..Out(out)
}

/// Time machine: everything the agent saw and did not see, straight from the sealed record, plus the trace session.
ClassMethod Replay(id As %String) As %Status
{
    Set case = ##class(pbp.Data.Case).Find(id)
    If '$ISOBJECT(case) Quit ..Fail("case_not_found", "404")
    Set out = {}
    Do out.%Set("ok", 1, "boolean")
    Set out."case_id" = id, out."session_id" = case.SessionId
    Set steps = []
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT Commitment FROM pbp_Data.Seal WHERE CaseId = ? ORDER BY ID", id)
    While rs.%Next() {
        Set seal = ##class(pbp.Data.Seal).Find(rs.%Get("Commitment"))
        Continue:'$ISOBJECT(seal)
        Set s = ..SealObj(seal, 1)
        Do steps.%Push(s)
    }
    Set out.steps = steps
    Set tools = []
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT Seq, Name, ArgsJSON, OutputJSON, DurationMs, ""At"" FROM pbp_Data.ToolCall WHERE CaseId = ? ORDER BY Seq", id)
    While rs.%Next() {
        Set t = {"seq": (rs.%Get("Seq")), "name": (rs.%Get("Name")), "duration_ms": (rs.%Get("DurationMs")), "at": (rs.%Get("At"))}
        Set a = ##class(pbp.Util).ParseJSON(rs.%Get("ArgsJSON"), .r)
        If $ISOBJECT(a) Do t.%Set("args", a)
        Set o = ##class(pbp.Util).ParseJSON(rs.%Get("OutputJSON"), .r)
        If $ISOBJECT(o) { Do t.%Set("output", o) } Else { Set t.output = rs.%Get("OutputJSON") }
        Do tools.%Push(t)
    }
    Set out."tool_calls" = tools
    Set out.decision = ..DecisionObj(id)
    Quit ..Out(out)
}

ClassMethod Stats() As %Status
{
    Set out = {}
    Do out.%Set("ok", 1, "boolean")
    Set byStatus = {}
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT Status, COUNT(*) AS N FROM pbp_Data.""Case"" GROUP BY Status")
    While rs.%Next() { Do byStatus.%Set($ZCONVERT(rs.%Get("Status"),"L"), +rs.%Get("N"), "number") }
    Set out."cases_by_status" = byStatus
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT Source, COUNT(*) AS N, SUM(PromptTokens) AS P, SUM(CompletionTokens) AS C, SUM(CostMicroUSD) AS Cost, SUM(CASE WHEN CostMicroUSD < 0 THEN 1 ELSE 0 END) AS UnknownCosts, AVG(DurationMs) AS D FROM pbp_Data.Decision GROUP BY Source")
    Set bySource = {}
    While rs.%Next() { Do bySource.%Set($ZCONVERT(rs.%Get("Source"),"L"), {"decisions": (+rs.%Get("N")), "prompt_tokens": (+rs.%Get("P")), "completion_tokens": (+rs.%Get("C")), "cost_micro_usd": ($SELECT(+rs.%Get("UnknownCosts")>0:-1,1:+rs.%Get("Cost"))), "avg_duration_ms": (+rs.%Get("D"))}) }
    Set out."decisions_by_source" = bySource
    // Recorded fixture usage is not paid inference. Keep separate buckets for the reviewer UI.
    Set byMode = {}
    For bucket="live","recorded","unknown" {
        Do byMode.%Set(bucket,{"decisions":0,"prompt_tokens":0,"completion_tokens":0,"known_cost_micro_usd":0,"unknown_cost_decisions":0,"cost_micro_usd":0,"billing_verified":false})
    }
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT Mode, COUNT(*) AS N, SUM(PromptTokens) AS P, SUM(CompletionTokens) AS C, SUM(CASE WHEN CostMicroUSD >= 0 THEN CostMicroUSD ELSE 0 END) AS KnownCost, SUM(CASE WHEN CostMicroUSD IS NULL OR CostMicroUSD < 0 THEN 1 ELSE 0 END) AS UnknownCosts FROM pbp_Data.Decision WHERE Source = 'model' GROUP BY Mode")
    While rs.%Next() {
        Set bucket=$ZCONVERT(rs.%Get("Mode"),"L")
        If (bucket'="live") && (bucket'="recorded") Set bucket="unknown"
        Set usage=byMode.%Get(bucket)
        Set usage.decisions=usage.decisions+rs.%Get("N")
        Set usage."prompt_tokens"=usage."prompt_tokens"+rs.%Get("P")
        Set usage."completion_tokens"=usage."completion_tokens"+rs.%Get("C")
        Set usage."known_cost_micro_usd"=usage."known_cost_micro_usd"+rs.%Get("KnownCost")
        Set usage."unknown_cost_decisions"=usage."unknown_cost_decisions"+rs.%Get("UnknownCosts")
        Set usage."cost_micro_usd"=$SELECT(usage."unknown_cost_decisions">0:-1,1:usage."known_cost_micro_usd")
    }
    Set out."model_decisions_by_mode"=byMode
    Set out."usage_cost_basis"="stored_decision_metadata_not_billing"
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT COUNT(*) AS N FROM pbp_Data.Seal")
    If rs.%Next() Do out.%Set("seals", +rs.%Get("N"), "number")
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT COUNT(*) AS N FROM pbp_Data.Receipt WHERE Status = 'effected'")
    If rs.%Next() Do out.%Set("effects", +rs.%Get("N"), "number")
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT COUNT(*) AS N FROM pbp_Data.Event WHERE Kind = 'duplicate_effect_prevented'")
    If rs.%Next() Do out.%Set("duplicate_effects_prevented", +rs.%Get("N"), "number")
    Quit ..Out(out)
}

/// Test-ledger state for a commitment (no salt, no record).
ClassMethod Ledger(c As %String) As %Status
{
    Set read = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Audit(c), .r)
    If read = "" Quit ..Fail("ledger_reply_invalid_json", "500")
    Quit ..Out(read, $SELECT(read.ok: "200", 1: "404"))
}

/// Cases waiting for a reviewer.
ClassMethod ReviewList() As %Status
{
    Quit ..Out({"ok": true, "user": ($USERNAME), "can_review": (''$SYSTEM.Security.Check("PBPReview", "U")), "pending": (##class(pbp.Review).Pending())})
}

/// Approve or reject as the authenticated user: body {"action":"Approve"|"Reject","note":"..."}.
ClassMethod ReviewAct(id As %String) As %Status
{
    Set body=..ReadJSONBody(.reason)
    If reason'="" Quit ..Fail(reason)
    Set obj = ##class(pbp.Util).ParseJSON(body, .reason)
    If obj = "" Quit ..Fail("body_invalid_json")
    Set out = ##class(pbp.Review).Act(id, obj.action, obj.note, obj.commitment)
    Quit ..Out(out, $SELECT(out.ok: "200", out.reason [ "forbidden": "403", 1: "409"))
}

ClassMethod WhoAmI() As %Status
{
    Quit ..Out({"ok": true, "user": ($USERNAME), "can_review": (''$SYSTEM.Security.Check("PBPReview", "U"))})
}

}
