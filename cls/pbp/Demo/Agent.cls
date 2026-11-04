/// The original scoped tools/instructions, using a private host budget bridge.
/// This constant is a local placeholder, not a provider key or security boundary.
Class pbp.Demo.Agent Extends pbp.Agent
{
Method %OnInit() As %Status
{
    Set cfg=##class(pbp.Demo.Runtime).Config()
    If '$ISOBJECT(cfg) Quit $$$ERROR($$$GeneralError,"public_demo_profile_missing")
    Set config={"api_key":"pbp-public-live-local-placeholder-not-a-provider-key","base_url":(cfg."bridge_url")}
    Set ..Provider=##class(%AI.Provider).Create("openai",config)
    If '$ISOBJECT(..Provider) Quit $$$ERROR($$$GeneralError,"public_demo_provider_init_failed")
    Set ..Model=##class(pbp.Demo.Runtime).#MODEL
    Set ..Temperature=0,..MaxIterations=3
    Quit $$$OK
}
}
