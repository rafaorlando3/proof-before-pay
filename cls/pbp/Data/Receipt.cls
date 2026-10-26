/// Effect receipt from the test ledger. PermitId is unique: a permit can be consumed exactly once,
/// so a duplicate or replayed ledger request can never create a second effect.
Class pbp.Data.Receipt Extends %Persistent
{

Property ReceiptId As %String(MAXLEN = 64) [ Required ];

Property PermitId As %String(MAXLEN = 64) [ Required ];

Property CaseId As %String(MAXLEN = 64) [ Required ];

Property Commitment As %String(MAXLEN = 64);

Property AmountMinor As %String(MAXLEN = 20);

Property Currency As %String(MAXLEN = 3);

Property Recipient As %String(MAXLEN = 64);

/// effected, failed
Property Status As %String(MAXLEN = 16);

Property Reason As %String(MAXLEN = 256);

Property LedgerRef As %String(MAXLEN = 128);

Property EffectAt As %String(MAXLEN = 32);

/// Ledger sequence number of the effect (monotonic; ordering proof independent of clocks).
Property EffectSeq As %Integer;

Index ReceiptIdx On ReceiptId [ Unique ];

Index PermitIdx On PermitId [ Unique ];

Index CaseIdx On CaseId;

/// Compare every field in the readable projection with the authoritative receipt.
Method Matches(receipt As %DynamicObject) As %Boolean
{
    If '$ISOBJECT(receipt) Quit 0
    Quit (..ReceiptId=receipt."receipt_id") && (..Commitment=receipt.commitment) && (..CaseId=receipt."case_id") && (..AmountMinor=receipt."amount_minor") && (..Currency=receipt.currency) && (..Recipient=receipt."recipient_ref") && (..EffectAt=receipt."executed_at") && (..EffectSeq=receipt."executed_seq") && (..Status="effected") && (..LedgerRef=("sandbox:"_receipt."receipt_id"))
}

}
