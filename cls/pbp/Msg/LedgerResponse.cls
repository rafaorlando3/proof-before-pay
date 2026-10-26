/// Ledger outcome. Duplicate=1 means the permit had already been consumed: the receipt returned is the
/// original one and no second effect happened. Uncertain=1 means the ledger could not confirm either way;
/// the process then stops and asks for reconciliation, never a new effect.
Class pbp.Msg.LedgerResponse Extends Ens.Response
{

Property Ok As %Boolean;

Property Reason As %String(MAXLEN = 256);

Property ReceiptId As %String(MAXLEN = 64);

Property LedgerRef As %String(MAXLEN = 128);

Property EffectAt As %String(MAXLEN = 32);

Property Duplicate As %Boolean [ InitialExpression = 0 ];

Property Uncertain As %Boolean [ InitialExpression = 0 ];


}
