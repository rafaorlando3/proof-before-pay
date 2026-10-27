"""Deterministic payment selection. Unknown/ambiguous input never becomes a target.
The ledger independently validates the exact sealed amount, recipient and payment.
"""
import datetime
import json
import re

_ID = re.compile(r'[A-Za-z0-9_:.\-]{1,64}\Z')
_AMOUNT = re.compile(r'[1-9][0-9]{0,17}\Z')
_TIME = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z')


def timestamp(value):
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(datetime.timezone.utc)
    except (ValueError, OverflowError):
        return None


def derive(value):
    def refusal(reason):
        return {'payment_ref': None, 'reason': reason}
    if not isinstance(value, dict):
        return refusal('input_invalid')
    pays = value.get('payments')
    if not isinstance(pays, list) or len(pays) != 2 or any(not isinstance(p, dict) for p in pays):
        return refusal('payments_not_two')
    refs = [p.get('payment_ref') for p in pays]
    if any(not isinstance(r, str) or not _ID.fullmatch(r) for r in refs) or refs[0] == refs[1]:
        return refusal('payment_refs_not_distinct')
    order = value.get('order')
    amount = order.get('amount_minor') if isinstance(order, dict) else None
    if not isinstance(amount, str) or not _AMOUNT.fullmatch(amount) or any(p.get('amount_minor') != amount for p in pays):
        return refusal('amount_mismatch')
    if value.get('order_amount_minor', amount) != amount:
        return refusal('order_amount_mismatch')
    if value.get('currency') != 'BRL' or order.get('currency') != 'BRL' or any(p.get('currency', 'BRL') != 'BRL' for p in pays):
        return refusal('currency_mismatch')
    payer = pays[0].get('payer')
    if not isinstance(payer, str) or not _ID.fullmatch(payer) or not payer.startswith('test:') or pays[1].get('payer') != payer:
        return refusal('payer_mismatch')
    recipient = value.get('recipient_ref')
    if recipient not in (None, '') and recipient != payer:
        return refusal('recipient_mismatch')
    explicit = value.get('refund_payment_ref')
    if explicit not in (None, ''):
        if not isinstance(explicit, str) or explicit not in refs:
            return refusal('refund_payment_not_observed')
        return {'payment_ref': explicit, 'reason': ''}
    dates = [timestamp(p.get('received_at')) for p in pays]
    if any(d is None for d in dates):
        return refusal('received_at_invalid_or_missing')
    if dates[0] == dates[1]:
        return refusal('received_at_ambiguous')
    return {'payment_ref': refs[1] if dates[1] > dates[0] else refs[0], 'reason': ''}


def derive_json(text):
    try:
        result = derive(json.loads(text))
    except (ValueError, TypeError):
        result = {'payment_ref': None, 'reason': 'input_invalid'}
    return json.dumps(result, sort_keys=True, allow_nan=False)
