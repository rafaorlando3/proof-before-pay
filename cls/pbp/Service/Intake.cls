/// Entry point of the production. Adapterless: the REST API and the demo feeder call it in process
/// with ##class(Ens.Director).CreateBusinessService("pbp.Service.Intake", .svc) and svc.ProcessInput(json).
/// Validates the envelope, assigns a case id when absent and forwards a pbp.Msg.CaseRequest to the process.
Class pbp.Service.Intake Extends Ens.BusinessService
{

Parameter ADAPTER;

Property TargetConfigName As Ens.DataType.ConfigName [ InitialExpression = "pbp.Process.Decide" ];

Parameter SETTINGS = "TargetConfigName:Basic";

/// pInput: Ens.StringContainer with the JSON text of one case. pOutput: the CaseRequest sent.
/// The JSON is guarded (size, strict parse with duplicate keys refused, personal-data scan) BEFORE anything is stored.
Method OnProcessInput(pInput As Ens.StringContainer, Output pOutput As %RegisteredObject) As %Status
{
    Set pOutput = ""
    Set text = pInput.StringValue
    Set bad = ##class(pbp.Util).GuardJSON(text, 60000)
    If bad '= "" Quit $$$ERROR($$$GeneralError, "case_rejected:" _ bad)
    Set input = ##class(pbp.Util).ParseJSON(text, .reason)
    If input = "" Quit $$$ERROR($$$GeneralError, "case_invalid_json")
    If input.exception = "" Quit $$$ERROR($$$GeneralError, "case_exception_missing")
    If input."case_id" = "" Set input."case_id" = "pbp-" _ ##class(pbp.Util).RandomHex(6)
    If '$MATCH(input."case_id", "[A-Za-z0-9_\-:.]{1,64}") Quit $$$ERROR($$$GeneralError, "case_id_invalid")
    Set req = ##class(pbp.Msg.CaseRequest).%New()
    Set req.CaseId = input."case_id"
    Set req.StoreId = $SELECT(input.store = "": "store-default", 1: input.store)
    Set req.ExceptionType = input.exception
    Set req.InputJSON = input.%ToJSON()
    Set pOutput = req
    Quit ..SendRequestAsync(..TargetConfigName, req)
}

}
