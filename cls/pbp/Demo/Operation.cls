/// Separate operation: original scoped LIVE implementation, explicit demo provenance.
Class pbp.Demo.Operation Extends pbp.Operation.Agent
{
XData MessageMap
{
<MapItems>
  <MapItem MessageType="pbp.Msg.DecisionRequest"><Method>Decide</Method></MapItem>
</MapItems>
}

Method Decide(pRequest As pbp.Msg.DecisionRequest, Output pResponse As pbp.Msg.DecisionResponse) As %Status
{
    Set pResponse=##class(pbp.Msg.DecisionResponse).%New()
    Set pResponse.Ok=0,pResponse.Mode="live",pResponse.CostMicroUSD=-1,pResponse.Temperature=-1
    Set pResponse.ModelProvider="google-gemini-private-bridge",pResponse.ModelId=##class(pbp.Demo.Runtime).#MODEL
    Try {
        If '##class(pbp.Demo.Runtime).Allows(pRequest.CaseId) Throw ##class(%Exception.General).%New("public_demo_case_not_armed")
        Do ..Live(pRequest,pResponse)
    } Catch ex {
        Set pResponse.Ok=0,pResponse.Reason="public_demo_agent_failed"
        Do ##class(pbp.Util).LogEx("pbp.Demo.Operation",ex,pRequest.CaseId)
    }
    Do ##class(pbp.ToolsImpl).SetSessionCase("")
    Quit $$$OK
}

ClassMethod RecordedTemperature() As %Numeric
{
    Quit -1
}
}
