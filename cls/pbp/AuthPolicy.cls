/// Native AI Hub authorization policy: a tool call is allowed only for the case id of the current agent run
/// (set by the agent operation in a process-private global). A model-supplied case id for another case is denied.
/// The tools enforce the same rule themselves (defence in depth); this policy makes the denial visible to the AI Hub.
Class pbp.AuthPolicy Extends %AI.Policy.Authorization
{

Method %CanExecute(toolref As %String, call As %DynamicObject, metadata As %DynamicObject) As %Status
{
    Set sessionCase = ##class(pbp.ToolsImpl).SessionCase()
    If sessionCase = "" Quit $$$ERROR($$$GeneralError, "case_context_missing")
    Set asked = ..CaseIdOf(call)
    If asked '= sessionCase {
        Do ##class(pbp.Util).Log("warn", "pbp.AuthPolicy", "tool " _ toolref _ " denied: case id outside the session", sessionCase)
        Quit $$$ERROR($$$GeneralError, "case_not_in_session")
    }
    Quit $$$OK
}

Method %CanList(toolref As %String, metadata As %DynamicObject) As %Boolean
{
    Quit 1
}

/// The call object shape may differ across EAP builds; look for caseId under the usual argument containers.
ClassMethod CaseIdOf(call As %DynamicObject) As %String
{
    Set v = ""
    Try {
        If $ISOBJECT(call) {
            For key = "arguments", "args", "input", "parameters" {
                Set c = call.%Get(key)
                If $ISOBJECT(c) && (c.caseId '= "") { Set v = c.caseId Quit }
            }
            If (v = "") && (call.caseId '= "") Set v = call.caseId
        }
    } Catch ex {
        Set v = ""
    }
    Quit v
}

}
