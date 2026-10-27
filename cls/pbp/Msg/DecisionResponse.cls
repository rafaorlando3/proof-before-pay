/// Typed decision from the agent operation. Ok=0 means the agent could not produce a valid decision;
/// the process then routes to a human with the reason, never to an effect.
Class pbp.Msg.DecisionResponse Extends Ens.Response
{

Property Ok As %Boolean;

Property Reason As %String(MAXLEN = 256);

Property Action As %String(MAXLEN = 64);

Property MovesMoney As %Boolean;

Property AmountMinor As %String(MAXLEN = 20);

Property RequiresHuman As %Boolean;

Property Confidence As %Numeric(SCALE = 4);

Property Rationale As %String(MAXLEN = 800);

/// JSON array of strings
Property EvidenceRefsJSON As %String(MAXLEN = 1024);

/// JSON object, values null
Property MissingJSON As %String(MAXLEN = 4000);

/// Structurally validated proposal before context/policy changes. Diagnostic only, never authority.
Property ProposalJSON As %String(MAXLEN = "");

/// JSON array of {name,args,output}
Property ToolsJSON As %String(MAXLEN = "");

Property ModelProvider As %String(MAXLEN = 32);

Property ModelId As %String(MAXLEN = 64);

Property Mode As %String(MAXLEN = 16);

Property Temperature As %Numeric(SCALE = 2);

Property PromptTokens As %Integer;

Property CompletionTokens As %Integer;

Property DurationMs As %Integer;

Property CostMicroUSD As %Integer;


}
