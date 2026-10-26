/// A payment exception case: what arrived, where it stands, and the chain of sealed records.
/// Inputs are synthetic or pseudonymized; the case never stores personal data.
Class pbp.Data.Case Extends %Persistent
{

Property CaseId As %String(MAXLEN = 64) [ Required ];

Property StoreId As %String(MAXLEN = 64);

Property ExceptionType As %String(MAXLEN = 64);

/// received, rules_decided, agent_decided, sealed, awaiting_human, permitted, effected, closed, rejected, blocked
Property Status As %String(MAXLEN = 32) [ InitialExpression = "received" ];

Property StatusReason As %String(MAXLEN = 512);

Property InputJSON As %String(MAXLEN = "");

Property CreatedAt As %String(MAXLEN = 32);

Property UpdatedAt As %String(MAXLEN = 32);

/// Commitment of the latest sealed record for this case (head of the chain).
Property HeadCommitment As %String(MAXLEN = 64);

/// Ensemble session id of the production message trace, for the time machine view.
Property SessionId As %String(MAXLEN = 32);

Property PolicyId As %String(MAXLEN = 64);

Property PolicyVersion As %String(MAXLEN = 32);

Index CaseIdx On CaseId [ Unique ];

Index StatusIdx On Status;

ClassMethod Find(caseId As %String) As pbp.Data.Case
{
    Quit ..CaseIdxOpen(caseId)
}

/// Set status with a reason and timestamp; also appends an event line.
Method SetStatus(status As %String, reason As %String = "", ref As %String = "") As %Status
{
    Set ..Status = status
    Set ..StatusReason = $EXTRACT(reason, 1, 512)
    Set ..UpdatedAt = ##class(pbp.Util).NowISO()
    Set sc = ..%Save()
    If $$$ISOK(sc) Do ##class(pbp.Data.Event).Add(..CaseId, status, reason, ref)
    Quit sc
}

/// Parsed inputs.
Method Input() As %DynamicObject
{
    Quit ##class(pbp.Util).ParseJSON(..InputJSON, .r)
}

}
