/// Deterministic business rules. They close the simple cases without a model and always say which
/// evidence was absent. Output is a %DynamicObject:
///   {decided, rule, action, moves_money, amount_minor, requires_human, confidence, rationale, evidence_refs, missing, refund_payment_ref}
/// `missing` is an object whose values are null (sealed ignorance). Rules never call a model or move money.
/// Input shape (normalized by pbp.Process.Decide): order{amount_minor,currency,status,expires_at}, payments[{payment_ref,amount_minor,payer,received_at}],
/// recipient_ref, payer_history, evidence{...}.
Class pbp.Rules Extends %RegisteredObject
{

Parameter ENGINE = "pbp.Rules";

Parameter VERSION = "3";

/// Evaluate a normalized case input against a policy object.
ClassMethod Evaluate(input As %DynamicObject, policy As %DynamicObject) As %DynamicObject
{
    Set out = {}
    Do out.%Set("decided", 0, "boolean")
    Set out.rule = "no_match"
    Set out.missing = ..Missing(input)
    Set p = policy.rules
    If '$ISOBJECT(p) Set p = {}
    Set smallDiff = $SELECT(p."small_diff_minor" = "": 200, 1: +p."small_diff_minor")
    Set graceHours = $SELECT(p."late_grace_hours" = "": 48, 1: +p."late_grace_hours")
    Set type = input.exception
    Set order = input.order
    Set pays = input.payments
    Set orderAmount = $SELECT($ISOBJECT(order): order."amount_minor", 1: "")

    // R1: two Pix payments for one order, same payer, same amount as the order -> refund the later one.
    // Every refund needs a person in v1 (test ledger policy): the rule proposes, a reviewer approves.
    If (type = "duplicate_payment") && $ISOBJECT(pays) && (pays.%Size() = 2) {
        Set a = pays.%Get(0), b = pays.%Get(1)
        If $ISOBJECT(a) && $ISOBJECT(b) && (a."amount_minor" = b."amount_minor") && (a."amount_minor" = orderAmount) && (a.payer = b.payer) && (a.payer '= "") && (a."payment_ref" '= b."payment_ref") {
            Set refs = ["order"]
            Do refs.%Push(a."payment_ref")
            Do refs.%Push(b."payment_ref")
            Set target=##class(pbp.RefundTarget).Derive(input,.targetReason)
            If target="" {
                Do out.missing.%Set("refund_target","","null")
                Quit ..Decide(out,"R1","escalate_to_human",0,"",1,0.99,"The payment to return cannot be selected from the observed evidence; a person must resolve it: "_targetReason,refs)
            }
            If input."recipient_ref" = "" {
                Do out.missing.%Set("refund_target", "", "null")
                Set out."refund_payment_ref" = target
                Quit ..Decide(out, "R1", "refund_duplicate", 1, orderAmount, 1, 0.99, "Two Pix payments with the same amount from the same payer for one order; the later one is a duplicate. The refund destination is unknown, so a person must choose it.", refs)
            }
            Set out."refund_payment_ref" = target
            Quit ..Decide(out, "R1", "refund_duplicate", 1, orderAmount, 1, 0.99, "Two Pix payments with the same amount from the same payer for one order: the later one is a duplicate and is refunded in full to the payer after a reviewer approves.", refs)
        }
    }

    // R2: small amount difference -> accept without money movement.
    If (type = "amount_mismatch") && $ISOBJECT(pays) && (pays.%Size() >= 1) && $ISOBJECT(order) {
        Set paid = pays.%Get(0)."amount_minor"
        Set diff = +paid - +orderAmount
        Set refs = ["order"]
        Do refs.%Push(pays.%Get(0)."payment_ref")
        If (diff >= 0) && (diff <= smallDiff) {
            Quit ..Decide(out, "R2", "accept_order_keep_credit", 0, "", 0, 0.98, "Overpayment within the small-difference threshold: accept the order and keep the difference as store credit.", refs)
        }
        If (diff < 0) && (-diff <= smallDiff) {
            Quit ..Decide(out, "R2", "accept_order", 0, "", 0, 0.97, "Underpayment within the small-difference threshold: accept the order as paid.", refs)
        }
    }

    // R3: payment arrived late but inside the grace window and the order is still waiting -> release.
    If (type = "late_payment") && $ISOBJECT(order) && $ISOBJECT(pays) && (pays.%Size() >= 1) {
        Set expires = ##class(pbp.Util).ISOToSeconds(order."expires_at")
        Set received = ##class(pbp.Util).ISOToSeconds(pays.%Get(0)."received_at")
        Set refs = ["order"]
        Do refs.%Push(pays.%Get(0)."payment_ref")
        If (expires > 0) && (received > 0) && (order.status = "awaiting_payment") && ((received - expires) <= (graceHours * 3600)) && (pays.%Get(0)."amount_minor" = orderAmount) {
            Quit ..Decide(out, "R3", "release_order", 0, "", 0, 0.97, "Full payment arrived after expiry but inside the grace window and the order was still waiting: release it.", refs)
        }
    }
    Quit out
}

ClassMethod Decide(out As %DynamicObject, rule As %String, action As %String, movesMoney As %Boolean, amountMinor As %String, requiresHuman As %Boolean, confidence As %Numeric, rationale As %String, refs As %DynamicArray) As %DynamicObject
{
    Do out.%Set("decided", 1, "boolean")
    Set out.rule = rule
    Set out.action = action
    Do out.%Set("moves_money", movesMoney, "boolean")
    If amountMinor '= "" Set out."amount_minor" = amountMinor
    Do out.%Set("requires_human", requiresHuman, "boolean")
    Set out.confidence = confidence
    Set out.rationale = rationale
    Set out."evidence_refs" = refs
    Quit out
}

/// Evidence the case does NOT contain: every null under "evidence", plus absent payer history.
/// Key names that the test ledger treats as blocking: order_lookup, refund_target, payment_status.
ClassMethod Missing(input As %DynamicObject) As %DynamicObject
{
    Set m = {}
    Set ev = input.evidence
    If $ISOBJECT(ev) {
        Set it = ev.%GetIterator()
        While it.%GetNext(.k, .v) {
            If (ev.%GetTypeOf(k) = "null") || (v = "") Do m.%Set("evidence." _ k, "", "null")
        }
    } Else {
        Do m.%Set("evidence", "", "null")
    }
    If '$ISOBJECT(input."payer_history") Do m.%Set("payer_history", "", "null")
    If '$ISOBJECT(input.order) Do m.%Set("order_lookup", "", "null")
    Quit m
}

}
