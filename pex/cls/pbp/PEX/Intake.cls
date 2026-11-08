/// Adapterless, operator-only entry to the optional export-inspection production.
Class pbp.PEX.Intake Extends Ens.BusinessService
{
Method OnProcessInput(pInput As pbp.PEX.InspectRequest, Output pOutput As pbp.PEX.InspectResponse) As %Status
{
    Quit ..SendRequestSync("pbp.PEX.ExportDigest", pInput, .pOutput, 10)
}
}
