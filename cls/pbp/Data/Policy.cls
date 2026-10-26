/// A store policy version. The JSON is hashed; the hash is sealed with every decision so a later
/// policy edit cannot be passed off as the one in force at decision time.
Class pbp.Data.Policy Extends %Persistent
{

Property PolicyId As %String(MAXLEN = 64) [ Required ];

Property Version As %String(MAXLEN = 32) [ Required ];

Property JSON As %String(MAXLEN = "") [ Required ];

Property Sha256 As %String(MAXLEN = 64) [ Required ];

Property LoadedAt As %String(MAXLEN = 32);

Property Active As %Boolean [ InitialExpression = 1 ];

Index IdVer On (PolicyId, Version) [ Unique ];

/// Load (or re-load) a policy from JSON text. Returns the saved object or "" with reason.
ClassMethod Load(json As %String, Output reason As %String) As pbp.Data.Policy
{
    Set reason = ""
    Set obj = ##class(pbp.Util).ParseJSON(json, .reason)
    If obj = "" Quit ""
    If (obj.id = "") || (obj.version = "") { Set reason = "policy_id_or_version_missing" Quit "" }
    If '$ISOBJECT(obj.limits) || (obj.limits.currency = "") || '##class(pbp.Util).IsMinorAmount(obj.limits."autonomous_minor") {
        Set reason = "policy_limits_invalid" Quit ""
    }
    If '$ISOBJECT(obj.forbidden) { Set reason = "policy_forbidden_missing" Quit "" }
    Set sha = ##class(pbp.Util).SHA256Hex(json)
    Set pol = ..IdVerOpen(obj.id, obj.version)
    If '$ISOBJECT(pol) {
        Set pol = ..%New()
        Set pol.PolicyId = obj.id
        Set pol.Version = obj.version
    }
    Set pol.JSON = json
    Set pol.Sha256 = sha
    Set pol.LoadedAt = ##class(pbp.Util).NowISO()
    Set pol.Active = 1
    Set sc = pol.%Save()
    If $$$ISERR(sc) { Set reason = "policy_save_failed: " _ ##class(pbp.Util).StatusText(sc) Quit "" }
    Quit pol
}

/// The active policy for a store (falls back to "store-default").
ClassMethod ActiveFor(storeId As %String) As pbp.Data.Policy
{
    Set id = $SELECT(storeId = "": "store-default", 1: storeId)
    Set pol = ""
    &sql(SELECT TOP 1 ID INTO :pid FROM pbp_Data.Policy WHERE PolicyId = :id AND Active = 1 ORDER BY Version DESC)
    If SQLCODE = 0 Set pol = ..%OpenId(pid)
    If '$ISOBJECT(pol) && (id '= "store-default") Quit ..ActiveFor("store-default")
    Quit pol
}

/// Parsed JSON object of this policy.
Method Object() As %DynamicObject
{
    Quit ##class(pbp.Util).ParseJSON(..JSON, .r)
}

/// Sorted unique list of forbidden actions, as pbp.seal/1 requires.
Method ForbiddenSorted() As %DynamicArray
{
    Set obj = ..Object()
    Set arr = obj.forbidden
    Kill tmp
    Set it = arr.%GetIterator()
    While it.%GetNext(.k, .v) { If v '= "" Set tmp(v) = "" }
    Set out = []
    Set k = ""
    For { Set k = $ORDER(tmp(k)) Quit:k=""  Do out.%Push(k) }
    Quit out
}

}
