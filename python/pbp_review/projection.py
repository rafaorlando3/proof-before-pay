"""Read-only display facts from a decision record already verified by the caller.

This never authorizes an effect. In particular, delta_minor is a comparison of
observations, not an executable refund amount. Unknown/conflicting amounts stay
unknown. Python integers preserve minor units without floating-point rounding.
"""
import json
import re

_MINOR = re.compile(r'(0|[1-9][0-9]{0,17})\Z')
_TOOLS = ('GetOrder', 'GetPixEvents', 'GetPayerHistory', 'GetEvidence', 'GetStorePolicy')


def minor(value):
    return value if isinstance(value, str) and _MINOR.fullmatch(value) else None


def financial_view(record):
    inputs = record.get('saw', {}).get('inputs', {})
    order = inputs.get('order')
    order = order if isinstance(order, dict) else {}
    currency = inputs.get('currency')
    currency = currency if isinstance(currency, str) and re.fullmatch('[A-Z]{3}', currency) else None
    expected = minor(order.get('amount_minor'))
    issues = []
    if inputs.get('order_amount_minor') is not None and inputs['order_amount_minor'] != expected:
        issues.append('order_amount_conflict')
    if not currency or order.get('currency') != currency:
        issues.append('currency_unknown_or_conflicting')
    payments = inputs.get('payments')
    observed = []
    complete = isinstance(payments, list) and bool(payments) and expected is not None
    for event in payments if isinstance(payments, list) else []:
        event = event if isinstance(event, dict) else {}
        value = minor(event.get('amount_minor'))
        if value is None or event.get('currency', currency) != currency:
            complete = False
        observed.append({'amount_minor': value,
                         'payment_ref': event.get('payment_ref') if isinstance(event.get('payment_ref'), str) else None,
                         'received_at': event.get('received_at') if isinstance(event.get('received_at'), str) else None})
    complete = complete and not issues
    delta = str(sum(int(p['amount_minor']) for p in observed) - int(expected)) if complete else None
    decision = record.get('decision', {})
    return {'order': {'amount_minor': expected, 'currency': order.get('currency') if isinstance(order.get('currency'),str) and re.fullmatch('[A-Z]{3}',order['currency']) else None},
            'payments': observed, 'currency': currency, 'delta_minor': delta,
            'delta_basis': 'sum of sealed payment amounts minus sealed order amount; not an authorization',
            'amounts_complete': complete, 'comparison_issues': issues,
            'recipient_ref': inputs.get('recipient_ref') if isinstance(inputs.get('recipient_ref'), str) else None,
            'refund_payment_ref': inputs.get('refund_payment_ref') if isinstance(inputs.get('refund_payment_ref'), str) else None,
            'decision_amount_minor': minor(decision.get('amount_minor')) if decision.get('moves_money') is True else None}


def financial_json(record_json):
    return json.dumps(financial_view(json.loads(record_json)), sort_keys=True, allow_nan=False)


def denied_tool_name(message):
    for tool in _TOOLS:
        if re.search(r'(?<![A-Za-z0-9_])' + tool + r'(?![A-Za-z0-9_])', str(message)):
            return tool
    return 'unknown_tool'
