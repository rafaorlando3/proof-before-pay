/// Select a synthetic refund payment from normalized inputs, never from model prose.
/// Two distinct references and matching amounts/payer are required. An explicit observed
/// target is preserved; otherwise timestamps must identify one strictly later payment.
/// Missing recipient is still sealed as missing and refused independently by the Ledger.
Class pbp.RefundTarget Extends %RegisteredObject
{
Parameter VERSION = "1";
ClassMethod Derive(input As %DynamicObject, Output reason As %String) As %String
{
    Set reason="refund_target_unavailable",target=""
    Try {
        Set helper=##class(%SYS.Python).Import("pbp_refund_target.derive")
        Set result=##class(%DynamicObject).%FromJSON(helper."derive_json"(input.%ToJSON()))
        Set reason=result.reason
        If result.%GetTypeOf("payment_ref")="string" Set target=result."payment_ref"
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.RefundTarget.Derive",ex)
    }
    Quit target
}
}
