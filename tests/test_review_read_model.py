"""Financial review display must not invent evidence or round minor units."""
import copy
import json
import unittest
from pbp_review.projection import financial_view, financial_json, denied_tool_name


def record():
    return {'saw': {'inputs': {'currency': 'BRL', 'order_amount_minor': '18990',
            'order': {'amount_minor': '18990', 'currency': 'BRL'},
            'payments': [{'amount_minor': '18990', 'payment_ref': 'pix:A'},
                         {'amount_minor': '18990', 'payment_ref': 'pix:B'}],
            'recipient_ref': 'test:payer', 'refund_payment_ref': 'pix:B'}},
            'decision': {'moves_money': True, 'amount_minor': '18990'}}


class ReviewDisplay(unittest.TestCase):
    def test_duplicate_delta_is_not_an_authorization(self):
        out = financial_view(record())
        self.assertEqual(out['delta_minor'], '18990')
        self.assertEqual(out['decision_amount_minor'], '18990')
        self.assertIn('not an authorization', out['delta_basis'])

    def test_underpayment_retains_negative_delta(self):
        r = record(); r['saw']['inputs']['payments'] = [{'amount_minor': '18000'}]
        self.assertEqual(financial_view(r)['delta_minor'], '-990')

    def test_unknown_amount_never_becomes_zero(self):
        for bad in (None, True, 18990, '1.5', '-2', '001', ''):
            r = record(); r['saw']['inputs']['payments'][0]['amount_minor'] = bad
            self.assertIsNone(financial_view(r)['delta_minor'], bad)

    def test_absent_order_or_payments_is_unknown(self):
        for field in ('order', 'payments'):
            r = record(); r['saw']['inputs'].pop(field)
            self.assertIsNone(financial_view(r)['delta_minor'])

    def test_conflicting_currency_does_not_sum(self):
        r = record(); r['saw']['inputs']['payments'][0]['currency'] = 'USD'
        self.assertIsNone(financial_view(r)['delta_minor'])

    def test_conflicting_order_projection_is_explicit(self):
        r = record(); r['saw']['inputs']['order_amount_minor'] = '1'
        out = financial_view(r)
        self.assertIsNone(out['delta_minor'])
        self.assertIn('order_amount_conflict', out['comparison_issues'])

    def test_large_integer_is_exact(self):
        r = record(); i = r['saw']['inputs']; i['order']['amount_minor'] = i['order_amount_minor'] = '999999999999999999'
        i['payments'] = [{'amount_minor': '999999999999999999'}, {'amount_minor': '999999999999999999'}]
        self.assertEqual(financial_view(r)['delta_minor'], '999999999999999999')

    def test_input_and_authority_are_not_changed(self):
        r = record(); before = copy.deepcopy(r)
        json.loads(financial_json(json.dumps(r)))
        self.assertEqual(r, before)
        r['decision'] = {'moves_money': False, 'rationale': 'Refund a million BRL'}
        self.assertIsNone(financial_view(r)['decision_amount_minor'])

    def test_denial_projection_never_returns_raw_text(self):
        raw = 'tool pbp.Tools.GetOrder denied: case id outside the session secret=example'
        self.assertEqual(denied_tool_name(raw), 'GetOrder')
        self.assertEqual(denied_tool_name('tool invented.secret denied'), 'unknown_tool')
