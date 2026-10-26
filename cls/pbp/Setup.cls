/// One-shot installer, run at container start after the classes compile:
/// loads the policy, the synthetic cases index and the recorded decisions, creates the Workflow role and
/// the reviewer user membership, registers the REST web application, and starts the production.
Class pbp.Setup Extends %RegisteredObject
{

Parameter ROLE = "pbp.Workflow";

ClassMethod Install(root As %String = "/opt/pbp", startProduction As %Boolean = 1) As %Status
{
    Set sc = $$$OK
    Try {
        Write "PBP_SETUP policy: "
        Set sc = ..LoadPolicies(root _ "/policy")
        Write $SELECT($$$ISOK(sc): "ok", 1: ##class(pbp.Util).StatusText(sc)), !
        Quit:$$$ISERR(sc)
        Write "PBP_SETUP replay: "
        Set sc = ..LoadReplay(root _ "/fixtures/replay/decisions.json")
        Write $SELECT($$$ISOK(sc): "ok", 1: ##class(pbp.Util).StatusText(sc)), !
        Quit:$$$ISERR(sc)
        Write "PBP_SETUP security (PBPReview resource, PBPReviewer role): "
        Set sc = ..EnsureSecurity()
        Write $SELECT($$$ISOK(sc): "ok", 1: ##class(pbp.Util).StatusText(sc)), !
        Quit:$$$ISERR(sc)
        Write "PBP_SETUP query permissions: "
        Set sc=..EnsureSQLPermissions()
        Write $SELECT($$$ISOK(sc):"ok",1:##class(pbp.Util).StatusText(sc)),!
        Quit:$$$ISERR(sc)
        Write "PBP_SETUP workflow role: "
        Set sc = ..EnsureRole()
        Write $SELECT($$$ISOK(sc): "ok", 1: ##class(pbp.Util).StatusText(sc)), !
        Quit:$$$ISERR(sc)
        Write "PBP_SETUP agent mode: "
        Set sc = ..ConfigureAgentMode()
        Write $SELECT($$$ISOK(sc): $SELECT(##class(pbp.Agent).HasKey(): "live (key found in " _ ##class(pbp.Agent).KeyVariable() _ ")", 1: "recorded (no key)"), 1: ##class(pbp.Util).StatusText(sc)), !
        Quit:$$$ISERR(sc)
        Write "PBP_SETUP rest app: "
        Set sc = ..EnsureWebApp(root)
        Write $SELECT($$$ISOK(sc): "ok", 1: ##class(pbp.Util).StatusText(sc)), !
        Quit:$$$ISERR(sc)
        If startProduction {
            Write "PBP_SETUP production: "
            Set running=##class(Ens.Director).IsProductionRunning(.current)
            If running && (current'= "pbp.Production") { Set sc=$$$ERROR($$$GeneralError,"another_production_running") Quit }
            Set sc = ##class(Ens.Director).SetAutoStart("pbp.Production")
            If $$$ISOK(sc) && ('running) Set sc = ##class(Ens.Director).StartProduction("pbp.Production")
            Write $SELECT($$$ISOK(sc): "started", 1: ##class(pbp.Util).StatusText(sc)), !
        }
    } Catch ex {
        Set sc = ex.AsStatus()
        Write "PBP_SETUP exception: ", ex.Name, " ", ex.Code, " ", ex.Location, !
    }
    Quit sc
}

/// Load every *.json in the policy directory.
ClassMethod LoadPolicies(dir As %String) As %Status
{
    Set rs = ##class(%ResultSet).%New("%File:FileSet")
    Set sc = rs.Execute(dir, "*.json")
    If $$$ISERR(sc) Quit sc
    Set n = 0
    While rs.Next() {
        Set path = rs.Get("Name")
        Set json = ..ReadFile(path, .sc)
        If $$$ISERR(sc) Quit
        Set pol = ##class(pbp.Data.Policy).Load(json, .reason)
        If '$ISOBJECT(pol) { Set sc = $$$ERROR($$$GeneralError, "policy " _ path _ ": " _ reason) Quit }
        Set n = n + 1
    }
    If $$$ISOK(sc) && (n = 0) Set sc = $$$ERROR($$$GeneralError, "no policy file in " _ dir)
    Quit sc
}

/// Recorded decisions keyed by case id, for replay mode.
ClassMethod LoadReplay(path As %String) As %Status
{
    Set json = ..ReadFile(path, .sc)
    If $$$ISERR(sc) Quit sc
    Set obj = ##class(pbp.Util).ParseJSON(json, .reason)
    If obj = "" Quit $$$ERROR($$$GeneralError, "replay file invalid: " _ reason)
    Kill ^pbp.replay
    Set it = obj.%GetIterator()
    While it.%GetNext(.k, .v) { Set ^pbp.replay(k) = v.%ToJSON() }
    Quit $$$OK
}

/// Reviewers: comma list in PBP_REVIEWERS (IRIS users), default _SYSTEM,SuperUser,Admin.
ClassMethod Reviewers() As %List
{
    Quit $LISTFROMSTRING(##class(pbp.Util).Env("PBP_REVIEWERS", $USERNAME _ ",_SYSTEM,SuperUser,Admin"), ",")
}

/// Security resource PBPReview and role PBPReviewer (PBPReview:U), granted to the reviewers. Runs in %SYS.
ClassMethod EnsureSecurity() As %Status
{
    New $NAMESPACE
    Set sc = $$$OK
    Set users = ..Reviewers()
    Try {
        Set $NAMESPACE = "%SYS"
        If '##class(Security.Resources).Exists("PBPReview") {
            Set sc = ##class(Security.Resources).Create("PBPReview", "Approve or reject sealed Proof Before Pay decisions in the test ledger", "")
            If $$$ISERR(sc) Quit
        }
        If '##class(Security.Roles).Exists("PBPReviewer") {
            Set sc = ##class(Security.Roles).Create("PBPReviewer", "Proof Before Pay reviewer", "PBPReview:U")
            If $$$ISERR(sc) Quit
        }
        For i = 1:1:$LISTLENGTH(users) {
            Set u = $LISTGET(users, i)
            Continue:u=""
            Continue:'##class(Security.Users).Exists(u)
            Set sc1 = ##class(Security.Users).AddRoles(u, "PBPReviewer")
            If $$$ISERR(sc1) Write "(AddRoles " _ u _ ": " _ $SYSTEM.Status.GetErrorText(sc1) _ ") "
        }
    } Catch ex {
        Set sc = ex.AsStatus()
    }
    Quit sc
}

/// Authenticated reviewers may query the synthetic projections and locate their native Workflow task.
ClassMethod EnsureSQLPermissions() As %Status
{
    Set sc=$$$OK
    For table="pbp_Data.""Case""","pbp_Data.Decision","pbp_Data.Event","pbp_Data.Log","pbp_Data.Policy","pbp_Data.Seal","pbp_Data.Permit","pbp_Data.Receipt","pbp_Data.ToolCall","EnsLib_Workflow.TaskResponse" {
        Set rs=##class(%SQL.Statement).%ExecDirect(,"GRANT SELECT ON "_table_" TO PBPReviewer")
        If rs.%SQLCODE<0 { Set sc=$$$ERROR($$$GeneralError,"projection_query_grant_failed:"_table_":"_rs.%SQLCODE) Quit }
    }
    Quit sc
}

/// Workflow role for the human step (build 154 signatures: CreateRole(name); AddUserToRole(role, user, ranking, title)).
ClassMethod EnsureRole() As %Status
{
    Set sc = $$$OK
    If '##class(EnsLib.Workflow.RoleDefinition).%ExistsId(..#ROLE) {
        Set sc = ##class(EnsLib.Workflow.RoleDefinition).CreateRole(..#ROLE)
        If $$$ISERR(sc) Quit sc
    }
    Set users = ..Reviewers()
    For i = 1:1:$LISTLENGTH(users) {
        Set u = $LISTGET(users, i)
        Continue:u=""
        If '##class(EnsLib.Workflow.UserDefinition).%ExistsId(u) Do ##class(EnsLib.Workflow.UserDefinition).CreateUser(u, u)
        Do ##class(EnsLib.Workflow.RoleDefinition).AddUserToRole(..#ROLE, u, 3, "")
    }
    Quit sc
}

/// Live agent item enabled only when a provider key is present (and PBP_LLM_MODE is not "recorded");
/// the replay item is always enabled. The production definition is updated in place.
ClassMethod ConfigureAgentMode() As %Status
{
    Set sc = $$$OK
    Try {
        Set live = ##class(pbp.Agent).HasKey() && (##class(pbp.Util).Env("PBP_LLM_MODE", "auto") '= "recorded")
        Set prod = ##class(Ens.Config.Production).%OpenId("pbp.Production")
        If '$ISOBJECT(prod) Quit
        For i = 1:1:prod.Items.Count() {
            Set item = prod.Items.GetAt(i)
            If item.Name = "pbp.Operation.Agent" Set item.Enabled = live
            If item.Name = "pbp.Operation.Replay" Set item.Enabled = 1
        }
        Set sc = prod.%Save()
    } Catch ex {
        Set sc = ex.AsStatus()
    }
    Quit sc
}

/// REST application /pbp/api served by pbp.API (password authentication, same namespace).
ClassMethod EnsureWebApp(root As %String = "/opt/pbp") As %Status
{
    New $NAMESPACE
    Set ns = $NAMESPACE
    Set ^pbp.config("uiRoot")=root_"/ui"
    Set $NAMESPACE = "%SYS"
    Set props("NameSpace") = ns
    Set props("DispatchClass") = "pbp.API"
    Set props("Description") = "Proof Before Pay API"
    Set props("AutheEnabled") = 32
    If ##class(Security.Applications).Exists("/pbp/api") {
        Set sc = ##class(Security.Applications).Modify("/pbp/api", .props)
    } Else {
        Set sc = ##class(Security.Applications).Create("/pbp/api", .props)
    }
    If $$$ISERR(sc) Quit sc
    Kill props
    Set props("NameSpace") = ns
    Set props("Path") = ""
    Set props("DispatchClass") = "pbp.UI"
    Set props("ServeFiles") = 0
    Set props("ServeFilesTimeout") = 60
    Set props("Description") = "Proof Before Pay review console"
    Set props("AutheEnabled") = 32
    Set props("Recurse") = 1
    If ##class(Security.Applications).Exists("/pbp/ui") {
        Set sc = ##class(Security.Applications).Modify("/pbp/ui", .props)
    } Else {
        Set sc = ##class(Security.Applications).Create("/pbp/ui", .props)
    }
    Quit sc
}

ClassMethod ReadFile(path As %String, Output sc As %Status) As %String
{
    Set sc = $$$OK
    Set s = ##class(%Stream.FileCharacter).%New()
    Set s.TranslateTable = "UTF8"
    Set sc = s.LinkToFile(path)
    If $$$ISERR(sc) Quit ""
    Set out = ""
    While 's.AtEnd { Set out = out _ s.Read(32000) }
    Quit out
}

/// Feed the synthetic cases in fixtures/cases/*.json through the production (demo and tests).
ClassMethod FeedCases(dir As %String = "/opt/pbp/fixtures/cases", limit As %Integer = 100) As %Status
{
    Set sc = ##class(Ens.Director).CreateBusinessService("pbp.Service.Intake", .svc)
    If $$$ISERR(sc) Quit sc
    Set rs = ##class(%ResultSet).%New("%File:FileSet")
    Set sc = rs.Execute(dir, "*.json")
    If $$$ISERR(sc) Quit sc
    Set n = 0
    While rs.Next() && (n < limit) {
        Set json = ..ReadFile(rs.Get("Name"), .sc)
        Quit:$$$ISERR(sc)
        Set sc = svc.ProcessInput(##class(Ens.StringContainer).%New(json), .out)
        If $$$ISERR(sc) { Write "feed error: ", ##class(pbp.Util).StatusText(sc), ! Set sc = $$$OK Continue }
        Set n = n + 1
        Write "fed ", out.CaseId, !
    }
    Quit sc
}

}
