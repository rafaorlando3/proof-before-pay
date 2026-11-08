/// Exact-byte export inspection; never a substitute for Witness/approval/permit verification.
Class pbp.PEX.Inspection
{
ClassMethod Inspect(payload As %String, expectedSHA256 As %String, Output response As pbp.PEX.InspectResponse) As %Status
{
    If '$SYSTEM.Security.Check("%Admin_Operate", "U") Quit $$$ERROR($$$GeneralError,"Operator inspection access required")
    Set request=##class(pbp.PEX.InspectRequest).%New()
    Set request.Payload=payload, request.ExpectedSHA256=expectedSHA256
    Set sc=##class(Ens.Director).CreateBusinessService("pbp.PEX.Intake",.service)
    If $$$ISERR(sc) Quit sc
    Quit service.ProcessInput(request,.response)
}
}
