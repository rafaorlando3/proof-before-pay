/// Loaded only by the private runtime test harness, not by application startup.
Class ProofBeforePay.Tests.LedgerProbe Extends %RegisteredObject
{
ClassMethod UnprivilegedApprove(id As %String) As %String
{
    New $NAMESPACE
    Set original=$NAMESPACE
    Set name="PBPTestNoReview"_$JOB_"x"_$Extract($Translate($SYSTEM.Util.CreateGUID(),"-"),1,8)
    Set password=$SYSTEM.Util.CreateGUID()_"Aa9!"
    Set $NAMESPACE="%SYS"
    Set props("Roles")="%Developer",props("Password")=password,props("FullName")="Disposable test-only reviewer denial"
    Set props("NameSpace")="USER",props("ChangePassword")=0,props("Enabled")=1
    Set sc=##class(Security.Users).Create(name,.props)
    If $SYSTEM.Status.IsError(sc) Quit ##class(%DynamicObject).%FromJSON("{""ok"":false,""reason"":""test_user_setup_failed""}").%ToJSON()
    Set $NAMESPACE=original
    Try {
        Set out=..AsRestrictedUser(id,name,password)
    } Catch ex {
        Set out="{""ok"":false,""reason"":""test_login_failed""}"
    }
    Set $NAMESPACE="%SYS"
    Set deleted=##class(Security.Users).Delete(name)
    Set $NAMESPACE=original
    Set result=##class(%DynamicObject).%FromJSON(out)
    Do result.%Set("test_user_deleted",$SYSTEM.Status.IsOK(deleted),"boolean")
    Quit result.%ToJSON()
}

ClassMethod AsRestrictedUser(id As %String, name As %String, password As %String) As %String [ Private ]
{
    New $ROLES
    Set success=$SYSTEM.Security.Login(name,password)
    If 'success Quit "{""ok"":false,""reason"":""test_login_failed""}"
    Set out=##class(%DynamicObject).%FromJSON(##class(ProofBeforePay.Ledger).Approve(id))
    Do out.%Set("test_logged_in",($USERNAME=name),"boolean")
    Quit out.%ToJSON()
}

ClassMethod NestedStage(record As %String) As %String
{
    TStart
    Set before=$TLEVEL
    Set result=##class(%DynamicObject).%FromJSON(##class(ProofBeforePay.Ledger).Stage(record))
    Set after=$TLEVEL
    TRollback
    Set result.before=before,result.after=after
    Quit result.%ToJSON()
}
}
