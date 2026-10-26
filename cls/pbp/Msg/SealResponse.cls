/// Result of sealing. Ok=0 carries the stable reason code from the Witness (never the offending value).
Class pbp.Msg.SealResponse Extends Ens.Response
{

Property Ok As %Boolean;

Property Reason As %String(MAXLEN = 128);

Property Commitment As %String(MAXLEN = 64);

Property Memo As %String(MAXLEN = 80);

Property State As %String(MAXLEN = 16);

Property SealedAt As %String(MAXLEN = 32);

/// For money decisions: the test ledger state after Stage ("awaiting_approval") or "blocked:<reason>"; empty otherwise.
Property LedgerState As %String(MAXLEN = 128);


}
