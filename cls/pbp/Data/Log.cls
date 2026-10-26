/// Diagnostic log. Reasons are kept here so that no failure is silent, while public replies stay generic.
Class pbp.Data.Log Extends %Persistent
{

Property At As %String(MAXLEN = 32);

Property Level As %String(MAXLEN = 8);

Property Where As %String(MAXLEN = 128);

Property Message As %String(MAXLEN = 4000);

Property CaseId As %String(MAXLEN = 64);

Index AtIdx On At;

Index CaseIdx On CaseId;

}
