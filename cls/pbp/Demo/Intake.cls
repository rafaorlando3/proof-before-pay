/// Only the fixed nonfinancial public-demo exception types in an enabled profile.
Class pbp.Demo.Intake Extends pbp.Service.Intake
{
Method OnProcessInput(pInput As Ens.StringContainer, Output pOutput As %RegisteredObject) As %Status
{
    Set text=pInput.StringValue
    If ##class(pbp.Util).GuardJSON(text,32000)'="" Quit $$$ERROR($$$GeneralError,"public_demo_input_rejected")
    Set input=##class(pbp.Util).ParseJSON(text,.reason)
    If '$ISOBJECT(input) Quit $$$ERROR($$$GeneralError,"public_demo_input_invalid")
    If '##class(pbp.Demo.Runtime).Allows(input."case_id") Quit $$$ERROR($$$GeneralError,"public_demo_disabled_or_case_invalid")
    If input.environment'="sandbox" Quit $$$ERROR($$$GeneralError,"public_demo_sandbox_required")
    If (input.exception'="amount_mismatch") && (input.exception'="refund_request") Quit $$$ERROR($$$GeneralError,"public_demo_scenario_not_allowed")
    Quit ##super(pInput,.pOutput)
}
}
