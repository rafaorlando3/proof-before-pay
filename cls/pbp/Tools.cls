/// Tools the AI Hub agent may call. Every tool takes the case id, reads only stored synthetic case data,
/// and records its own OUTPUT in pbp.Data.ToolCall so that what the agent saw is sealed, not only
/// the fact that it asked. Tools never change data and never move money.
Class pbp.Tools Extends %AI.Tool
{

Parameter REQUIRESAUTH = 1;

Property Name As %String [ InitialExpression = "pbp.Tools" ];

Property Description As %String(MAXLEN = "") [ InitialExpression = "Read-only access to one payment exception case: order, Pix events, payer history, evidence and the store policy in force." ];

/// The order the exception refers to: amount (minor units), currency, status, timestamps, shipping state.
ClassMethod GetOrder(caseId As %String(DESCRIPTION = "The case id exactly as given in the task")) As %String
{
    Quit ##class(pbp.ToolsImpl).Serve(caseId, "GetOrder", "order")
}

/// Pix events received for the order: amount, payer pseudonym, received_at, end-to-end id.
ClassMethod GetPixEvents(caseId As %String(DESCRIPTION = "The case id exactly as given in the task")) As %String
{
    Quit ##class(pbp.ToolsImpl).Serve(caseId, "GetPixEvents", "payments")
}

/// Pseudonymous payer history: orders, disputes and chargebacks in the last 90 days. Absent when unknown.
ClassMethod GetPayerHistory(caseId As %String(DESCRIPTION = "The case id exactly as given in the task")) As %String
{
    Quit ##class(pbp.ToolsImpl).Serve(caseId, "GetPayerHistory", "payer_history")
}

/// Evidence attached to the case (delivery proof, customer message, refund request). Null means not available.
ClassMethod GetEvidence(caseId As %String(DESCRIPTION = "The case id exactly as given in the task")) As %String
{
    Quit ##class(pbp.ToolsImpl).Serve(caseId, "GetEvidence", "evidence")
}

/// The store policy in force for this case: allowed actions, forbidden actions, autonomous limit, thresholds.
ClassMethod GetStorePolicy(caseId As %String(DESCRIPTION = "The case id exactly as given in the task")) As %String
{
    Set t0 = $ZHOROLOG
    If ##class(pbp.ToolsImpl).SessionCase()="" Quit "{""error"":""case_context_missing""}"
    If '##class(pbp.ToolsImpl).Allowed(caseId) Quit ##class(pbp.ToolsImpl).Record(##class(pbp.ToolsImpl).SessionCase(), "GetStorePolicy", {"caseId": "[other case refused]"}, {"error": "case_not_in_session"}, t0)
    Set case = ##class(pbp.Data.Case).Find(caseId)
    If '$ISOBJECT(case) Quit ##class(pbp.ToolsImpl).Record(caseId, "GetStorePolicy", {"caseId": (caseId)}, {"error": "case_not_found"}, t0)
    Set pol = ##class(pbp.Data.Policy).ActiveFor(case.StoreId)
    If '$ISOBJECT(pol) Quit ##class(pbp.ToolsImpl).Record(caseId, "GetStorePolicy", {"caseId": (caseId)}, {"error": "policy_not_found"}, t0)
    Set obj = pol.Object()
    Set out = {}
    Set out.id = pol.PolicyId
    Set out.version = pol.Version
    Set out.sha256 = pol.Sha256
    Set out.limits = obj.limits
    Set out.forbidden = obj.forbidden
    Set out."allowed_actions" = obj."allowed_actions"
    Set out.rules = obj.rules
    Quit ##class(pbp.ToolsImpl).Record(caseId, "GetStorePolicy", {"caseId": (caseId)}, out, t0)
}

}
