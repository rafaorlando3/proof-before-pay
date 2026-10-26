/// Seal a pbp.seal/1 record for a case. The record JSON is built by the process; the operation only seals and stores.
Class pbp.Msg.SealRequest Extends Ens.Request
{

Property CaseId As %String(MAXLEN = 64);

Property Kind As %String(MAXLEN = 16);

Property RecordJSON As %String(MAXLEN = "");


}
