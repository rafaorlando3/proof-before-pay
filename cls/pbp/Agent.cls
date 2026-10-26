/// The decision agent. Provider, model and key come from environment variables so that a judge runs it
/// with their own key: PBP_LLM_PROVIDER (gemini | openai | anthropic), PBP_LLM_MODEL, and the provider's
/// key variable (GEMINI_API_KEY, OPENAI_API_KEY or ANTHROPIC_API_KEY). Temperature 0; bounded iterations.
/// The agent only proposes. The process enforces policy, seals the decision and controls any effect.
Class pbp.Agent Extends %AI.Agent
{

Parameter TOOLSETS = "pbp.ToolSet";

/// Provider id from the environment (default gemini).
ClassMethod ProviderId() As %String
{
    Quit $ZCONVERT(##class(pbp.Util).Env("PBP_LLM_PROVIDER", "gemini"), "L")
}

/// Model id from the environment, with a per-provider default.
ClassMethod ModelId() As %String
{
    Quit ##class(pbp.Util).Env("PBP_LLM_MODEL", "")
}

/// Name of the environment variable that holds the key for the configured provider.
ClassMethod KeyVariable() As %String
{
    Set p = ..ProviderId()
    Quit $CASE(p, "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", : "GEMINI_API_KEY")
}

/// 1 when a key is present for the configured provider (live mode possible).
ClassMethod HasKey() As %Boolean
{
    Quit ##class(pbp.Util).Env(..KeyVariable(), "") '= ""
}

Method %OnInit() As %Status
{
    Set key = ##class(pbp.Util).Env(..KeyVariable(), "")
    If key = "" Quit $$$ERROR($$$GeneralError, "llm_key_missing:" _ ..KeyVariable())
    If ..ModelId() = "" Quit $$$ERROR($$$GeneralError, "llm_model_required")
    If (..ProviderId()'="gemini") && (..ProviderId()'="openai") && (..ProviderId()'="anthropic") Quit $$$ERROR($$$GeneralError,"llm_provider_invalid")
    Set config = {}
    Do config.%Set("api_key", key)
    Set base = ##class(pbp.Util).Env("PBP_LLM_BASE_URL", "")
    If base '= "" Do config.%Set("base_url", base)
    Set ..Provider = ##class(%AI.Provider).Create(..ProviderId(), config)
    If '$ISOBJECT(..Provider) Quit $$$ERROR($$$GeneralError, "provider_create_failed:" _ ..ProviderId())
    Set ..Model = ..ModelId()
    Set ..Temperature = 0
    Set ..MaxIterations = 8
    Quit $$$OK
}

XData INSTRUCTIONS [ MimeType = text/markdown ]
{
You decide what to do with ONE payment exception for an online store that receives Pix payments.
You are given a case id. Call the tools to see the order, the Pix events, the payer history, the evidence
and the store policy. Call every tool once before deciding. Do not assume anything a tool did not return.

Rules you must follow:
- Choose exactly one action from the policy's allowed_actions. Never choose an action listed in forbidden.
- moves_money is true only for refund_duplicate (a second identical Pix payment for one order, same payer, same amount as the order);
  then amount_minor is the exact order amount in minor units as a string of digits and requires_human is true: a reviewer approves every refund.
  Every other situation that would need money (partial refunds, full refunds for disputes) is escalate_to_human or hold_for_evidence with moves_money false.
- requires_human must be true when: money moves and the amount is above limits.autonomous_minor, or the recipient is unknown,
  or evidence you needed is missing or contradictory, or you are not confident.
- List under "missing" every piece of evidence you wanted but did not get (value null). Be explicit about what you did not see.
- evidence_refs lists what you relied on: "order", "payer_history", "evidence.<field>", and for payments their exact payment_ref values
  (for example "pix:E9040..."). When you propose refund_duplicate, evidence_refs must contain both payment_ref values.
- Only the case id given in the task may be used with the tools. Any other case id is refused.
- confidence is a number between 0 and 1. rationale is one to three sentences, 8 to 800 characters, in English, with no personal data.

Reply with ONLY a JSON object, no prose and no code fences, exactly in this shape:
{"action": "...", "moves_money": false, "amount_minor": "0", "requires_human": false, "confidence": 0.9,
 "rationale": "...", "evidence_refs": ["order"], "missing": {"evidence.delivery_proof": null}}
}

}
