/// Helpers behind pbp.Tools. Not a %AI.Tool, so none of this is exposed to the agent.
Class pbp.ToolsImpl Extends %RegisteredObject
{

/// Read one section of the stored case input and record the call with its output.
/// The case the current agent run is allowed to read. Set by the agent operation before the model runs,
/// in a process-private global, so a model-supplied case id can never reach another case.
ClassMethod SessionCase() As %String
{
    Quit $GET(^||pbp("case"))
}

ClassMethod SetSessionCase(caseId As %String)
{
    Set ^||pbp("case") = caseId
}

/// 1 when the requested case id is the session's case (or no session case is set: direct replay/test calls).
ClassMethod Allowed(caseId As %String) As %Boolean
{
    Set sc = ..SessionCase()
    Quit (sc '= "") && (sc = caseId)
}

ClassMethod Serve(caseId As %String, tool As %String, section As %String) As %String
{
    Set t0 = $ZHOROLOG
    If ..SessionCase()="" Quit "{""error"":""case_context_missing""}"
    If '..Allowed(caseId) Quit ..Record(..SessionCase(), tool, {"caseId": "[other case refused]"}, {"error": "case_not_in_session"}, t0)
    Set case = ##class(pbp.Data.Case).Find(caseId)
    If '$ISOBJECT(case) Quit ..Record(caseId, tool, {"caseId": (caseId)}, {"error": "case_not_found"}, t0)
    Set input = case.Input()
    If '$ISOBJECT(input) Quit ..Record(caseId, tool, {"caseId": (caseId)}, {"error": "case_input_invalid"}, t0)
    Set value = input.%Get(section)
    If (input.%GetTypeOf(section) = "unassigned") Quit ..Record(caseId, tool, {"caseId": (caseId)}, {"absent": true, "section": (section)}, t0)
    If '$ISOBJECT(value) Quit ..Record(caseId, tool, {"caseId": (caseId)}, {"section": (section), "value": (value)}, t0)
    Quit ..Record(caseId, tool, {"caseId": (caseId)}, value, t0)
}

/// GetOrder's payload: the stored order section plus the refund destination on record for this case.
/// The destination comes from the normalized input (recipient_ref), never from evidence or messages; null when absent.
/// A COPY is returned; the stored input is never mutated.
ClassMethod ServeOrder(caseId As %String) As %String
{
    Set t0 = $ZHOROLOG
    If ..SessionCase()="" Quit "{""error"":""case_context_missing""}"
    If '..Allowed(caseId) Quit ..Record(..SessionCase(), "GetOrder", {"caseId": "[other case refused]"}, {"error": "case_not_in_session"}, t0)
    Set case = ##class(pbp.Data.Case).Find(caseId)
    If '$ISOBJECT(case) Quit ..Record(caseId, "GetOrder", {"caseId": (caseId)}, {"error": "case_not_found"}, t0)
    Set input = case.Input()
    If '$ISOBJECT(input) Quit ..Record(caseId, "GetOrder", {"caseId": (caseId)}, {"error": "case_input_invalid"}, t0)
    If input.%GetTypeOf("order")'="object" Quit ..Record(caseId, "GetOrder", {"caseId": (caseId)}, {"absent": true, "section": "order"}, t0)
    Set out = ##class(%DynamicObject).%FromJSON(input.order.%ToJSON())
    Set rec = ""
    If input.%GetTypeOf("recipient_ref")="string" Set rec=input."recipient_ref"
    If (rec '= "") && ($EXTRACT(rec, 1, 5) = "test:") {
        Set out."refund_destination" = {"recipient_ref": (rec), "source": "store_record"}
    } Else {
        Do out.%Set("refund_destination", "", "null")
    }
    Quit ..Record(caseId, "GetOrder", {"caseId": (caseId)}, out, t0)
}

/// Persist the call and return the output JSON string to the agent.
ClassMethod Record(caseId As %String, tool As %String, args As %DynamicObject, outputObj As %DynamicAbstractObject, t0 As %Numeric) As %String
{
    Set json = outputObj.%ToJSON()
    Try {
        Set seq = 1
        &sql(SELECT MAX(Seq) INTO :mx FROM pbp_Data.ToolCall WHERE CaseId = :caseId)
        If (SQLCODE = 0) && (mx '= "") Set seq = mx + 1
        Set row = ##class(pbp.Data.ToolCall).%New()
        Set row.CaseId = caseId
        Set row.Seq = seq
        Set row.Name = tool
        Set row.ArgsJSON = args.%ToJSON()
        Set row.OutputJSON = json
        Set row.DurationMs = (($ZHOROLOG - t0) * 1000) \ 1
        Set row.At = ##class(pbp.Util).NowISO()
        Set sc = row.%Save()
        If $$$ISERR(sc) Do ##class(pbp.Util).Log("error", "pbp.Tools.Record", ##class(pbp.Util).StatusText(sc), caseId)
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Tools.Record", ex, caseId)
    }
    Quit json
}

}
