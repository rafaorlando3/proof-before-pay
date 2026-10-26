/// The agent operation's output contract: invalid model output fails closed; valid JSON is normalized.
Class pbp.Test.Agent Extends %UnitTest.TestCase
{

Method TestParseValid()
{
    Set d = ##class(pbp.Operation.Replay).ParseDecision("Here you go:" _ $CHAR(10) _ "```json" _ $CHAR(10) _ "{""action"":""escalate_to_human"",""moves_money"":false,""requires_human"":true,""confidence"":0.9,""rationale"":""Evidence contradicts the customer; a person decides."",""evidence_refs"":[""order""],""missing"":{""evidence.carrier_signature"":null}}" _ $CHAR(10) _ "```", .reason)
    Do $$$AssertTrue($ISOBJECT(d), "fenced JSON accepted: " _ reason)
    Do $$$AssertEquals(d.missing.%GetTypeOf("evidence.carrier_signature"), "null", "null missing value kept")
    // Contract: a non-null value under "missing" is a model error, refused (never silently turned into null).
    Set d = ##class(pbp.Operation.Replay).ParseDecision("{""action"":""escalate_to_human"",""moves_money"":false,""requires_human"":true,""confidence"":0.9,""rationale"":""Evidence contradicts the customer; a person decides."",""evidence_refs"":[""order""],""missing"":{""x"":""anything""}}", .reason)
    Do $$$AssertTrue('$ISOBJECT(d) && (reason = "missing_value_must_be_null"), "non-null missing value refused: " _ reason)
}

Method TestParseInvalid()
{
    Do ##class(pbp.Operation.Replay).ParseDecision("I cannot decide.", .reason)
    Do $$$AssertEquals(reason, "no_json_object", "prose refused")
    Do ##class(pbp.Operation.Replay).ParseDecision("{""action"":""refund_full"",""moves_money"":true,""requires_human"":false,""confidence"":0.9,""rationale"":""long enough rationale"",""evidence_refs"":[""order""]}", .reason)
    Do $$$AssertEquals(reason, "amount_minor_invalid", "money without amount refused")
    Do ##class(pbp.Operation.Replay).ParseDecision("{""action"":""accept_order"",""moves_money"":""no"",""requires_human"":false,""confidence"":0.9,""rationale"":""long enough rationale"",""evidence_refs"":[""order""]}", .reason)
    Do $$$AssertEquals(reason, "moves_money_not_boolean", "string boolean refused")
    Do ##class(pbp.Operation.Replay).ParseDecision("{""action"":""accept_order"",""moves_money"":false,""requires_human"":false,""confidence"":1.5,""rationale"":""long enough rationale"",""evidence_refs"":[""order""]}", .reason)
    Do $$$AssertEquals(reason, "confidence_out_of_range", "confidence > 1 refused")
    Do ##class(pbp.Operation.Replay).ParseDecision("{""action"":""accept_order"",""moves_money"":false,""requires_human"":false,""confidence"":0.5,""rationale"":""short"",""evidence_refs"":[""order""]}", .reason)
    Do $$$AssertEquals(reason, "rationale_length", "short rationale refused")
    Do ##class(pbp.Operation.Replay).ParseDecision("{""action"":""accept_order"",""moves_money"":false,""requires_human"":false,""confidence"":0.5,""rationale"":""long enough rationale"",""evidence_refs"":[]}", .reason)
    Do $$$AssertEquals(reason, "evidence_refs_missing", "empty evidence refused")
}

Method TestRecordedModeWithoutKey()
{
    // A recorded decision must exist for the fixture case and produce Ok=1 with mode=recorded, even with no key.
    If $GET(^pbp.replay("pix-0005")) = "" { Do $$$AssertSkipped("replay fixtures not loaded") Quit }
    Set cid="unit-replay-" _ ##class(pbp.Util).RandomHex(4)
    Set ^pbp.replay(cid)=^pbp.replay("pix-0005")
    Set case = ##class(pbp.Data.Case).Find(cid)
    If '$ISOBJECT(case) {
        Set case = ##class(pbp.Data.Case).%New()
        Set case.CaseId = cid, case.StoreId = "store-default", case.ExceptionType = "amount_mismatch"
        Set case.InputJSON = "{""case_id"":""pix-0005"",""exception"":""amount_mismatch"",""order"":{""amount_minor"":""8900""},""payments"":[{""payment_ref"":""pix:X"",""amount_minor"":""12900"",""payer"":""test:p""}],""evidence"":{}}"
        Do case.%Save()
    }
    Set req = ##class(pbp.Msg.DecisionRequest).%New()
    Set req.CaseId = cid, req.RulesResult = "no_match"
    Set resp = ##class(pbp.Msg.DecisionResponse).%New()
    Set resp.Ok = 0, resp.Temperature = 0
    Do ##class(pbp.Operation.Replay).RunRecorded(req, resp)
    Do $$$AssertTrue(resp.Ok, "recorded decision ok: " _ resp.Reason)
    Do $$$AssertEquals(resp.Mode, "recorded", "labelled recorded")
    Do $$$AssertEquals(resp.Action, "escalate_to_human", "recorded action")
    Set tools = ##class(pbp.Util).ParseJSON(resp.ToolsJSON, .r)
    Do $$$AssertTrue($ISOBJECT(tools) && (tools.%Size() = 5), "five tool outputs captured for sealing")
    Do $$$AssertEquals(resp.CostMicroUSD, 0, "no cost in recorded mode")
    Do case.%DeleteId(case.%Id())
    Kill ^pbp.replay(cid)
    Do ##class(pbp.ToolsImpl).SetSessionCase("")
}


Method TestToolCaseIsolation()
{
    Set cid="unit-scope-" _ ##class(pbp.Util).RandomHex(4)
    Set other=cid_"-other"
    Set case=##class(pbp.Data.Case).%New()
    Set case.CaseId=cid,case.StoreId="store-default",case.ExceptionType="amount_mismatch"
    Set case.InputJSON="{""order"":{""id"":""SYNTHETIC-SECRET-OWN""}}"
    Do $$$AssertStatusOK(case.%Save(),"own case saved")
    Set foreign=##class(pbp.Data.Case).%New()
    Set foreign.CaseId=other,foreign.StoreId="store-default",foreign.ExceptionType="amount_mismatch"
    Set foreign.InputJSON="{""order"":{""id"":""SYNTHETIC-SECRET-FOREIGN""}}"
    Do $$$AssertStatusOK(foreign.%Save(),"foreign case saved")
    Do ##class(pbp.ToolsImpl).SetSessionCase("")
    Set none=##class(pbp.Tools).GetOrder(cid)
    Do $$$AssertTrue(none [ "case_context_missing","no context denies access")
    Set auth=##class(pbp.AuthPolicy).%New()
    Set denied=auth.%CanExecute("GetOrder",{"arguments":{"caseId":(cid)}},{})
    Do $$$AssertTrue($$$ISERR(denied),"native auth policy denies missing scope")
    Do ##class(pbp.ToolsImpl).SetSessionCase(cid)
    Set own=##class(pbp.Tools).GetOrder(cid)
    Do $$$AssertTrue(own [ "SYNTHETIC-SECRET-OWN","own case visible")
    Set foreignReply=##class(pbp.Tools).GetOrder(other)
    Do $$$AssertTrue((foreignReply [ "case_not_in_session") && (foreignReply '[ "SYNTHETIC-SECRET-FOREIGN"),"cross-case tool request discloses no foreign evidence")
    Set denied=auth.%CanExecute("GetOrder",{"arguments":{"caseId":(other)}},{})
    Do $$$AssertTrue($$$ISERR(denied),"native auth policy denies model-supplied foreign id")
    Set allowed=auth.%CanExecute("GetOrder",{"arguments":{"caseId":(cid)}},{})
    Do $$$AssertStatusOK(allowed,"native auth policy accepts own scope")
    Do ##class(pbp.ToolsImpl).SetSessionCase("")
    Do case.%DeleteId(case.%Id())
    Do foreign.%DeleteId(foreign.%Id())
}

}
