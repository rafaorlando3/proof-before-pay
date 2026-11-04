/// Optional, operator-configured Production module. Not installed as a running host by default.
Class pbp.Operation.SolanaMemo Extends Ens.BusinessOperation
{
Parameter ADAPTER = "pbp.Adapter.SolanaMemo";
Parameter INVOCATION = "Queue";
XData MessageMap
{
<MapItems><MapItem MessageType="pbp.Msg.AnchorRequest"><Method>Anchor</Method></MapItem></MapItems>
}

Method Anchor(pRequest As pbp.Msg.AnchorRequest, Output pResponse As Ens.StringContainer) As %Status
{
    Set pResponse=##class(Ens.StringContainer).%New()
    Set pResponse.StringValue="{""ok"":false,""state"":""unavailable"",""reason"":""intact_local_seal_required""}"
    Set seal=##class(pbp.Data.Seal).Find(pRequest.Commitment)
    If '$ISOBJECT(seal) Quit $$$OK
    Set verification=seal.Verify()
    If 'verification.ok Quit $$$OK
    Set pResponse.StringValue=..Adapter.SendMemo(pRequest.Commitment)
    // The private adapter journal retains the verified RPC readback. Local
    // verification remains local; this optional operation does not approve money.
    Quit $$$OK
}
}
