/// Bounded local sealing adapter; local verification remains pending until anchored.
/// InterSystems official %SYS.Python.Import API; JSON strings cross the boundary.
Class ProofBeforePay.Witness Extends %RegisteredObject
{
ClassMethod Seal(recordJSON As %String) As %String
{
    Try {
        Set adapter = ##class(%SYS.Python).Import("pbp_witness.adapter")
        Set response = adapter."seal_json"(recordJSON)
    } Catch ex {
        Set response = "{""schema"":""pbp.witness.response/1"",""spec"":""pbp.seal/1"",""mode"":""offline_local"",""ok"":false,""state"":""unverifiable"",""reason"":""bridge_unavailable"",""on_chain_verified"":false,""authorizes_payment"":false,""money_order_verified"":false}"
    }
    Quit response
}

ClassMethod VerifyLocal(envelopeJSON As %String) As %String
{
    Try {
        Set adapter = ##class(%SYS.Python).Import("pbp_witness.adapter")
        Set response = adapter."verify_local_json"(envelopeJSON)
    } Catch ex {
        Set response = "{""schema"":""pbp.witness.response/1"",""spec"":""pbp.seal/1"",""mode"":""offline_local"",""ok"":false,""state"":""unverifiable"",""reason"":""bridge_unavailable"",""on_chain_verified"":false,""authorizes_payment"":false,""money_order_verified"":false}"
    }
    Quit response
}
}
