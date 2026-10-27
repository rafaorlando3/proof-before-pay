"""Check a model proposal against observed tool outputs; never authorize an effect.

The ledger still validates every financial binding. This guard prevents a syntactically
valid proposal from closing a case using invented evidence or inconsistent action flags.
It performs no I/O and does not interpret instructions embedded in tool data.
"""
import json

TOOLS = {'GetOrder', 'GetPixEvents', 'GetPayerHistory', 'GetEvidence', 'GetStorePolicy'}
NON_FINANCIAL = {'accept_order', 'accept_order_keep_credit', 'release_order',
                 'hold_for_evidence', 'request_top_up', 'escalate_to_human'}


def observed_missing(tools: list) -> dict:
    missing = {}
    sections = {'GetOrder': 'order_lookup', 'GetPixEvents': 'payment_status',
                'GetPayerHistory': 'payer_history', 'GetEvidence': 'evidence',
                'GetStorePolicy': 'policy_lookup'}
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name, output = tool.get('name'), tool.get('output')
        if name not in sections:
            continue
        if output is None or isinstance(output, dict) and (output.get('error') or output.get('absent')
                or ('section' in output and 'value' in output)):
            missing[sections[name]] = None
        elif name == 'GetEvidence' and isinstance(output, dict):
            missing.update({'evidence.' + key: None for key, value in output.items()
                            if value is None or value == ''})
    return missing


def merge_missing(missing_json: str, tools_json: str) -> str:
    missing, tools = json.loads(missing_json), json.loads(tools_json)
    if not isinstance(missing, dict) or not isinstance(tools, list):
        raise ValueError('missing_context_invalid')
    return json.dumps({**missing, **observed_missing(tools)}, sort_keys=True)


def check_context(decision_json: str, tools_json: str) -> str:
    try:
        decision, tools = json.loads(decision_json), json.loads(tools_json)
        if not isinstance(decision, dict) or not isinstance(tools, list):
            return 'decision_context_invalid'
        action = decision.get('action')
        moves, human = decision.get('moves_money'), decision.get('requires_human')
        if type(moves) is not bool or type(human) is not bool:
            return 'decision_flags_invalid'
        if action == 'refund_duplicate':
            if not moves or not human:
                return 'refund_flags_inconsistent'
        elif action in NON_FINANCIAL:
            if moves:
                return 'nonfinancial_action_moves_money'
        else:
            return 'action_not_supported_in_v1'
        if action in {'escalate_to_human', 'hold_for_evidence'} and not human:
            return 'review_action_requires_human'
        missing = decision.get('missing')
        if not isinstance(missing, dict) or any(value is not None for value in missing.values()):
            return 'missing_invalid'
        if (missing or observed_missing(tools)) and not human:
            return 'missing_evidence_requires_human'

        seen, refs = set(), set()
        for tool in tools:
            if not isinstance(tool, dict):
                return 'tool_trace_invalid'
            name, output = tool.get('name'), tool.get('output')
            if name not in TOOLS:
                return 'tool_trace_invalid'
            seen.add(name)
            if isinstance(output, dict) and (output.get('error') or output.get('absent')
                                             or ('section' in output and 'value' in output)):
                continue
            if name == 'GetOrder' and isinstance(output, dict):
                refs.add('order')
            elif name == 'GetPayerHistory' and isinstance(output, dict):
                refs.add('payer_history')
            elif name == 'GetEvidence' and isinstance(output, dict):
                refs.update('evidence.' + key for key, value in output.items()
                            if value is not None and value != '')
            elif name == 'GetPixEvents' and isinstance(output, list):
                refs.update(payment['payment_ref'] for payment in output
                            if isinstance(payment, dict) and isinstance(payment.get('payment_ref'), str)
                            and payment['payment_ref'])
            elif name == 'GetStorePolicy' and isinstance(output, dict) and output.get('sha256'):
                refs.update({'policy', 'store_policy'})
        if seen != TOOLS:
            return 'required_tool_not_observed'
        if action == 'refund_duplicate':
            for tool in tools:
                if tool['name'] != 'GetPixEvents':
                    continue
                payments = tool.get('output')
                if not isinstance(payments, list) or len(payments) != 2:
                    return 'refund_requires_two_observed_payments'
                payment_refs = [p.get('payment_ref') if isinstance(p, dict) else None
                                for p in payments]
                if any(not isinstance(ref, str) or not ref.strip() for ref in payment_refs):
                    return 'refund_payment_reference_missing'
                if len(set(payment_refs)) != 2:
                    return 'refund_payment_references_not_distinct'
        cited = decision.get('evidence_refs')
        if not isinstance(cited, list) or not cited or any(not isinstance(ref, str) for ref in cited):
            return 'evidence_refs_invalid'
        if any(ref not in refs for ref in cited):
            return 'evidence_reference_not_observed'
        return ''
    except (ValueError, TypeError, KeyError):
        return 'decision_context_invalid'
