/// The reviewer's actions, executed IN THE REVIEWER'S OWN AUTHENTICATED SESSION (REST or terminal), never by the
/// business process: (1) record approval or rejection in the test ledger under $USERNAME, which requires the
/// PBPReview:U resource; (2) assign and complete the native Workflow task so the process continues.
/// Approving in the Management Portal inbox alone completes the task but leaves the ledger unauthorized; the
/// process then asks again (see pbp.Process.Decide.OnHuman).
Class pbp.Review Extends %RegisteredObject
{

Parameter RESOURCE = "PBPReview";

/// Cases waiting for a reviewer, with the task id when one is open for the case's production session.
ClassMethod Pending() As %DynamicArray
{
    Set arr = []
    Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT CaseId, ExceptionType, StatusReason, HeadCommitment, SessionId, UpdatedAt FROM pbp_Data.""Case"" WHERE Status = 'awaiting_human' ORDER BY UpdatedAt")
    While rs.%Next() {
        Set c = {}
        Set c."case_id" = rs.%Get("CaseId"), c.exception = rs.%Get("ExceptionType"), c.reason = rs.%Get("StatusReason")
        Set c.commitment = rs.%Get("HeadCommitment"), c."updated_at" = rs.%Get("UpdatedAt")
        Set c."task_id" = ..FindTask(rs.%Get("SessionId"))
        Set read = ##class(pbp.Util).ParseJSON(##class(ProofBeforePay.Ledger).Read(rs.%Get("HeadCommitment")), .r)
        Set c."ledger_state" = $SELECT($ISOBJECT(read) && read.ok: read.state, $ISOBJECT(read): "none:" _ read.reason, 1: "unknown")
        Do arr.%Push(c)
    }
    Quit arr
}

/// Open (not completed) Workflow task created in the given production session, or "".
ClassMethod FindTask(sessionId As %String) As %String
{
    Set found = ""
    If sessionId = "" Quit ""
    Try {
        Set rs = ##class(%SQL.Statement).%ExecDirect(, "SELECT ID FROM EnsLib_Workflow.TaskResponse ORDER BY ID DESC")
        While rs.%Next() {
            Set task = ##class(EnsLib.Workflow.TaskResponse).%OpenId(rs.%Get("ID"))
            Continue:'$ISOBJECT(task)
            Continue:'$ISOBJECT(task.%TaskStatus)
            If (task.%TaskStatus.SessionId = sessionId) && ('task.%TaskStatus.IsComplete) { Set found = task.%Id() Quit }
        }
    } Catch ex {
        Do ##class(pbp.Util).LogEx("pbp.Review.FindTask", ex)
    }
    Quit found
}

/// Approve or reject a case as the current user. action = "Approve" | "Reject". Returns a JSON reply object.
ClassMethod Act(caseId As %String, action As %String, note As %String = "", expectedCommitment As %String = "") As %DynamicObject
{
    Set out = {"ok": false, "case_id": (caseId), "action": (action), "user": ($USERNAME)}
    If (action '= "Approve") && (action '= "Reject") { Set out.reason = "action_must_be_Approve_or_Reject" Quit out }
    If '$SYSTEM.Security.Check(..#RESOURCE, "U") { Set out.reason = "review_forbidden:" _ ..#RESOURCE _ ":U required" Quit out }
    Set case = ##class(pbp.Data.Case).Find(caseId)
    If '$ISOBJECT(case) { Set out.reason = "case_not_found" Quit out }
    If case.Status '= "awaiting_human" { Set out.reason = "case_not_awaiting_human:" _ case.Status Quit out }
    If expectedCommitment="" { Set out.reason="expected_commitment_required" Quit out }
    If case.HeadCommitment'=expectedCommitment { Set out.reason="reviewed_version_changed" Quit out }
    Set out.commitment = case.HeadCommitment
    Set seal = ##class(pbp.Data.Seal).Find(case.HeadCommitment)
    If '$ISOBJECT(seal) { Set out.reason = "seal_not_found" Quit out }
    Set v = seal.Verify()
    If 'v.ok { Set out.reason = "seal_not_intact:" _ v.state Quit out }
    // Money decisions staged in the test ledger: record the reviewer's identity there first.
    If seal.Source = "ledger" {
        Set raw = $SELECT(action = "Approve": ##class(ProofBeforePay.Ledger).Approve(seal.Commitment), 1: ##class(ProofBeforePay.Ledger).Reject(seal.Commitment))
        Set led = ##class(pbp.Util).ParseJSON(raw, .r)
        If (led = "") || 'led.ok { Set out.reason = "ledger_" _ $SELECT($ISOBJECT(led): led.reason, 1: "invalid_json") Quit out }
        Set out."ledger_state" = led.state
        Do ##class(pbp.Data.Event).Add(caseId, "ledger_" _ $SELECT(action = "Approve": "authorized", 1: "rejected"), "by " _ $USERNAME _ " in their own session", seal.Commitment)
    }
    Set taskId = ..FindTask(case.SessionId)
    If taskId = "" { Set out.reason = "workflow_task_not_found" Quit out }
    Set task = ##class(EnsLib.Workflow.TaskResponse).%OpenId(taskId)
    If '$ISOBJECT(task) { Set out.reason = "workflow_task_unreadable" Quit out }
    Set failed = ""
    Try {
        Set sc = task.AssignTask($USERNAME, .count)
        If $$$ISERR(sc) {
            Set failed="assign_task_failed"
            Do ##class(pbp.Util).Log("warn","pbp.Review.Act","assign_task_failed",caseId)
            Quit
        }
        Set task.%UserName = $USERNAME
        If note '= "" Do task.%FormValues.SetAt($EXTRACT(note, 1, 400), "pbp_note")
        Set sc=task.%Save()
        If $$$ISERR(sc) { Set failed="save_review_task_failed" Quit }
        Set sc = task.CompleteTask(action)
        If $$$ISERR(sc) { Set failed = "complete_task_failed" Do ##class(pbp.Util).Log("error", "pbp.Review.Act", ##class(pbp.Util).Sanitize(##class(pbp.Util).StatusText(sc)), caseId) }
    } Catch ex {
        Set failed = "complete_task_exception"
        Do ##class(pbp.Util).LogEx("pbp.Review.Act", ex, caseId)
    }
    If failed '= "" { Set out.reason = failed Quit out }
    Set out."task_id" = taskId
    Do out.%Set("ok", 1, "boolean")
    Set out.reason = ""
    Quit out
}

}
