/// LIVE AI Hub agent through the native Interoperability adapter (EnsLib.AI.Agent.OutboundAdapter).
/// The adapter instantiates pbp.Agent (provider, model and key from the environment), attaches the
/// pbp.AuthPolicy / pbp.AuditPolicy policies and runs the chat; tool outputs are read back from
/// pbp.Data.ToolCall; tokens, time and estimated cost are measured per decision.
/// Enabled by pbp.Setup only when a provider key is present; otherwise pbp.Operation.Replay answers.
/// Invalid model output fails closed (Ok=0) and the process sends the case to a person.
Class pbp.Operation.Agent Extends Ens.BusinessOperation
{

Parameter ADAPTER = "EnsLib.AI.Agent.OutboundAdapter";

Property Adapter As EnsLib.AI.Agent.OutboundAdapter;

Parameter INVOCATION = "Queue";

/// Default price table, USD per million tokens (checked 26/10/2026 on the providers' pricing pages).
Parameter PRICES = "{""gemini-3.8-flash"":{""in"":0.75,""out"":3.75},""gemini-3.5-flash-lite"":{""in"":0.30,""out"":2.50},""gpt-5.4-mini"":{""in"":0.75,""out"":4.50},""claude-haiku-4-5"":{""in"":1.00,""out"":5.00}}";

/// JSON price table, USD per million tokens: {"model":{"in":0.75,"out":3.75}}
Property PriceTableJSON As %String(MAXLEN = 4000) [ InitialExpression = {..#PRICES} ];

Parameter SETTINGS = "PriceTableJSON:Basic";

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
    Set pResponse.Ok = 0
    Set pResponse.Mode = "live"
    Set pResponse.CostMicroUSD = -1
    Set pResponse.Temperature = 0
    Set pResponse.ModelProvider = ##class(pbp.Agent).ProviderId()
    Set pResponse.ModelId = ##class(pbp.Agent).ModelId()
    Set caseId = pRequest.CaseId
    Try {
        Do ..Live(pRequest, pResponse)
    } Catch ex {
        Set pResponse.Ok = 0
        Set pResponse.Reason = "agent_exception"
        Do ##class(pbp.Util).LogEx("pbp.Operation.Agent", ex, caseId)
    }
    Do ##class(pbp.ToolsImpl).SetSessionCase("")
    If pResponse.ModelId'="" {
        Set ^pbp.live(pResponse.ModelProvider,pResponse.ModelId,"last_attempt_at")=##class(pbp.Util).NowISO()
        Set ^pbp.live(pResponse.ModelProvider,pResponse.ModelId,"last_attempt_ok")=pResponse.Ok
    }
    If 'pResponse.Ok Do ##class(pbp.Util).Log("warn", "pbp.Operation.Agent", "decision not produced: " _ pResponse.Reason, caseId)
    Quit $$$OK
}

Method Live(pRequest As pbp.Msg.DecisionRequest, pResponse As pbp.Msg.DecisionResponse)
{
    Set caseId = pRequest.CaseId
    If '$ISOBJECT(..Adapter) || '$ISOBJECT(..Adapter.Agent) {
        Set pResponse.Reason = "agent_adapter_not_initialized"
        Do ##class(pbp.Util).Log("error", "pbp.Operation.Agent.Live", "adapter or agent missing (key variable " _ ##class(pbp.Agent).KeyVariable() _ " set? " _ ##class(pbp.Agent).HasKey() _ ")", caseId)
        Quit
    }
    Do ##class(pbp.ToolsImpl).SetSessionCase(caseId)
    Set startSeq = ##class(pbp.Operation.Replay).LastToolSeq(caseId)
    Set t0 = $ZHOROLOG
    Set session = ..Adapter.Agent.CreateSession()
    Set prompt = "Case id: " _ caseId _ ". Exception type: " _ ..ExceptionOf(caseId) _ ". Rules engine result: " _ pRequest.RulesResult _ ". Fetch everything with the tools (this case id only), then answer with the JSON object only."
    Set sc = ..Adapter.SendChat(prompt, .llm, session)
    If $$$ISERR(sc) {
        Set pResponse.Reason = "llm_call_failed"
        Do ##class(pbp.Util).Log("error", "pbp.Operation.Agent.Live", "SendChat: " _ ##class(pbp.Util).Sanitize(##class(pbp.Util).StatusText(sc)), caseId)
        Set pResponse.DurationMs = (($ZHOROLOG - t0) * 1000) \ 1
        Quit
    }
    Set text = ..ReplyText(llm)
    Set decision = ##class(pbp.Operation.Replay).ParseDecision(text, .reason)
    If decision = "" {
        Do ##class(pbp.Util).Log("warn", "pbp.Operation.Agent.Live", "first reply invalid (" _ reason _ "), retrying once", caseId)
        Set sc = ..Adapter.SendChat("Your previous answer was not a valid decision (" _ reason _ "). Reply with ONLY the JSON object in the required shape, no prose.", .llm, session)
        Set text = $SELECT($$$ISOK(sc): ..ReplyText(llm), 1: "")
        Set decision = ##class(pbp.Operation.Replay).ParseDecision(text, .reason)
    }
    Set pResponse.DurationMs = (($ZHOROLOG - t0) * 1000) \ 1
    Do ..Usage(session, llm, pResponse)
    Set pResponse.ToolsJSON = ##class(pbp.Operation.Replay).ToolsSince(caseId, startSeq).%ToJSON()
    If decision = "" {
        Set pResponse.Reason = "model_output_invalid:" _ reason
        Quit
    }
    Set tools=##class(pbp.Util).ParseJSON(pResponse.ToolsJSON,.r)
    Set names={},n=0
    For i=0:1:tools.%Size()-1 {
        Set t=tools.%Get(i)
        Do names.%Set(t.name,1)
    }
    For name="GetOrder","GetPixEvents","GetPayerHistory","GetEvidence","GetStorePolicy" {
        If 'names.%IsDefined(name) { Set pResponse.Reason="required_tool_not_observed:"_name Quit }
        Set n=n+1
    }
    If n'=5 Quit
    Do ##class(pbp.Operation.Replay).Fill(pResponse, decision)
    Do ##class(pbp.Operation.Replay).ValidateContext(pResponse)
    If pResponse.Ok Set ^pbp.live(pResponse.ModelProvider,pResponse.ModelId,"last_ok")=##class(pbp.Util).NowISO()
}

/// Text of an agent reply (%AI.LLM.Response.Content on build 154).
ClassMethod ReplyText(reply) As %String
{
    Set text = ""
    If '$ISOBJECT(reply) Quit $GET(reply)
    Try { Set text = reply.Content } Catch ex { Set text = "" }
    Quit text
}

Method ExceptionOf(caseId As %String) As %String
{
    Set c = ##class(pbp.Data.Case).Find(caseId)
    Quit $SELECT($ISOBJECT(c): c.ExceptionType, 1: "unknown")
}

/// Token usage from the response (Usage) or the session statistics, and estimated cost from the price table.
Method Usage(session, llm, pResponse As pbp.Msg.DecisionResponse)
{
    Set pResponse.PromptTokens = 0, pResponse.CompletionTokens = 0, pResponse.CostMicroUSD = -1
    Try {
        Set stats = session.GetStats()
        If $ISOBJECT(stats) {
            Set pResponse.PromptTokens = +stats."total_prompt_tokens"
            Set pResponse.CompletionTokens = +stats."total_completion_tokens"
            If +stats."total_llm_duration_ms" > 0 Set pResponse.DurationMs = +stats."total_llm_duration_ms"
        }
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Operation.Agent.Usage.GetStats", ex)
    }
    Try {
        If (pResponse.PromptTokens = 0) && $ISOBJECT(llm) && $ISOBJECT(llm.Usage) {
            Set u = llm.Usage
            Set pResponse.PromptTokens = +$SELECT(u."prompt_tokens" '= "": u."prompt_tokens", u."input_tokens" '= "": u."input_tokens", 1: u."promptTokenCount")
            Set pResponse.CompletionTokens = +$SELECT(u."completion_tokens" '= "": u."completion_tokens", u."output_tokens" '= "": u."output_tokens", 1: u."candidatesTokenCount")
        }
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Operation.Agent.Usage.Response", ex)
    }
    Try {
        Set table = ##class(pbp.Util).ParseJSON(..PriceTableJSON, .r)
        Set price = $SELECT($ISOBJECT(table): table.%Get(pResponse.ModelId), 1: "")
        If $ISOBJECT(price) && ((pResponse.PromptTokens+pResponse.CompletionTokens)>0) {
            // USD per million tokens times tokens = micro-USD.
            Set pResponse.CostMicroUSD = ((pResponse.PromptTokens * price.in) + (pResponse.CompletionTokens * price.out)) \ 1
        }
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Operation.Agent.Usage.Price", ex)
    }
}

}
