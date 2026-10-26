/// Ask the agent operation for a decision on a case that the deterministic rules could not close.
Class pbp.Msg.DecisionRequest Extends Ens.Request
{

Property CaseId As %String(MAXLEN = 64);

Property StoreId As %String(MAXLEN = 64);

Property PolicyId As %String(MAXLEN = 64);

Property PolicyVersion As %String(MAXLEN = 32);

/// Rules outcome passed along so the agent sees what the rules already concluded (sealed in "rules").
Property RulesResult As %String(MAXLEN = 256);


}
