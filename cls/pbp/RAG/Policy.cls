/// Optional policy retrieval through the native AI Hub RAG stack and local FastEmbed.
/// Full policy constraints remain authoritative; retrieved passages add provenance only.
Class pbp.RAG.Policy Extends %RegisteredObject
{
ClassMethod Ready(pol As pbp.Data.Policy) As %Boolean
{
    If '$ISOBJECT(pol) Quit 0
    If '$MATCH(pol.Sha256,"[0-9a-f]{64}") Quit 0
    Quit $GET(^pbp.policyRAG(pol.Sha256,"ready"))=1
}

ClassMethod Applies(caseId As %String, pol As pbp.Data.Policy) As %Boolean
{
    Quit ..Ready(pol) && +$GET(^pbp.policyRAG("enabled")) && ##class(pbp.Demo.Runtime).Allows(caseId)
}

ClassMethod Text(pol As pbp.Data.Policy, section As %String) As %String
{
    Set obj=pol.Object()
    If '$ISOBJECT(obj) Quit ""
    If (section'="limits") && (section'="allowed_actions") && (section'="forbidden") && (section'="rules") Quit ""
    Set value=obj.%Get(section)
    If '$ISOBJECT(value) Quit ""
    Quit section_": "_value.%ToJSON()
}

ClassMethod Build(pol As pbp.Data.Policy, Output kb As %AI.RAG.KnowledgeBase) As %Status
{
    Set kb="",sc=$$$OK
    Try {
        If '$ISOBJECT(pol) || '$MATCH(pol.Sha256,"[0-9a-f]{64}") Throw ##class(%Exception.General).%New("policy_identity_required")
        If ($LENGTH(pol.JSON)>20000) || (##class(pbp.Util).SHA256Hex(pol.JSON)'=pol.Sha256) Throw ##class(%Exception.General).%New("bounded_intact_policy_required")
        Set emb=##class(%AI.RAG.Embedding.FastEmbed).Create()
        Set vs=##class(%AI.RAG.VectorStore.IRIS).%New()
        Set vs.TableName="pbp_RAG.Policy"_$EXTRACT(pol.Sha256,1,40),vs.Dimensions=384,vs.ModelName="AllMiniLML6V2"
        Set sc=vs.Build()
        If $$$ISERR(sc) Throw ##class(%Exception.StatusException).CreateFromStatus(sc)
        Set kb=##class(%AI.RAG.KnowledgeBase).%New("search_pbp_store_policy","Current synthetic store policy passages; constraints are returned separately and remain authoritative")
        Set kb.TopK=3
        Set sc=kb.Build(emb,vs)
        If $$$ISERR(sc) Throw ##class(%Exception.StatusException).CreateFromStatus(sc)
    } Catch ex { Set sc=ex.AsStatus() }
    Quit sc
}

/// Explicit operator indexing, once per exact policy hash. Never runs at installation or from a model.
ClassMethod Stage(pol As pbp.Data.Policy) As %Status
{
    If '$SYSTEM.Security.Check("%Admin_Manage","USE") Quit $$$ERROR($$$GeneralError,"policy_index_operator_required")
    If ..Ready(pol) Quit $$$OK
    Set sc=..Build(pol,.kb)
    If $$$ISERR(sc) Quit sc
    If $DATA(^pbp.policyRAG(pol.Sha256,"index_attempt")) Quit $$$ERROR($$$GeneralError,"partial_policy_index_reconcile_first")
    Set ^pbp.policyRAG(pol.Sha256,"index_attempt")=##class(pbp.Util).NowISO()
    Try {
        For section="limits","allowed_actions","forbidden","rules" {
            Set text=..Text(pol,section)
            If text="" Throw ##class(%Exception.General).%New("policy_section_missing")
            Set meta={"source":("policy:"_pol.Sha256_":"_section),"policy_sha256":(pol.Sha256),"policy_id":(pol.PolicyId),"policy_version":(pol.Version),"section":(section),"passage_sha256":(##class(pbp.Util).SHA256Hex(text))}
            Set sc=kb.AddDocument(text,meta)
            If $$$ISERR(sc) Throw ##class(%Exception.StatusException).CreateFromStatus(sc)
        }
        Set ^pbp.policyRAG(pol.Sha256,"ready")=1
        Set ^pbp.policyRAG(pol.Sha256,"indexed_at")=##class(pbp.Util).NowISO()
    } Catch ex { Set sc=ex.AsStatus() }
    Quit sc
}

ClassMethod SetEnabled(enabled As %Boolean) As %Status
{
    If '$SYSTEM.Security.Check("%Admin_Manage","USE") Quit $$$ERROR($$$GeneralError,"policy_index_operator_required")
    Set ^pbp.policyRAG("enabled")=enabled
    Set index=$INCREMENT(^pbp.policyRAG("history"))
    Set entry={"enabled":(enabled),"at":(##class(pbp.Util).NowISO())}
    Set ^pbp.policyRAG("history",index)=entry.%ToJSON()
    Quit $$$OK
}

/// Executes a native KB search locally, validates every passage against the exact active policy.
/// Errors return an explicit unavailable result; full policy constraints are still returned by the tool.
ClassMethod Retrieve(pol As pbp.Data.Policy, query As %String) As %DynamicObject
{
    Set out={"available":false,"method":"AI Hub RAG + IRIS Vector Search","embedding_model":"AllMiniLML6V2","embedding_location":"local","passages":[]}
    Try {
        If '..Ready(pol) || ($LENGTH(query)>500) || (query="") Throw ##class(%Exception.General).%New("policy_index_unavailable")
        Set sc=..Build(pol,.kb)
        If $$$ISERR(sc) Throw ##class(%Exception.StatusException).CreateFromStatus(sc)
        Set mgr=##class(%AI.ToolMgr).%New()
        Set sc=kb.AddToManager(mgr)
        If $$$ISERR(sc) Throw ##class(%Exception.StatusException).CreateFromStatus(sc)
        Set result=mgr.ExecuteTool("search_pbp_store_policy",{"query":(query),"top_k":3})
        If '$ISOBJECT(result.value) Throw ##class(%Exception.General).%New("policy_search_result_invalid")
        Set passages=[]
        For i=0:1:result.value.%Size()-1 {
            Set hit=result.value.%Get(i),meta=hit.metadata
            If '$ISOBJECT(meta) || (meta."policy_sha256"'=pol.Sha256) Throw ##class(%Exception.General).%New("policy_search_identity_mismatch")
            Set expected=..Text(pol,meta.section)
            If (expected="") || (hit.text'=expected) || (meta."passage_sha256"'=##class(pbp.Util).SHA256Hex(expected)) Throw ##class(%Exception.General).%New("policy_passage_integrity_mismatch")
            Set passage={"chunk_id":(hit.id),"source":(meta.source),"section":(meta.section),"text":(hit.text),"sha256":(meta."passage_sha256")}
            Do passage.%Set("similarity_decimal",$FNUMBER(hit.score,"",8),"string")
            Do passages.%Push(passage)
        }
        If passages.%Size()=0 Throw ##class(%Exception.General).%New("policy_search_empty")
        Set out.passages=passages,out.query=query,out."policy_sha256"=pol.Sha256,out."policy_version"=pol.Version
        Do out.%Set("available",1,"boolean")
    } Catch ex { Set out.reason="policy_retrieval_unavailable_full_constraints_retained" }
    Quit out
}

ClassMethod ForCase(pol As pbp.Data.Policy, case As pbp.Data.Case) As %DynamicObject
{
    Set query=$SELECT(case.ExceptionType="amount_mismatch":"Payment amount differs from the order. Which actions, limits and review rules apply?",case.ExceptionType="refund_request":"Refund request with missing delivery proof. Which actions and restrictions apply?",1:"Which payment actions, limits and restrictions apply to this exception?")
    Quit ..Retrieve(pol,query)
}
}
