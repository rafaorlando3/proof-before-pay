"""Bounded offline JSON adapter. Never logs input, opens network or moves money."""
import hmac
import json
import re

from pbp_s0_core.record import SealError, commitment, seal

MAX_INPUT_BYTES = 32768
HEX64 = re.compile(r'[0-9a-f]{64}')
SAFE_REASONS = frozenset({
    'missing_field', 'wrong_type', 'unknown_field', 'float_not_allowed',
    'number_not_finite', 'int_out_of_safe_range', 'non_string_key',
    'unsupported_type', 'not_sorted_unique', 'bad_spec_version', 'bad_kind',
    'bad_timestamp', 'bad_case_id', 'bad_prev', 'missing_value_must_be_null',
    'bad_hash', 'bad_model_mode', 'rationale_length', 'evidence_refs_missing',
    'confidence_out_of_range', 'action_is_forbidden', 'bad_amount',
    'bad_currency', 'money_above_limit_without_human', 'bad_operator_id',
    'bad_outcome', 'record_not_object', 'personal_data_found', 'bad_salt',
})

class ContractError(Exception):
    pass

def _reply(ok, state, reason, **fields):
    value = {
        'schema': 'pbp.witness.response/1', 'spec': 'pbp.seal/1',
        'mode': 'offline_local', 'ok': ok, 'state': state, 'reason': reason,
        'on_chain_verified': False, 'authorizes_payment': False,
        'money_order_verified': False,
    }
    value.update(fields)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)

def _parse(text):
    if type(text) is not str:
        raise ContractError('json_string_required')
    try:
        if len(text.encode('utf-8')) > MAX_INPUT_BYTES:
            raise ContractError('input_too_large')
    except UnicodeError:
        raise ContractError('invalid_json') from None
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ContractError('duplicate_field')
            value[key] = item
        return value
    def constant(_):
        raise ContractError('nonfinite_json')
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ContractError('invalid_json') from None
    if type(value) is not dict:
        raise ContractError('json_object_required')
    def bounded(item, depth=0):
        if depth > 20:
            raise ContractError('input_too_deep')
        if type(item) is dict:
            for child in item.values():
                bounded(child, depth + 1)
        elif type(item) is list:
            for child in item:
                bounded(child, depth + 1)
    bounded(value)
    return value

def _hex64(value, code):
    if type(value) is not str or len(value) != 64 or HEX64.fullmatch(value) is None:
        raise ContractError(code)
    return value

def _error(error):
    if isinstance(error, ContractError):
        reason = str(error)  # Only fixed local codes are ever constructed.
    elif isinstance(error, SealError):
        reason = error.reason if error.reason in SAFE_REASONS else 'invalid_record'
    else:
        reason = 'internal_error'
    # Never project exception text, offending values, JSON paths or findings.
    return _reply(False, 'unverifiable', reason)

def seal_json(record_json):
    """Return a private local envelope. Caller owns record/salt storage; no anchor."""
    try:
        record = _parse(record_json)
        value = seal(record)  # Exact S0 core; CSPRNG salt is generated inside S0.
        _hex64(value['salt'], 'internal_error')
        return _reply(True, 'pending', 'local_only_not_anchored', **value)
    except Exception as error:
        return _error(error)

def verify_local_json(envelope_json):
    """Check local record+salt against expected digest. Local match stays pending."""
    try:
        value = _parse(envelope_json)
        if set(value) != {'record', 'salt', 'commitment'}:
            raise ContractError('envelope_fields')
        salt = _hex64(value['salt'], 'bad_salt')
        expected = _hex64(value['commitment'], 'bad_hash')
        actual = commitment(value['record'], salt)
        if not hmac.compare_digest(actual, expected):
            return _reply(False, 'tampered', 'commitment_mismatch')
        return _reply(True, 'pending', 'local_match_not_anchored', commitment=actual)
    except Exception as error:
        return _error(error)
