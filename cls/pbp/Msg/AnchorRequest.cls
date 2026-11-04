/// Only the commitment of an already intact local seal; no raw record, salt or payment data.
Class pbp.Msg.AnchorRequest Extends Ens.Request
{
Property Commitment As %String(MAXLEN = 64) [ Required ];
}
