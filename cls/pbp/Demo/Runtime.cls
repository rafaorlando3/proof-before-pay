/// Optional public synthetic-demo profile. No provider secret is stored in IRIS.
/// Operator staging/enabling is explicit; normal installation does neither.
Class pbp.Demo.Runtime Extends %RegisteredObject
{
Parameter MODEL = "gemini-3.6-flash";

ClassMethod Config() As %DynamicObject
{
    Set cfg=##class(pbp.Util).ParseJSON($GET(^pbp.demoRuntime("config")),.reason)
    If '$ISOBJECT(cfg) Quit ""
    If cfg.schema'="pbp.public-live-native/1" Quit ""
    If '$MATCH(cfg."source_revision","[0-9a-f]{40}") Quit ""
    If cfg.model'=..#MODEL Quit ""
    If '$MATCH(cfg."expires_at","[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.]000Z") Quit ""
    // Only an explicitly selected private bridge, never a caller-supplied URL.
    If '$MATCH(cfg."bridge_url","http://(127[.]0[.]0[.]1|10[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}|172[.](1[6-9]|2[0-9]|3[01])[.][0-9]{1,3}[.][0-9]{1,3}|192[.]168[.][0-9]{1,3}[.][0-9]{1,3}):[0-9]{1,5}/v1") Quit ""
    Quit cfg
}

ClassMethod Allows(caseId As %String) As %Boolean
{
    If '$MATCH(caseId,"public-live:[A-Za-z0-9_\-]{16,48}") Quit 0
    Set cfg=..Config()
    If '$ISOBJECT(cfg) Quit 0
    Quit +cfg.enabled && ..IsUnexpired(cfg."expires_at")
}

/// Canonical UTC ISO strings require string collation, not numeric < or >.
ClassMethod IsUnexpired(expires As %String, now As %String = "") As %Boolean
{
    If now="" Set now=##class(pbp.Util).NowISO()
    Quit expires]now
}

ClassMethod ItemsReady() As %Boolean
{
    Set prod=##class(Ens.Config.Production).%OpenId("pbp.Production")
    If '$ISOBJECT(prod) Quit 0
    For name="pbp.Demo.Intake","pbp.Demo.Process","pbp.Demo.Operation" {
        Set item=prod.FindItemByConfigName(name,.sc)
        If $$$ISERR(sc) || '$ISOBJECT(item) Quit
        If (item.ClassName'=name) || 'item.Enabled Quit
        If (name'="pbp.Demo.Intake") && (item.PoolSize'=1) Quit
        If name="pbp.Demo.Process" {
            Set safe=0
            For i=1:1:item.Settings.Count() {
                Set setting=item.Settings.GetAt(i)
                If (setting.Name="AutonomousEffects") && (setting.Target="Host") && (setting.Value="0") Set safe=1
            }
            If 'safe Quit
        }
        Set checked(name)=1
    }
    Quit $DATA(checked("pbp.Demo.Intake")) && $DATA(checked("pbp.Demo.Process")) && $DATA(checked("pbp.Demo.Operation"))
}

ClassMethod PublicStatus() As %DynamicObject
{
    Set cfg=..Config(),out={"enabled":false,"model":(..#MODEL),"case_prefix":"public-live:","transport":"private_budget_bridge","autonomous_effects":false,"source_revision":""}
    If '$ISOBJECT(cfg) Quit out
    Set out."source_revision"=cfg."source_revision"
    Set ok=+cfg.enabled && ..IsUnexpired(cfg."expires_at") && ..ItemsReady()
    Do out.%Set("enabled",ok,"boolean")
    Quit out
}

/// Records a new profile and only its three actors. Never starts/restarts the production.
ClassMethod Stage(bridgeURL As %String, revision As %String, expires As %String, approval As %String) As %Status
{
    Set sc=$$$OK,owned=0
    Try {
        If '$SYSTEM.Security.Check("%Admin_Manage","USE") Throw ##class(%Exception.General).%New("demo_operator_required")
        If $DATA(^pbp.demoRuntime("config")) Throw ##class(%Exception.General).%New("demo_already_staged_reconcile_do_not_overwrite")
        If (approval="") || ($LENGTH(approval)>200) Throw ##class(%Exception.General).%New("demo_approval_reference_required")
        If $TLEVEL'=0 Throw ##class(%Exception.General).%New("demo_outer_transaction_forbidden")
        Set cfg={"schema":"pbp.public-live-native/1","enabled":false,"model":(..#MODEL),"bridge_url":(bridgeURL),"source_revision":(revision),"expires_at":(expires),"approval_ref":(approval)}
        // Use the same reader inside the configuration transaction; failures roll back.
        TSTART
        Set owned=1,^pbp.demoRuntime("config")=cfg.%ToJSON()
        If '$ISOBJECT(..Config()) Throw ##class(%Exception.General).%New("demo_profile_invalid")
        Set prod=##class(Ens.Config.Production).%OpenId("pbp.Production")
        If '$ISOBJECT(prod) Throw ##class(%Exception.General).%New("demo_production_missing")
        For name="pbp.Demo.Intake","pbp.Demo.Process","pbp.Demo.Operation" {
            Set item=prod.FindItemByConfigName(name,.unused)
            If $ISOBJECT(item) Throw ##class(%Exception.General).%New("demo_item_already_exists_reconcile")
            Set item=##class(Ens.Config.Item).%New()
            Set item.Name=name,item.ClassName=name,item.Enabled=1,item.Foreground=0,item.LogTraceEvents=0
            Set item.PoolSize=$SELECT(name="pbp.Demo.Intake":0,1:1)
            Set item.Comment="Optional fixed synthetic live demo; private budget bridge, no public review"
            If name="pbp.Demo.Intake" Do ..Setting(item,"Host","TargetConfigName","pbp.Demo.Process")
            If name="pbp.Demo.Process" Do ..Setting(item,"Host","AutonomousEffects","0")
            If name="pbp.Demo.Operation" {
                Do ..Setting(item,"Adapter","AgentClass","pbp.Demo.Agent")
                Do ..Setting(item,"Adapter","AuthPolicy","pbp.AuthPolicy")
                Do ..Setting(item,"Adapter","AuditPolicy","pbp.AuditPolicy")
                Do ..Setting(item,"Host","FailureTimeout","0")
                Do ..Setting(item,"Host","RetryInterval","0")
            }
            Do prod.Items.Insert(item)
        }
        Set sc=prod.%Save()
        If $$$ISERR(sc) Throw ##class(%Exception.StatusException).CreateFromStatus(sc)
        Set ^pbp.demoRuntime("staged_at")=##class(pbp.Util).NowISO()
        TCOMMIT
        Set owned=0
    } Catch ex {
        If owned && $TLEVEL TROLLBACK
        Set sc=ex.AsStatus()
    }
    Quit sc
}

/// Explicit OFF-profile recovery after a base production was reimported at boot.
/// Call only with this production stopped. Never stage a new profile or reset history.
/// expectedRevision compares the caller expectation to persisted config; it is not
/// an attestation of loaded source. Before enable, the operator must verify the
/// deployed bundle and explicitly RebindRevision. Other operator setters do not
/// take this restore lock; coordinate them while the production is stopped.
ClassMethod RestoreStagedActors(expectedRevision As %String) As %Status
{
    Set sc=$$$OK,owned=0,locked=0
    Try {
        If '$SYSTEM.Security.Check("%Admin_Manage","USE") Throw ##class(%Exception.General).%New("demo_operator_required")
        If $TLEVEL'=0 Throw ##class(%Exception.General).%New("demo_outer_transaction_forbidden")
        Lock +^pbp.demoRuntime("restore_lock"):0
        If '$TEST Throw ##class(%Exception.General).%New("demo_restore_busy")
        Set locked=1,cfg=..Config(),before=$GET(^pbp.demoRuntime("config"))
        If '$ISOBJECT(cfg) Throw ##class(%Exception.General).%New("demo_profile_missing")
        If cfg.enabled Throw ##class(%Exception.General).%New("disable_demo_before_restore")
        If '$MATCH(expectedRevision,"[0-9a-f]{40}") || (cfg."source_revision"'=expectedRevision) Throw ##class(%Exception.General).%New("demo_source_revision_changed")
        Set running=##class(Ens.Director).IsProductionRunning(.current)
        If running && (current="pbp.Production") Throw ##class(%Exception.General).%New("stop_own_production_before_restore")
        Set prod=##class(Ens.Config.Production).%OpenId("pbp.Production")
        If '$ISOBJECT(prod) Throw ##class(%Exception.General).%New("demo_production_missing")
        Set present=0
        For name="pbp.Demo.Intake","pbp.Demo.Process","pbp.Demo.Operation" {
            Set item=prod.FindItemByConfigName(name,.unused)
            If $ISOBJECT(item) Set present=present+1
        }
        If present && ((present'=3) || '..ItemsReady()) Throw ##class(%Exception.General).%New("demo_actor_configuration_requires_review")
        If present=0 {
            TSTART
            Set owned=1
            If before'=$GET(^pbp.demoRuntime("config")) Throw ##class(%Exception.General).%New("demo_profile_changed_during_restore")
        For name="pbp.Demo.Intake","pbp.Demo.Process","pbp.Demo.Operation" {
            Set item=prod.FindItemByConfigName(name,.unused)
            If $ISOBJECT(item) Throw ##class(%Exception.General).%New("demo_item_already_exists_reconcile")
            Set item=##class(Ens.Config.Item).%New()
            Set item.Name=name,item.ClassName=name,item.Enabled=1,item.Foreground=0,item.LogTraceEvents=0
            Set item.PoolSize=$SELECT(name="pbp.Demo.Intake":0,1:1)
            Set item.Comment="Optional fixed synthetic live demo; private budget bridge, no public review"
            If name="pbp.Demo.Intake" Do ..Setting(item,"Host","TargetConfigName","pbp.Demo.Process")
            If name="pbp.Demo.Process" Do ..Setting(item,"Host","AutonomousEffects","0")
            If name="pbp.Demo.Operation" {
                Do ..Setting(item,"Adapter","AgentClass","pbp.Demo.Agent")
                Do ..Setting(item,"Adapter","AuthPolicy","pbp.AuthPolicy")
                Do ..Setting(item,"Adapter","AuditPolicy","pbp.AuditPolicy")
                Do ..Setting(item,"Host","FailureTimeout","0")
                Do ..Setting(item,"Host","RetryInterval","0")
            }
            Do prod.Items.Insert(item)
        }
            // Write history before Save: there is no fallible history write after Save.
            Set entry={"at":(##class(pbp.Util).NowISO()),"source_revision":(expectedRevision),"kept_disabled":true}
            Set i=$INCREMENT(^pbp.demoRuntime("restore_history")),^pbp.demoRuntime("restore_history",i)=entry.%ToJSON()
            Set sc=prod.%Save()
            If $$$ISERR(sc) Throw ##class(%Exception.StatusException).CreateFromStatus(sc)
            TCOMMIT
            Set owned=0
        }
    } Catch ex {
        If owned && $TLEVEL TROLLBACK
        Set sc=ex.AsStatus()
    }
    If locked Lock -^pbp.demoRuntime("restore_lock")
    Quit sc
}

ClassMethod Setting(item As Ens.Config.Item, target As %String, name As %String, value As %String)
{
    Set setting=##class(Ens.Config.Setting).%New()
    Set setting.Target=target,setting.Name=name,setting.Value=value
    Do item.Settings.Insert(setting)
}

/// Explicit toggle only; costs, queues, cases, approvals and history are untouched.
ClassMethod SetEnabled(enabled As %Boolean) As %Status
{
    If '$SYSTEM.Security.Check("%Admin_Manage","USE") Quit $$$ERROR($$$GeneralError,"demo_operator_required")
    Set cfg=..Config()
    If '$ISOBJECT(cfg) Quit $$$ERROR($$$GeneralError,"demo_profile_missing")
    If enabled && ('..IsUnexpired(cfg."expires_at") || '..ItemsReady()) Quit $$$ERROR($$$GeneralError,"demo_profile_not_ready")
    Do cfg.%Set("enabled",enabled,"boolean")
    Set ^pbp.demoRuntime("config")=cfg.%ToJSON()
    Set entry={"enabled":(enabled),"at":(##class(pbp.Util).NowISO())}
    Set index=$INCREMENT(^pbp.demoRuntime("enabled_history"))
    Set ^pbp.demoRuntime("enabled_history",index)=entry.%ToJSON()
    Quit $$$OK
}

/// Rebind only a disabled profile after verifying changed native source files.
/// This does not recreate the profile, clear its history or touch any budget.
ClassMethod RebindRevision(expected As %String, revision As %String, approval As %String) As %Status
{
    If '$SYSTEM.Security.Check("%Admin_Manage","USE") Quit $$$ERROR($$$GeneralError,"demo_operator_required")
    Set cfg=..Config()
    If '$ISOBJECT(cfg) Quit $$$ERROR($$$GeneralError,"demo_profile_missing")
    If cfg.enabled Quit $$$ERROR($$$GeneralError,"disable_demo_before_source_rebind")
    If cfg."source_revision"'=expected Quit $$$ERROR($$$GeneralError,"demo_source_revision_changed")
    If '$MATCH(revision,"[0-9a-f]{40}") || (approval="") Quit $$$ERROR($$$GeneralError,"reviewed_revision_reference_required")
    Set entry={"from":(expected),"to":(revision),"approval_ref":(approval),"at":(##class(pbp.Util).NowISO())}
    Set index=$INCREMENT(^pbp.demoRuntime("revision_history"))
    Set ^pbp.demoRuntime("revision_history",index)=entry.%ToJSON()
    Set cfg."source_revision"=revision
    Set ^pbp.demoRuntime("config")=cfg.%ToJSON()
    Quit $$$OK
}

/// Explicit operator-only migration of an OFF legacy profile; no activation or reset.
/// Config() intentionally rejects the old model after installing the new constant.
ClassMethod MigrateDisabledModel(expectedRevision As %String, revision As %String, approval As %String) As %Status
{
    Set sc=$$$OK,owned=0,locked=0
    Try {
        If '$SYSTEM.Security.Check("%Admin_Manage","USE") Throw ##class(%Exception.General).%New("demo_operator_required")
        If $TLEVEL'=0 Throw ##class(%Exception.General).%New("demo_outer_transaction_forbidden")
        If '$MATCH(expectedRevision,"[0-9a-f]{40}") || '$MATCH(revision,"[0-9a-f]{40}") || (revision=expectedRevision) || (approval="") || ($LENGTH(approval)>200) Throw ##class(%Exception.General).%New("reviewed_model_migration_reference_required")
        Lock +^pbp.demoRuntime("config"):5
        If '$TEST Throw ##class(%Exception.General).%New("demo_profile_busy")
        Set locked=1,cfg=##class(pbp.Util).ParseJSON($GET(^pbp.demoRuntime("config")),.reason)
        If '$ISOBJECT(cfg) Throw ##class(%Exception.General).%New("demo_profile_missing")
        If cfg.schema'="pbp.public-live-native/1" Throw ##class(%Exception.General).%New("demo_profile_invalid")
        If cfg.enabled Throw ##class(%Exception.General).%New("disable_demo_before_model_migration")
        If (cfg."source_revision"'=expectedRevision) || (cfg.model'="gemini-3.8-flash") Throw ##class(%Exception.General).%New("demo_expected_model_or_source_changed")
        Set entry={"from_model":(cfg.model),"to_model":(..#MODEL),"from_source":(expectedRevision),"to_source":(revision),"approval_ref":(approval),"at":(##class(pbp.Util).NowISO())}
        TSTART
        Set owned=1,cfg.model=..#MODEL,cfg."source_revision"=revision,^pbp.demoRuntime("config")=cfg.%ToJSON()
        If '$ISOBJECT(..Config()) Throw ##class(%Exception.General).%New("demo_migrated_profile_invalid")
        Set index=$INCREMENT(^pbp.demoRuntime("model_history")),^pbp.demoRuntime("model_history",index)=entry.%ToJSON()
        TCOMMIT
        Set owned=0
    } Catch ex {
        If owned TROLLBACK
        Set sc=ex.AsStatus()
    }
    If locked Lock -^pbp.demoRuntime("config")
    Quit sc
}
}
