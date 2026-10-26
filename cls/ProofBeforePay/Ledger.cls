/// Private test-only effect boundary. No banking adapter and no external settlement.
/// All mutations take the same short native lock and commit their state atomically.
/// Only trusted BS/BP code may Stage; model tools and public endpoints must not expose it.
Class ProofBeforePay.Ledger Extends %RegisteredObject
{
Parameter REVIEWRESOURCE = "PBPReview";

Parameter VALIDITYSECONDS = 600;

ClassMethod NowISO() As %String
{
    Set now=$ZTIMESTAMP
    Quit $ZDATE(+now,3)_"T"_$ZTIME($Piece(now,",",2),1,3)_"Z"
}

ClassMethod NowSeconds() As %Numeric
{
    Set now=$ZTIMESTAMP
    Quit ($Piece(now,",",1)*86400)+$Piece(now,",",2)
}

ClassMethod Error(reason As %String) As %String
{
    Set out={"schema":"pbp.test-ledger/1","ok":false,"state":"blocked","environment":"sandbox","authorizes_real_payment":false,"on_chain_verified":false}
    Set out.reason=reason
    Quit out.%ToJSON()
}

ClassMethod ValidID(id As %String) As %Boolean
{
    Quit ($Length(id)=64)&($Translate(id,"0123456789abcdef")="")
}

ClassMethod Plan(recordJSON As %String) As %DynamicObject
{
    Set adapter=##class(%SYS.Python).Import("pbp_ledger.contract")
    Quit ##class(%DynamicObject).%FromJSON(adapter."plan_json"(recordJSON))
}

ClassMethod Stage(recordJSON As %String) As %String
{
    If $TLEVEL Quit ..Error("nested_transaction")
    Set failed=""
    Try {
        Set plan=..Plan(recordJSON)
        If 'plan.ok {
            Set failed=plan.%ToJSON()
        } Else {
            Set seal=##class(%DynamicObject).%FromJSON(##class(ProofBeforePay.Witness).Seal(recordJSON))
            If 'seal.ok Set failed=..Error("seal_failed")
        }
    } Catch ex {
        Set failed=..Error("validation_unavailable")
    }
    If failed'="" Quit failed
    Set id=seal.commitment
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        Set prior=""
        If plan."effect_key"'="" Set prior=$Get(^PBP49Ledger("effectIndex",plan."effect_key"))
        If (plan."effect_key"'="")&(prior'="") {
            If $Get(^PBP49Ledger("decision",prior,"record"))=recordJSON {
                Set out=..Read(prior,1)
            } Else {
                Set out=..Error("payment_already_staged")
            }
        } Else {
            TStart
            Set seq=$Increment(^PBP49Ledger("sequence"))
            Set ^PBP49Ledger("decision",id,"record")=recordJSON
            Set ^PBP49Ledger("decision",id,"salt")=seal.salt
            Set ^PBP49Ledger("decision",id,"plan")=plan.%ToJSON()
            Set ^PBP49Ledger("decision",id,"state")=plan.state
            Set ^PBP49Ledger("decision",id,"sealed_seq")=seq
            Set ^PBP49Ledger("decision",id,"created_by")=$USERNAME
            Set ^PBP49Ledger("decision",id,"expires_seconds")=..NowSeconds()+..#VALIDITYSECONDS
            If plan."effect_key"'="" Set ^PBP49Ledger("effectIndex",plan."effect_key")=id
            TCommit
            Set out=..Read(id)
        }
    } Catch ex {
        If $TLEVEL TRollback
        Set out=..Error("storage_failed")
    }
    Lock -^PBP49Ledger("lock")
    Quit out
}

/// Approval identity comes from the IRIS session, never from a JSON operator field.
ClassMethod Approve(id As %String) As %String
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    If $TLEVEL Quit ..Error("nested_transaction")
    If ($USERNAME="")!($USERNAME="UnknownUser") Quit ..Error("review_forbidden")
    If '$SYSTEM.Security.Check(..#REVIEWRESOURCE,"U") Quit ..Error("review_forbidden")
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        Set state=$Get(^PBP49Ledger("decision",id,"state"))
        Set verified=##class(%DynamicObject).%FromJSON(..Verify(id))
        If 'verified.ok {
            Set out=..Error("proof_invalid")
        } ElseIf ..NowSeconds()>$Get(^PBP49Ledger("decision",id,"expires_seconds"),0) {
            Set out=..Error("authorization_expired")
        } ElseIf state="awaiting_approval" {
            TStart
            Set ^PBP49Ledger("decision",id,"approved_by")=$USERNAME
            Set ^PBP49Ledger("decision",id,"approved_commitment")=id
            Set ^PBP49Ledger("decision",id,"authorized_seq")=$Increment(^PBP49Ledger("sequence"))
            Set ^PBP49Ledger("decision",id,"state")="authorized"
            TCommit
            Set out=..Read(id)
        } ElseIf (state="authorized")!(state="executed")!(state="confirmed") {
            Set out=..Read(id)
        } Else {
            Set out=..Error("not_awaiting_approval")
        }
    } Catch ex {
        If $TLEVEL TRollback
        Set out=..Error("approval_failed")
    }
    Lock -^PBP49Ledger("lock")
    Quit out
}

ClassMethod Reject(id As %String) As %String
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    If $TLEVEL Quit ..Error("nested_transaction")
    If '$SYSTEM.Security.Check(..#REVIEWRESOURCE,"U") Quit ..Error("review_forbidden")
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        Set state=$Get(^PBP49Ledger("decision",id,"state"))
        If (state="awaiting_approval")!(state="authorized") {
            TStart
            Set ^PBP49Ledger("decision",id,"state")="rejected"
            Set ^PBP49Ledger("decision",id,"rejected_by")=$USERNAME
            Set ^PBP49Ledger("decision",id,"rejected_seq")=$Increment(^PBP49Ledger("sequence"))
            TCommit
            Set out=..Read(id)
        } Else {
            Set out=..Error("not_rejectable")
        }
    } Catch ex {
        If $TLEVEL TRollback
        Set out=..Error("rejection_failed")
    }
    Lock -^PBP49Ledger("lock")
    Quit out
}

ClassMethod Execute(id As %String) As %String
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    If $TLEVEL Quit ..Error("nested_transaction")
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        Set state=$Get(^PBP49Ledger("decision",id,"state"))
        Set verified=##class(%DynamicObject).%FromJSON(..Verify(id))
        If 'verified.ok {
            Set out=..Error("proof_invalid")
        } ElseIf (state="executed")!(state="confirmed") {
            If ..EffectMatches(id) {
                Set out=..Read(id,1)
            } Else {
                Set out=..Error("readback_mismatch")
            }
        } ElseIf state'="authorized" {
            Set out=..Error("not_authorized")
        } ElseIf ..NowSeconds()>$Get(^PBP49Ledger("decision",id,"expires_seconds"),0) {
            Set out=..Error("authorization_expired")
        } ElseIf $Get(^PBP49Ledger("decision",id,"approved_commitment"))'=id {
            Set out=..Error("approval_binding_mismatch")
        } Else {
            Set plan=..Plan(^PBP49Ledger("decision",id,"record"))
            Set effectKey=plan."effect_key"
            If ('plan.ok)!(effectKey="") {
                Set out=..Error("invalid_effect")
            } ElseIf $Data(^PBP49Ledger("effect",effectKey)) {
                Set out=..Error("effect_already_exists")
            } Else {
                TStart
                Set seq=$Increment(^PBP49Ledger("sequence"))
                Set receipt={"schema":"pbp.test-receipt/1","environment":"sandbox","settlement_verified":false}
                Set receipt."receipt_id"="test-refund:"_seq
                Set receipt.commitment=id,receipt."effect_key"=effectKey,receipt."case_id"=plan."case_id"
                Set receipt."amount_minor"=plan."amount_minor",receipt.currency=plan.currency,receipt."recipient_ref"=plan."recipient_ref"
                Set receipt."executed_at"=..NowISO()
                Set receipt."executed_seq"=seq,receipt."sealed_seq"=^PBP49Ledger("decision",id,"sealed_seq")
                Set receipt."authorized_seq"=^PBP49Ledger("decision",id,"authorized_seq")
                Set ^PBP49Ledger("effect",effectKey)=receipt.%ToJSON()
                Set ^PBP49Ledger("decision",id,"receipt")=receipt.%ToJSON()
                Set ^PBP49Ledger("decision",id,"state")="executed"
                Set counter=$Increment(^PBP49Ledger("effectCount",effectKey))
                TCommit
                Set out=..Read(id)
            }
        }
    } Catch ex {
        If $TLEVEL TRollback
        Set out=..Error("execution_failed")
    }
    Lock -^PBP49Ledger("lock")
    Quit out
}

/// Independent readback of the sandbox effect, not an assertion of bank settlement.
ClassMethod Confirm(id As %String) As %String
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    If $TLEVEL Quit ..Error("nested_transaction")
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        Set state=$Get(^PBP49Ledger("decision",id,"state"))
        If (state'="executed")&(state'="confirmed") {
            Set out=..Error("not_executed")
        } Else {
            Set verified=##class(%DynamicObject).%FromJSON(..Verify(id))
            Set plan=..Plan(^PBP49Ledger("decision",id,"record"))
            If ('verified.ok)!('..EffectMatches(id)) {
                Set out=..Error("readback_mismatch")
            } Else {
                If state="executed" {
                    TStart
                    Set ^PBP49Ledger("decision",id,"confirmed_seq")=$Increment(^PBP49Ledger("sequence"))
                    Set ^PBP49Ledger("decision",id,"state")="confirmed"
                    TCommit
                }
                Set out=..Read(id)
            }
        }
    } Catch ex {
        If $TLEVEL TRollback
        Set out=..Error("confirmation_failed")
    }
    Lock -^PBP49Ledger("lock")
    Quit out
}

ClassMethod EffectMatches(id As %String) As %Boolean [ Private ]
{
    Set valid=0
    Try {
        Set plan=..Plan(^PBP49Ledger("decision",id,"record"))
        Set effect=$Get(^PBP49Ledger("effect",plan."effect_key"))
        If plan.ok,(effect'=""),(effect=$Get(^PBP49Ledger("decision",id,"receipt"))) {
            Set receipt=##class(%DynamicObject).%FromJSON(effect)
            Set valid=(receipt.commitment=id)&(receipt."effect_key"=plan."effect_key")
            Set valid=valid&(receipt."case_id"=plan."case_id")&(receipt."amount_minor"=plan."amount_minor")
            Set valid=valid&(receipt.currency=plan.currency)&(receipt."recipient_ref"=plan."recipient_ref")
            Set valid=valid&(receipt."sealed_seq"=^PBP49Ledger("decision",id,"sealed_seq"))
            Set valid=valid&(receipt."authorized_seq"=^PBP49Ledger("decision",id,"authorized_seq"))
            Set valid=valid&(receipt."sealed_seq"<receipt."authorized_seq")&(receipt."authorized_seq"<receipt."executed_seq")
            Set valid=valid&(receipt.environment="sandbox")&('receipt."settlement_verified")
        }
    } Catch ex {
        Set valid=0
    }
    Quit valid
}

ClassMethod Envelope(id As %String) As %String
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        If '$Data(^PBP49Ledger("decision",id,"record")) {
            Set result=..Error("not_found")
        } Else {
            Set out={}
            Set out.record=##class(%DynamicObject).%FromJSON(^PBP49Ledger("decision",id,"record"))
            Set out.salt=^PBP49Ledger("decision",id,"salt"),out.commitment=id
            Set result=out.%ToJSON()
        }
    } Catch ex {
        Set result=..Error("proof_unavailable")
    }
    Lock -^PBP49Ledger("lock")
    Quit result
}

ClassMethod Verify(id As %String) As %String
{
    Try {
        Set envelope=..Envelope(id)
        Set out=##class(ProofBeforePay.Witness).VerifyLocal(envelope)
    } Catch ex {
        Set out=..Error("proof_unavailable")
    }
    Quit out
}

/// Read-only independent integrity check for dashboards and receipt projections. Never executes or confirms.
ClassMethod Audit(id As %String) As %String
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        Set out=##class(%DynamicObject).%FromJSON(..Snapshot(id))
        If out.ok {
            Set verified=##class(%DynamicObject).%FromJSON(..Verify(id))
            If 'verified.ok { Set out=##class(%DynamicObject).%FromJSON(..Error("proof_invalid")) }
            ElseIf out."test_effect" {
                If '..EffectMatches(id) { Set out=##class(%DynamicObject).%FromJSON(..Error("readback_mismatch")) }
                Else { Do out.%Set("receipt_integrity_verified",1,"boolean") }
            }
        }
        Set result=out.%ToJSON()
    } Catch ex { Set result=..Error("audit_unavailable") }
    Lock -^PBP49Ledger("lock")
    Quit result
}

ClassMethod Read(id As %String, replayed As %Boolean = 0) As %String
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    Lock +^PBP49Ledger("lock"):5
    If '$TEST Quit ..Error("ledger_busy")
    Try {
        Set out=..Snapshot(id,replayed)
    } Catch ex {
        Set out=..Error("read_failed")
    }
    Lock -^PBP49Ledger("lock")
    Quit out
}

ClassMethod Snapshot(id As %String, replayed As %Boolean = 0) As %String [ Private ]
{
    If '..ValidID(id) Quit ..Error("invalid_commitment")
    If '$Data(^PBP49Ledger("decision",id,"state")) Quit ..Error("not_found")
    Set plan=##class(%DynamicObject).%FromJSON(^PBP49Ledger("decision",id,"plan"))
    Set out={"schema":"pbp.test-ledger/1","ok":true,"environment":"sandbox","authorizes_real_payment":false,"on_chain_verified":false}
    Set out.commitment=id,out.state=^PBP49Ledger("decision",id,"state"),out.reason="stored_state"
    Set out."case_id"=plan."case_id",out."verification_state"="pending_local_only"
    Do out.%Set("replayed",replayed,"boolean")
    Set out."sealed_seq"=^PBP49Ledger("decision",id,"sealed_seq")
    Do out.%Set("expires_utc_seconds",+$Get(^PBP49Ledger("decision",id,"expires_seconds")),"number")
    If $Data(^PBP49Ledger("decision",id,"authorized_seq")) {
        Set out."authorized_seq"=^PBP49Ledger("decision",id,"authorized_seq")
        Set out."approved_by"=^PBP49Ledger("decision",id,"approved_by")
    }
    Do out.%Set("test_effect",($Data(^PBP49Ledger("decision",id,"receipt"))>0),"boolean")
    If out."test_effect" {
        Set out.receipt=##class(%DynamicObject).%FromJSON(^PBP49Ledger("decision",id,"receipt"))
        Set out."effect_count"=$Get(^PBP49Ledger("effectCount",plan."effect_key"),0)
    }
    If $Data(^PBP49Ledger("decision",id,"confirmed_seq")) Set out."confirmed_seq"=^PBP49Ledger("decision",id,"confirmed_seq")
    Quit out.%ToJSON()
}
}
