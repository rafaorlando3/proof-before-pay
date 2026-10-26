/// Native AI Hub audit policy: every tool execution and every denial is written to pbp.Data.Log with the
/// session case, tool name, duration and status code. Tool OUTPUTS are recorded by the tools themselves
/// (pbp.Data.ToolCall) because they are part of the sealed record.
Class pbp.AuditPolicy Extends %AI.Policy.Audit
{

Method %LogExecution(call As %DynamicObject, metadata As %DynamicObject, result As %DynamicObject, duration As %Integer, status As %Status) As %Status
{
    Set name = ..NameOf(call)
    Quit ##class(pbp.Util).Log("info", "pbp.AuditPolicy", "tool " _ name _ " executed in " _ (+duration) _ " ms, status " _ $SELECT($$$ISOK(status): "ok", 1: "error"), ##class(pbp.ToolsImpl).SessionCase())
}

Method %LogDenial(call As %DynamicObject, metadata As %DynamicObject, status As %Status) As %Status
{
    Set name = ..NameOf(call)
    Quit ##class(pbp.Util).Log("warn", "pbp.AuditPolicy", "tool " _ name _ " DENIED: " _ ##class(pbp.Util).Sanitize($SYSTEM.Status.GetErrorText(status)), ##class(pbp.ToolsImpl).SessionCase())
}

ClassMethod NameOf(call As %DynamicObject) As %String
{
    Set n = ""
    Try {
        If $ISOBJECT(call) {
            Set n = call.name
            If (n = "") && $ISOBJECT(call.function) Set n = call.function.name
            If n = "" Set n = call.tool
        }
    } Catch ex {
        Set n = ""
    }
    Quit $SELECT(n = "": "?", 1: n)
}

}
