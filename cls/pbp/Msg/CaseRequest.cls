/// A payment exception entering the production. InputJSON carries the synthetic/pseudonymized case.
Class pbp.Msg.CaseRequest Extends Ens.Request
{

Property CaseId As %String(MAXLEN = 64);

Property StoreId As %String(MAXLEN = 64);

Property ExceptionType As %String(MAXLEN = 64);

Property InputJSON As %String(MAXLEN = "");


}
