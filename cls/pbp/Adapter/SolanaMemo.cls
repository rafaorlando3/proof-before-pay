/// Optional outbound adapter. Fixed Solana devnet, Memo only, no transfer or automatic resend.
Class pbp.Adapter.SolanaMemo Extends Ens.OutboundAdapter
{
Parameter SETTINGS = "Enabled,DevnetKeypairFile,StateDirectory";
Property Enabled As %Boolean [ InitialExpression = 0 ];
Property DevnetKeypairFile As %String(MAXLEN = 1024);
Property StateDirectory As %String(MAXLEN = 1024);

Method SendMemo(commitment As %String) As %String
{
    If '..Enabled Quit "{""ok"":false,""state"":""disabled"",""cluster"":""devnet"",""reason"":""devnet_adapter_not_configured""}"
    If (..DevnetKeypairFile="") || (..StateDirectory="") Quit "{""ok"":false,""state"":""disabled"",""cluster"":""devnet"",""reason"":""devnet_adapter_not_configured""}"
    Try {
        Set module=##class(%SYS.Python).Import("pbp_solana_demo.adapter")
        Set result=module."anchor_json"(commitment,..DevnetKeypairFile,..StateDirectory,..Enabled)
    } Catch ex { Set result="{""ok"":false,""state"":""unavailable"",""cluster"":""devnet"",""reason"":""optional_devnet_bridge_unavailable""}" }
    Quit result
}
}
