/// The decision as produced (by rules or by the AI Hub agent), with model usage and cost.
/// The sealed record is the source of truth; this table is the readable projection for the UI and the article.
Class pbp.Data.Decision Extends %Persistent
{

Property CaseId As %String(MAXLEN = 64) [ Required ];

/// rules | model
Property Source As %String(MAXLEN = 8);

Property Action As %String(MAXLEN = 64);

Property MovesMoney As %Boolean;

Property AmountMinor As %String(MAXLEN = 20);

Property RequiresHuman As %Boolean;

Property Confidence As %Numeric(SCALE = 4);

Property Rationale As %String(MAXLEN = 800);

Property EvidenceRefs As %String(MAXLEN = 1024);

/// JSON object of evidence the agent did NOT have (values null), sealed as "missing".
Property MissingJSON As %String(MAXLEN = 4000);

Property ModelProvider As %String(MAXLEN = 32);

Property ModelId As %String(MAXLEN = 64);

/// live | recorded | none
Property Mode As %String(MAXLEN = 16);

Property PromptTokens As %Integer;

Property CompletionTokens As %Integer;

Property DurationMs As %Integer;

/// Estimated cost in micro-USD (1e-6 USD) from the configured price table; 0 in recorded mode.
Property CostMicroUSD As %Integer;

Property ToolCalls As %Integer;

Property Commitment As %String(MAXLEN = 64);

Property CreatedAt As %String(MAXLEN = 32);

Index CaseIdx On CaseId;

Index CommitIdx On Commitment;

}
