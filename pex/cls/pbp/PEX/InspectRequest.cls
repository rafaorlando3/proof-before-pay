/// Public synthetic export bytes and a separately retained expected digest.
Class pbp.PEX.InspectRequest Extends Ens.Request
{
Property Payload As %String(MAXLEN = 65536);
Property ExpectedSHA256 As %String(MAXLEN = 64);
}
