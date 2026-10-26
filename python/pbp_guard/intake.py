"""Intake guard: strict JSON (duplicate keys refused, bounded size/depth) and personal-data scan,
reusing the sealing core's rules so what cannot be sealed is never persisted either.
Returns a stable reason code or '' when clean. Never returns offending values."""
from pbp_witness.adapter import _parse, ContractError
from pbp_s0_core.pii import scan_pii


def check_json(text, max_bytes=60000):
    try:
        if type(text) is not str:
            return 'json_string_required'
        if len(text.encode('utf-8')) > max_bytes:
            return 'input_too_large'
        value = _parse(text)
    except ContractError as e:
        return str(e)
    except Exception:
        return 'invalid_json'
    if value.get('environment', 'sandbox') != 'sandbox':
        return 'sandbox_required'
    if 'payments' in value and 'pix' in value:
        return 'ambiguous_payment_fields'
    try:
        findings = scan_pii(value)
    except Exception:
        return 'guard_unavailable'
    if findings:
        return 'personal_data_found'
    return ''
