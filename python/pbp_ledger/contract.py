"""Validate the effect bound inside a sealed decision, independently of the LLM.

The trusted Interoperability intake/policy owns evidence provenance. This second
boundary restricts the ledger to synthetic duplicate refunds and derives every
effect field from the exact record; execution never accepts replacement fields.
"""
import json
import re

from pbp_witness.adapter import _parse
from pbp_s0_core.record import validate

_ID = re.compile(r'[A-Za-z0-9_:.\-]{1,64}')
MAX_REFUND_MINOR = 100000
SCHEMA = 'pbp.test-ledger/1'


def reply(ok, state, reason, **fields):
    value = dict(schema=SCHEMA, ok=ok, state=state, reason=reason,
                 environment='sandbox', authorizes_real_payment=False,
                 on_chain_verified=False)
    value.update(fields)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class BindingError(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise BindingError(reason)


def plan(record):
    validate(record)
    _require(record['kind'] == 'decision', 'decision_required')
    d = record['decision']
    if not d['moves_money']:
        _require(d['action'] in {'request_information', 'escalate', 'hold'}, 'unsupported_action')
        return dict(effect_key='', case_id=record['case']['id'], amount_minor='0',
                    recipient_ref='', currency='BRL', requires_human=False,
                    state='sealed', reason='no_financial_action')
    _require(d['action'] == 'refund_duplicate', 'unsupported_action')
    # Demo policy: every financial effect needs a separate authenticated review.
    # Neither model confidence nor a limit supplied in the record can waive it.
    _require(d['requires_human'] is True, 'human_required')
    inputs = record['saw']['inputs']
    _require(inputs.get('environment') == 'sandbox', 'sandbox_required')
    _require(record['case']['exception'] in {'duplicate_payment', 'duplicate_charge'}, 'unsupported_exception')
    amount = d.get('amount_minor')
    _require(type(amount) is str and re.fullmatch(r'[1-9][0-9]{0,5}', amount) is not None,
             'invalid_effect_amount')
    _require(int(amount) <= MAX_REFUND_MINOR, 'refund_cap_exceeded')
    _require(record['limits']['currency'] == 'BRL' and inputs.get('currency') == 'BRL',
             'currency_mismatch')
    recipient = inputs.get('recipient_ref')
    payment_ref = inputs.get('refund_payment_ref')
    _require(type(recipient) is str and _ID.fullmatch(recipient) is not None
             and recipient.startswith('test:'), 'test_recipient_required')
    _require(type(payment_ref) is str and _ID.fullmatch(payment_ref) is not None,
             'refund_payment_required')
    _require(inputs.get('order_amount_minor') == amount, 'amount_mismatch')
    payments = inputs.get('payments')
    _require(type(payments) is list and len(payments) == 2
             and all(type(p) is dict for p in payments), 'duplicate_evidence_required')
    refs = [p.get('payment_ref') for p in payments]
    _require(all(type(r) is str and _ID.fullmatch(r) is not None for r in refs)
             and len(set(refs)) == 2 and payment_ref in refs, 'payment_reference_mismatch')
    _require(all(p.get('amount_minor') == amount and p.get('payer') == recipient for p in payments),
             'payment_binding_mismatch')
    _require(payment_ref in d['evidence_refs'] and set(refs) <= set(d['evidence_refs']),
             'evidence_reference_mismatch')
    _require(not ({'order_lookup', 'refund_target', 'payment_status'} & record['missing'].keys()),
             'required_evidence_missing')
    # Deduplicate both observed payments, including targets reserved by older plans.
    # Choosing the opposite member must not turn one duplicate into two refunds.
    return dict(effect_key=payment_ref, payment_refs=sorted(refs),
                case_id=record['case']['id'], amount_minor=amount,
                recipient_ref=recipient, currency='BRL', requires_human=True,
                state='awaiting_approval', reason='review_required')


def plan_json(record_json):
    try:
        value = plan(_parse(record_json))
        return reply(True, **value)
    except BindingError as e:
        return reply(False, 'blocked', str(e))
    except Exception:
        # The Witness boundary reports detailed safe schema reason codes. This
        # layer must not leak offending data or exception strings to a caller.
        return reply(False, 'blocked', 'invalid_record')
