/// The only way to ask the test ledger for an effect: a single-use permit. The ledger re-checks the permit
/// (status, expiry, exact amount/recipient/currency binding) and uses PermitId as its idempotency key.
Class pbp.Msg.LedgerRequest Extends Ens.Request
{

Property PermitId As %String(MAXLEN = 64);

Property Commitment As %String(MAXLEN = 64);

Property CaseId As %String(MAXLEN = 64);

Property Recipient As %String(MAXLEN = 64);

Property AmountMinor As %String(MAXLEN = 20);

Property Currency As %String(MAXLEN = 3);


}
