/// Timeline of a case (status changes, seals, permits, effects). Read by the review UI.
Class pbp.Data.Event Extends %Persistent
{

Property CaseId As %String(MAXLEN = 64) [ Required ];

Property At As %String(MAXLEN = 32);

Property Kind As %String(MAXLEN = 32);

Property Detail As %String(MAXLEN = 1024);

/// A commitment, permit id, receipt id or message header id related to the event.
Property Ref As %String(MAXLEN = 128);

Index CaseAt On (CaseId, At);

ClassMethod Add(caseId As %String, kind As %String, detail As %String = "", ref As %String = "") As %Status
{
    Set e = ..%New()
    Set e.CaseId = caseId
    Set e.At = ##class(pbp.Util).NowISO()
    Set e.Kind = kind
    Set e.Detail = $EXTRACT(detail, 1, 1024)
    Set e.Ref = ref
    Quit e.%Save()
}

}
