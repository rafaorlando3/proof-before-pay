/// The decision workflow for one payment exception. Order of operations is the product:
///   intake -> deterministic rules -> (AI Hub agent if needed) -> policy enforced server-side ->
///   SEAL the decision (what was seen, what was missing, what was forbidden) ->
///   permit (within limit) or native human task (Workflow) -> sealed approval -> single-use permit ->
///   test ledger effect -> receipt. Nothing moves before the seal; an uncertain ledger answer stops the
///   case for reconciliation instead of retrying into a second effect.
Class pbp.Process.Decide Extends Ens.BusinessProcess
{

Parameter SETTINGS = "AgentTarget:Basic,ReplayTarget:Basic,WitnessTarget:Basic,LedgerTarget:Basic,WorkflowTarget:Basic,PermitValiditySeconds:Basic,AutonomousEffects:Basic,MaxHumanRounds:Basic";

/// Live AI Hub agent (used only when a provider key is present and PBP_LLM_MODE is not "recorded").
Property AgentTarget As Ens.DataType.ConfigName [ InitialExpression = "pbp.Operation.Agent" ];

/// Recorded decisions (no key): honest replay, labelled as such in every sealed record.
Property ReplayTarget As Ens.DataType.ConfigName [ InitialExpression = "pbp.Operation.Replay" ];

/// How many times a reviewer may be asked again when the test ledger has not been authorized in their session.
Property MaxHumanRounds As %Integer [ InitialExpression = 3 ];

Property WitnessTarget As Ens.DataType.ConfigName [ InitialExpression = "pbp.Operation.Witness" ];

Property LedgerTarget As Ens.DataType.ConfigName [ InitialExpression = "pbp.Operation.TestLedger" ];

Property WorkflowTarget As Ens.DataType.ConfigName [ InitialExpression = "pbp.Workflow" ];

Property PermitValiditySeconds As %Integer [ InitialExpression = 600 ];

/// When 0 (v1 default, test-ledger policy), every money movement goes to a person regardless of the policy limit.
Property AutonomousEffects As %Boolean [ InitialExpression = 0 ];

/// Ledger state recorded at sealing time for money decisions ("awaiting_approval" or "blocked:<reason>").
Property LedgerState As %String(MAXLEN = 128);

Property HumanRounds As %Integer [ InitialExpression = 0 ];

Property CaseId As %String(MAXLEN = 64);

Property StoreId As %String(MAXLEN = 64);

Property ExceptionType As %String(MAXLEN = 64);

Property PolicyId As %String(MAXLEN = 64);

Property PolicyVersion As %String(MAXLEN = 32);

Property PolicySha As %String(MAXLEN = 64);

Property RulesResult As %String(MAXLEN = 256);

/// Projection of the final (policy-enforced) decision as JSON.
Property DecisionJSON As %String(MAXLEN = "");

/// Evidence the agent did not have (JSON object, null values), kept for the reviewer's task.
Property MissingJSON As %String(MAXLEN = 4000);

Property Commitment As %String(MAXLEN = 64);

Property ApprovalCommitment As %String(MAXLEN = 64);

Property PermitId As %String(MAXLEN = 64);

Property Recipient As %String(MAXLEN = 64);

Property AmountMinor As %String(MAXLEN = 20);

Property Currency As %String(MAXLEN = 3);

Property Operator As %String(MAXLEN = 64);

Property Outcome As %String(MAXLEN = 16);

Method OnRequest(pRequest As pbp.Msg.CaseRequest, Output pResponse As Ens.Response) As %Status
{
    Set pResponse = ""
    Set ..CaseId = pRequest.CaseId
    Set ..StoreId = pRequest.StoreId
    Set ..ExceptionType = pRequest.ExceptionType
    Set input = ##class(pbp.Util).ParseJSON(pRequest.InputJSON, .reason)
    If input = "" Quit ..Block("input_invalid_json")
    // Idempotent intake: a case id that already exists is not processed twice.
    Set case = ##class(pbp.Data.Case).Find(..CaseId)
    If $ISOBJECT(case) {
        Do ##class(pbp.Util).Log("warn", "pbp.Process.Decide", "duplicate intake ignored (status " _ case.Status _ ")", ..CaseId)
        Do ##class(pbp.Data.Event).Add(..CaseId, "duplicate_intake_ignored", "status " _ case.Status, "")
        Quit $$$OK
    }
    Set case = ##class(pbp.Data.Case).%New()
    Set case.CaseId = ..CaseId
    Set case.StoreId = ..StoreId
    Set case.ExceptionType = ..ExceptionType
    Set case.InputJSON = pRequest.InputJSON
    Set case.CreatedAt = ##class(pbp.Util).NowISO()
    Set case.SessionId = ..%SessionId
    Set pol = ##class(pbp.Data.Policy).ActiveFor(..StoreId)
    If '$ISOBJECT(pol) { Do case.%Save() Quit ..Block("policy_not_found") }
    Set ..PolicyId = pol.PolicyId, ..PolicyVersion = pol.Version, ..PolicySha = pol.Sha256
    Set case.PolicyId = pol.PolicyId, case.PolicyVersion = pol.Version
    Set sc = case.SetStatus("received", ..ExceptionType, "")
    If $$$ISERR(sc) Quit ..Block("case_save_failed: " _ ##class(pbp.Util).StatusText(sc))
    Set input = ..Normalize(input, pol)
    Set case.InputJSON = input.%ToJSON()
    Do case.%Save()
    Set ..Recipient = input."recipient_ref"
    Set ..Currency = input.currency

    Set rules = ##class(pbp.Rules).Evaluate(input, pol.Object())
    Set ..RulesResult = $SELECT(rules.decided: rules.rule _ ":" _ rules.action, 1: "no_match")
    If rules."refund_payment_ref" '= "" {
        Set input."refund_payment_ref" = rules."refund_payment_ref"
        Set case.InputJSON = input.%ToJSON()
        Do case.%Save()
    }
    If rules.decided {
        Do case.SetStatus("rules_decided", ..RulesResult, "")
        Set record = ..BuildDecisionRecord(input, pol, rules, "", [])
        If record = "" Quit ..Block("record_build_failed")
        Quit ..SendSeal("decision", record, "seal_decision")
    }
    Set req = ##class(pbp.Msg.DecisionRequest).%New()
    Set req.CaseId = ..CaseId, req.StoreId = ..StoreId, req.PolicyId = ..PolicyId, req.PolicyVersion = ..PolicyVersion, req.RulesResult = ..RulesResult
    Set live = ##class(pbp.Agent).HasKey() && (##class(pbp.Util).Env("PBP_LLM_MODE", "auto") '= "recorded")
    Set target = $SELECT(live: ..AgentTarget, 1: ..ReplayTarget)
    Do case.SetStatus("agent_requested", $SELECT(live: "live agent", 1: "recorded decisions (no key)"), "")
    Quit ..SendRequestAsync(target, req, 1, "agent")
}

/// Canonical input shape shared by rules, agent tools and the test-ledger contract, preserving the original fields:
/// environment "sandbox", currency, order_amount_minor, payments[{payment_ref,amount_minor,payer,received_at}]
/// (built from a legacy "pix" array when needed), recipient_ref (test:...).
Method Normalize(input As %DynamicObject, pol As pbp.Data.Policy) As %DynamicObject
{
    Set input.environment = "sandbox"
    If input.currency = "" Set input.currency = $SELECT($ISOBJECT(input.order) && (input.order.currency '= ""): input.order.currency, 1: pol.Object().limits.currency)
    If $ISOBJECT(input.order) && (input."order_amount_minor" = "") Set input."order_amount_minor" = input.order."amount_minor"
    If '$ISOBJECT(input.payments) && $ISOBJECT(input.pix) {
        Set pays = []
        Set it = input.pix.%GetIterator()
        While it.%GetNext(.k, .p) {
            Continue:'$ISOBJECT(p)
            Set q = {}
            Set q."payment_ref" = $SELECT(p."payment_ref" '= "": p."payment_ref", 1: "pix:" _ p.e2e)
            Set q."amount_minor" = p."amount_minor"
            Set q.payer = $SELECT($EXTRACT(p.payer, 1, 5) = "test:": p.payer, 1: "test:" _ p.payer)
            Set q."received_at" = p."received_at"
            Do pays.%Push(q)
        }
        Set input.payments = pays
    }
    If (input."recipient_ref" = "") && (input.recipient '= "") Set input."recipient_ref" = $SELECT($EXTRACT(input.recipient, 1, 5) = "test:": input.recipient, 1: "test:" _ input.recipient)
    Quit input
}

Method OnResponse(request As Ens.Request, ByRef response As Ens.Response, callrequest As Ens.Request, callresponse As Ens.Response, pCompletionKey As %String) As %Status
{
    Set case = ##class(pbp.Data.Case).Find(..CaseId)
    If pCompletionKey = "agent" Quit ..OnAgent(case, callresponse)
    If pCompletionKey = "seal_decision" Quit ..OnSealDecision(case, callresponse)
    If pCompletionKey = "human" Quit ..OnHuman(case, callresponse)
    If pCompletionKey = "seal_approval" Quit ..OnSealApproval(case, callresponse)
    If pCompletionKey = "ledger" Quit ..OnLedger(case, callresponse)
    Quit ..Block("unknown_completion_key:" _ pCompletionKey)
}

/// The agent answered (or failed closed). Policy is enforced here, never trusted from the model.
Method OnAgent(case As pbp.Data.Case, resp As pbp.Msg.DecisionResponse) As %Status
{
    If '$ISOBJECT(resp) Quit ..Block("agent_no_response")
    Set pol = ##class(pbp.Data.Policy).IdVerOpen(..PolicyId, ..PolicyVersion)
    Set input = case.Input()
    If 'resp.Ok {
        // Fail closed: a sealed escalation, no effect.
        Set d = {}
        Set d.action = "escalate_to_human"
        Do d.%Set("moves_money", 0, "boolean")
        Do d.%Set("requires_human", 1, "boolean")
        Set d.confidence = 0
        Set d.rationale = "The model did not return a valid decision (" _ $EXTRACT(resp.Reason, 1, 120) _ "); a person decides."
        Set d."evidence_refs" = ["order"]
        Set d.missing = ##class(pbp.Rules).Missing(input)
        // Keep the proposal's declared ignorance even when its action/refs fail contextual validation.
        Set wanted=##class(pbp.Util).ParseJSON(resp.MissingJSON,.r)
        If $ISOBJECT(wanted) {
            Set it=wanted.%GetIterator()
            While it.%GetNext(.k,.v) {
                If wanted.%GetTypeOf(k)="null" Do d.missing.%Set(k,"","null")
            }
        }
        Do case.SetStatus("agent_failed", resp.Reason, "")
        Set record = ..BuildDecisionRecord(input, pol, d, resp, ..ToolsOf(resp))
        If record = "" Quit ..Block("record_build_failed")
        Quit ..SendSeal("decision", record, "seal_decision")
    }
    Set d = {}
    Set d.action = resp.Action
    Do d.%Set("moves_money", resp.MovesMoney, "boolean")
    If resp.MovesMoney Set d."amount_minor" = resp.AmountMinor
    Do d.%Set("requires_human", resp.RequiresHuman, "boolean")
    Set d.confidence = +resp.Confidence
    Set d.rationale = resp.Rationale
    Set d."evidence_refs" = ##class(pbp.Util).ParseJSON(resp.EvidenceRefsJSON, .r)
    Set d.missing = ##class(pbp.Util).ParseJSON(resp.MissingJSON, .r)
    If '$ISOBJECT(d.missing) Set d.missing = {}
    Do case.SetStatus("agent_decided", resp.Action _ " (" _ resp.Mode _ ", " _ resp.ModelId _ ")", "")
    Set record = ..BuildDecisionRecord(input, pol, d, resp, ..ToolsOf(resp))
    If record = "" Quit ..Block("record_build_failed")
    Quit ..SendSeal("decision", record, "seal_decision")
}

Method ToolsOf(resp As pbp.Msg.DecisionResponse) As %DynamicArray
{
    Set t = ##class(pbp.Util).ParseJSON(resp.ToolsJSON, .r)
    Quit $SELECT($ISOBJECT(t): t, 1: [])
}

/// Build the pbp.seal/1 decision record with server-side policy enforcement:
///  - an action in the forbidden list becomes escalate_to_human;
///  - money above the autonomous limit (or any money when AutonomousEffects=0, or recipient unknown) requires a human;
///  - the agent's rationale and evidence are kept as given; the enforcement is recorded in the rationale.
Method BuildDecisionRecord(input As %DynamicObject, pol As pbp.Data.Policy, d As %DynamicObject, resp As pbp.Msg.DecisionResponse, tools As %DynamicArray) As %String
{
    Set json = ""
    Try {
        Set polObj = pol.Object()
        Set forbidden = pol.ForbiddenSorted()
        Set limit = polObj.limits."autonomous_minor"
        If '..AutonomousEffects Set limit = "0"
        Set action = d.action
        Set moves = ''d."moves_money"
        Set human = ''d."requires_human"
        Set amount = d."amount_minor"
        Set rationale = d.rationale
        Set enforced = ""
        Set allowed = polObj."allowed_actions"
        Set isAllowed = 0
        If $ISOBJECT(allowed) { Set it = allowed.%GetIterator() While it.%GetNext(.k, .v) { If v = action Set isAllowed = 1 } }
        Set isForbidden = 0
        Set it = forbidden.%GetIterator() While it.%GetNext(.k, .v) { If v = action Set isForbidden = 1 }
        If isForbidden || 'isAllowed {
            Set enforced = enforced _ " Policy: action '" _ action _ "' is not allowed; escalated to a person."
            Set action = "escalate_to_human", moves = 0, human = 1, amount = ""
        }
        If moves {
            If (amount = "") || '##class(pbp.Util).IsMinorAmount(amount) || (amount = "0") {
                Set enforced = enforced _ " Policy: amount unknown or invalid; a person must confirm."
                Set human = 1
            } ElseIf (limit = "0") || (+amount > +limit) {
                If 'human Set enforced = enforced _ " Policy: amount above the autonomous limit; a person must approve."
                Set human = 1
            }
            If ..Recipient = "" {
                If 'human Set enforced = enforced _ " Policy: refund destination unknown; a person must choose it."
                Set human = 1
                Do d.missing.%Set("refund_target", "", "null")
            }
        }
        If enforced '= "" Set rationale = $EXTRACT(rationale _ enforced, 1, 800)
        Set ..AmountMinor = $SELECT(moves: amount, 1: "")

        Set r = {}
        Set r.v = "pbp.seal/1"
        Set r.kind = "decision"
        Set r.at = ##class(pbp.Util).NowISO()
        Set r.case = {}
        Set r.case.id = ..CaseId
        Set r.case.exception = ..ExceptionType
        Set r.case.store = ..StoreId
        Set saw = {}
        Do saw.%Set("inputs", input)
        Do saw.%Set("tools", tools)
        Do r.%Set("saw", saw)
        Do r.%Set("missing", d.missing)
        Set r.policy = {}
        Set r.policy.id = pol.PolicyId, r.policy.version = pol.Version, r.policy.sha256 = pol.Sha256
        Set r.rules = {}
        Set r.rules.engine = ##class(pbp.Rules).#ENGINE, r.rules.version = ##class(pbp.Rules).#VERSION, r.rules.result = ..RulesResult
        If $ISOBJECT(resp) {
            Set m = {}
            Set m.provider = resp.ModelProvider, m.id = resp.ModelId, m.mode = resp.Mode
            Do m.%Set("temperature", +resp.Temperature, "number")
            Do r.%Set("model", m)
        } Else {
            Do r.%Set("model", "", "null")
        }
        Set dec = {}
        Set dec.action = action
        Do dec.%Set("moves_money", moves, "boolean")
        If moves Set dec."amount_minor" = amount
        Do dec.%Set("requires_human", human, "boolean")
        Do dec.%Set("confidence", +d.confidence, "number")
        Set dec.rationale = rationale
        Set dec."evidence_refs" = d."evidence_refs"
        Do r.%Set("decision", dec)
        Do r.%Set("forbidden", forbidden)
        Set lim = {}
        Set lim."autonomous_minor" = limit, lim.currency = polObj.limits.currency
        Do r.%Set("limits", lim)
        Set case = ##class(pbp.Data.Case).Find(..CaseId)
        If $ISOBJECT(case) && (case.HeadCommitment '= "") { Set r.prev = case.HeadCommitment } Else { Do r.%Set("prev", "", "null") }
        Set ..DecisionJSON = dec.%ToJSON()
        Set ..MissingJSON = d.missing.%ToJSON()
        Do ..SaveDecisionRow(d, dec, resp, tools)
        Set json = r.%ToJSON()
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Process.Decide.BuildDecisionRecord", ex, ..CaseId)
        Set json = ""
    }
    Quit json
}

Method SaveDecisionRow(d As %DynamicObject, dec As %DynamicObject, resp As pbp.Msg.DecisionResponse, tools As %DynamicArray)
{
    Try {
        Set row = ##class(pbp.Data.Decision).%New()
        Set row.CaseId = ..CaseId
        Set row.Source = $SELECT($ISOBJECT(resp): "model", 1: "rules")
        Set row.Action = dec.action
        Set row.MovesMoney = dec."moves_money"
        Set row.AmountMinor = dec."amount_minor"
        Set row.RequiresHuman = dec."requires_human"
        Set row.Confidence = dec.confidence
        Set row.Rationale = dec.rationale
        Set row.EvidenceRefs = dec."evidence_refs".%ToJSON()
        Set row.MissingJSON = d.missing.%ToJSON()
        If $ISOBJECT(resp) {
            Set row.ModelProvider = resp.ModelProvider, row.ModelId = resp.ModelId, row.Mode = resp.Mode
            Set row.PromptTokens = resp.PromptTokens, row.CompletionTokens = resp.CompletionTokens
            Set row.DurationMs = resp.DurationMs, row.CostMicroUSD = resp.CostMicroUSD
        } Else {
            Set row.Mode = "none", row.ModelProvider = "", row.ModelId = ""
            Set row.PromptTokens = 0, row.CompletionTokens = 0, row.DurationMs = 0, row.CostMicroUSD = 0
        }
        Set row.ToolCalls = tools.%Size()
        Set row.CreatedAt = ##class(pbp.Util).NowISO()
        Set sc = row.%Save()
        If $$$ISERR(sc) Do ##class(pbp.Util).Log("error", "pbp.Process.Decide.SaveDecisionRow", ##class(pbp.Util).StatusText(sc), ..CaseId)
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Process.Decide.SaveDecisionRow", ex, ..CaseId)
    }
}

Method SendSeal(kind As %String, recordJSON As %String, key As %String) As %Status
{
    Set req = ##class(pbp.Msg.SealRequest).%New()
    Set req.CaseId = ..CaseId, req.Kind = kind, req.RecordJSON = recordJSON
    Quit ..SendRequestAsync(..WitnessTarget, req, 1, key)
}

/// The decision is sealed. Now, and only now, something may happen.
Method OnSealDecision(case As pbp.Data.Case, resp As pbp.Msg.SealResponse) As %Status
{
    If '$ISOBJECT(resp) || 'resp.Ok Quit ..Block("seal_failed:" _ $SELECT($ISOBJECT(resp): resp.Reason, 1: "no_response"))
    Set ..Commitment = resp.Commitment
    Set ..LedgerState = resp.LedgerState
    Do ..LinkDecisionRow(resp.Commitment)
    Set dec = ##class(pbp.Util).ParseJSON(..DecisionJSON, .r)
    If dec."requires_human" || dec."moves_money" {
        Quit ..AskHuman(case, dec)
    }
    Quit ..Close(case, "closed", "no money movement: " _ dec.action)
}

Method LinkDecisionRow(commitment As %String)
{
    Set caseId=..CaseId
    &sql(UPDATE pbp_Data.Decision SET Commitment = :commitment WHERE CaseId = :caseId AND Commitment IS NULL)
}

/// Native Interoperability Workflow task. The reviewer sees the sealed decision and approves or rejects.
Method AskHuman(case As pbp.Data.Case, dec As %DynamicObject) As %Status
{
    Set task = ##class(EnsLib.Workflow.TaskRequest).%New()
    Set task.%Actions = "Approve,Reject"
    Set task.%Subject = "Proof Before Pay: " _ ..CaseId _ " (" _ dec.action _ $SELECT(dec."moves_money": ", " _ dec."amount_minor" _ " " _ ..Currency, 1: "") _ ")"
    Set task.%Message = "Sealed decision " _ ..Commitment _ $CHAR(13,10) _ "Action: " _ dec.action _ $CHAR(13,10) _ "Moves money: " _ dec."moves_money" _ $SELECT(dec."moves_money": " (" _ dec."amount_minor" _ " " _ ..Currency _ " to " _ $SELECT(..Recipient = "": "UNKNOWN recipient", 1: ..Recipient) _ ")", 1: "") _ $CHAR(13,10) _ "Rationale: " _ dec.rationale _ $CHAR(13,10) _ "Missing evidence: " _ ..MissingJSON _ $CHAR(13,10) _ $SELECT(..LedgerState = "": "", 1: "Test ledger: " _ ..LedgerState _ $CHAR(13,10)) _ "Review in the Proof Before Pay console (/pbp/ui), which records your approval in the test ledger under your own IRIS login and completes this task. Approving issues a single-use permit bound to this seal; editing anything after the seal invalidates it." _ $SELECT(..HumanRounds > 0: $CHAR(13,10) _ "Round " _ (..HumanRounds + 1) _ ": the previous approval was not recorded in the test ledger under your login. Use the console.", 1: "")
    Set task.%Priority = 2
    Set task.%FormFields = "Note"
    Set ..HumanRounds = ..HumanRounds + 1
    Do case.SetStatus("awaiting_human", dec.action _ $SELECT(..LedgerState = "": "", 1: " (ledger " _ ..LedgerState _ ")"), ..Commitment)
    Quit ..SendRequestAsync(..WorkflowTarget, task, 1, "human")
}

/// The person answered: seal the approval (kind approval, approves = decision commitment), then act.
Method OnHuman(case As pbp.Data.Case, resp As EnsLib.Workflow.TaskResponse) As %Status
{
    If '$ISOBJECT(resp) Quit ..Block("workflow_no_response")
    If resp.%UserName="" Quit ..Block("workflow_authenticated_reviewer_missing")
    Set action = resp.%Action
    If (action'="Approve") && (action'="Reject") Quit ..Block("workflow_action_invalid")
    Set ..Operator = ..SafeId(resp.%UserName)
    Set ..Outcome = $SELECT(action = "Approve": "approved", 1: "rejected")
    Set note = ""
    Try { Set note = resp.%FormValues.GetAt("pbp_note") } Catch ex { Set note = "" }
    Set dec = ##class(pbp.Util).ParseJSON(..DecisionJSON, .r)
    If (..Outcome = "approved") && dec."moves_money" && (..LedgerState '[ "blocked") {
        // The test ledger must have been authorized in the reviewer's own authenticated session (never by this process).
        Set read = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Read(..Commitment), .r)
        Set authorized = $ISOBJECT(read) && read.ok && ((read.state = "authorized") || (read.state = "executed") || (read.state = "confirmed"))
        If 'authorized || (..SafeId(read."approved_by") '= ..Operator) {
            If ..HumanRounds >= ..MaxHumanRounds Quit ..Block("ledger_not_authorized_by_reviewer_after_" _ ..HumanRounds _ "_rounds")
            Do ##class(pbp.Data.Event).Add(..CaseId, "approval_without_ledger_authorization", "task approved by " _ ..Operator _ " but the test ledger is " _ $SELECT($ISOBJECT(read): read.state, 1: "unreadable") _ "; asking again", ..Commitment)
            Quit ..AskHuman(case, dec)
        }
    }
    Set r = {}
    Set r.v = "pbp.seal/1"
    Set r.kind = "approval"
    Set r.at = ##class(pbp.Util).NowISO()
    Set r.case = {}
    Set r.case.id = ..CaseId, r.case.exception = ..ExceptionType, r.case.store = ..StoreId
    Set h = {}
    Set h.operator = ..Operator
    Set h.outcome = ..Outcome
    Set h.approves = ..Commitment
    If note '= "" Set h.note = $EXTRACT(note, 1, 400)
    Do r.%Set("human", h)
    Set r.prev = ..Commitment
    Do case.SetStatus("human_" _ ..Outcome, "by " _ ..Operator, ..Commitment)
    Quit ..SendSeal("approval", r.%ToJSON(), "seal_approval")
}

Method OnSealApproval(case As pbp.Data.Case, resp As pbp.Msg.SealResponse) As %Status
{
    If '$ISOBJECT(resp) || 'resp.Ok Quit ..Block("approval_seal_failed:" _ $SELECT($ISOBJECT(resp): resp.Reason, 1: "no_response"))
    Set ..ApprovalCommitment = resp.Commitment
    If ..Outcome '= "approved" Quit ..Close(case, "rejected", "rejected by " _ ..Operator)
    Set dec = ##class(pbp.Util).ParseJSON(..DecisionJSON, .r)
    If 'dec."moves_money" Quit ..Close(case, "closed", "approved, no money movement: " _ dec.action)
    If ..LedgerState [ "blocked" Quit ..Close(case, "closed_no_effect", "approved as acknowledgement; test ledger refused the effect: " _ ..LedgerState)
    If ..Recipient = "" Quit ..Block("recipient_missing_after_approval")
    Quit ..IssuePermitAndPay(case, ..Operator, ..ApprovalCommitment)
}

/// Issue the single-use permit bound to the sealed decision and ask the ledger for the one effect.
Method IssuePermitAndPay(case As pbp.Data.Case, authorizedBy As %String, approvalCommitment As %String) As %Status
{
    Set seal = ##class(pbp.Data.Seal).Find(..Commitment)
    If '$ISOBJECT(seal) Quit ..Block("sealed_decision_not_found")
    If ..Recipient = "" Quit ..Block("recipient_missing")
    Set permit = ##class(pbp.Data.Permit).Issue(seal, ..Recipient, ..AmountMinor, ..Currency, ..PolicyId, ..PolicyVersion, authorizedBy, approvalCommitment, ..PermitValiditySeconds, .reason)
    If '$ISOBJECT(permit) Quit ..Block("permit_refused:" _ reason)
    Set ..PermitId = permit.PermitId
    Do case.SetStatus("permitted", "permit " _ permit.PermitId _ " by " _ authorizedBy, ..Commitment)
    Set req = ##class(pbp.Msg.LedgerRequest).%New()
    Set req.PermitId = permit.PermitId, req.Commitment = ..Commitment, req.CaseId = ..CaseId
    Set req.Recipient = ..Recipient, req.AmountMinor = ..AmountMinor, req.Currency = ..Currency
    Quit ..SendRequestAsync(..LedgerTarget, req, 1, "ledger")
}

Method OnLedger(case As pbp.Data.Case, resp As pbp.Msg.LedgerResponse) As %Status
{
    If '$ISOBJECT(resp) Quit ..Block("ledger_no_response")
    If resp.Uncertain {
        // Never retry into a second effect: reconcile by reading the ledger (idempotent).
        Do ##class(pbp.Data.Event).Add(..CaseId, "reconcile_started", resp.Reason, ..PermitId)
        Do ##class(pbp.Operation.TestLedger).Reconcile(..PermitId, .rec)
        If rec.Ok {
            Do ##class(pbp.Data.Event).Add(..CaseId, "reconciled", "effect found once in the ledger, no second effect", rec.ReceiptId)
            Do case.SetStatus("effected", ..AmountMinor _ " minor units " _ ..Currency _ " receipt " _ rec.ReceiptId _ " (reconciled)", rec.ReceiptId)
            Quit ..Close(case, "closed", "effect " _ rec.ReceiptId _ " confirmed by reconciliation")
        }
        If rec.Uncertain Quit ..Block("reconcile_required:" _ rec.Reason)
        Quit ..Block("ledger_uncertain_no_effect:" _ rec.Reason)
    }
    If 'resp.Ok Quit ..Block("ledger_refused:" _ resp.Reason)
    If resp.Duplicate Do ##class(pbp.Data.Event).Add(..CaseId, "duplicate_effect_prevented", resp.Reason, resp.ReceiptId)
    Do case.SetStatus("effected", ..AmountMinor _ " minor units " _ ..Currency _ " receipt " _ resp.ReceiptId, resp.ReceiptId)
    Quit ..Close(case, "closed", "effect " _ resp.ReceiptId _ " at " _ resp.EffectAt)
}

Method Close(case As pbp.Data.Case, status As %String, reason As %String) As %Status
{
    If $ISOBJECT(case) Do case.SetStatus(status, reason, ..Commitment)
    Quit $$$OK
}

/// Stop the case with its reason. No effect ever follows a Block.
Method Block(reason As %String) As %Status
{
    Do ##class(pbp.Util).Log("error", "pbp.Process.Decide", "blocked: " _ reason, ..CaseId)
    Set case = ##class(pbp.Data.Case).Find(..CaseId)
    If $ISOBJECT(case) Do case.SetStatus("blocked", reason, ..Commitment)
    Quit $$$OK
}

/// Operator ids must match the pbp.seal/1 id pattern [A-Za-z0-9_\-:.]{1,64}.
ClassMethod SafeId(name As %String) As %String
{
    Set out = ""
    For i = 1:1:$LENGTH(name) {
        Set c = $EXTRACT(name, i)
        Set out = out _ $SELECT($MATCH(c, "[A-Za-z0-9_\-:.]"): c, 1: "_")
    }
    If out = "" Set out = "operator"
    Quit $EXTRACT(out, 1, 64)
}

}
