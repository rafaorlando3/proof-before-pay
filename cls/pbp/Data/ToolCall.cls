/// Every tool call the agent made for a case: name, arguments and the OUTPUT it saw.
/// The output is what gets sealed; a tool call without its output proves nothing.
Class pbp.Data.ToolCall Extends %Persistent
{

Property CaseId As %String(MAXLEN = 64) [ Required ];

Property Seq As %Integer;

Property Name As %String(MAXLEN = 64);

Property ArgsJSON As %String(MAXLEN = 4000);

Property OutputJSON As %String(MAXLEN = "");

Property DurationMs As %Integer;

Property At As %String(MAXLEN = 32);

Index CaseSeq On (CaseId, Seq) [ Unique ];

}
