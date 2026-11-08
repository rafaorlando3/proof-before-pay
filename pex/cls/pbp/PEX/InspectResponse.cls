/// Transport integrity only: this never authorizes a payment or verifies a decision seal.
Class pbp.PEX.InspectResponse Extends Ens.Response
{
Property Status As %String;
Property SHA256 As %String(MAXLEN = 64);
Property ByteCount As %Integer;
Property InspectionOnly As %Boolean [ InitialExpression = 1 ];
}
