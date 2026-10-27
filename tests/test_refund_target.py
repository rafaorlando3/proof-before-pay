import copy
import itertools
import json
import unittest
from pbp_refund_target.derive import derive, derive_json


class RefundTarget(unittest.TestCase):
    def setUp(self):
        self.value = {'currency': 'BRL', 'order': {'amount_minor': '4200', 'currency': 'BRL'},
                      'order_amount_minor': '4200', 'recipient_ref': 'test:buyer',
                      'payments': [dict(payment_ref='pix:A', amount_minor='4200', payer='test:buyer', received_at='2026-10-20T12:00:00Z'),
                                   dict(payment_ref='pix:B', amount_minor='4200', payer='test:buyer', received_at='2026-10-20T12:02:00Z')]}

    def test_order_independent_selection_and_no_input_mutation(self):
        original = copy.deepcopy(self.value)
        for order in itertools.permutations(self.value['payments']):
            self.assertEqual({'payment_ref': 'pix:B', 'reason': ''}, derive({**self.value, 'payments': list(order)}))
        self.assertEqual(original, self.value)

    def test_offsets_compared_as_instants_not_strings(self):
        self.value['payments'][0]['received_at'] = '2026-10-20T13:00:00+02:00'
        self.assertEqual('pix:B', derive(self.value)['payment_ref'])

    def test_equal_instants_are_ambiguous_even_with_different_offsets(self):
        self.value['payments'][0]['received_at'] = '2026-10-20T14:02:00+02:00'
        self.assertEqual('received_at_ambiguous', derive(self.value)['reason'])

    def test_invalid_or_missing_time_never_selects_a_payment(self):
        for date in [None, '', 'yesterday', '2026-02-30T12:00:00Z', '2026-10-20T12:00:00', '0001-01-01T00:00:00+14:00', 4]:
            self.value['payments'][0]['received_at'] = date
            self.assertIsNone(derive(self.value)['payment_ref'])

    def test_explicit_observed_target_is_preserved_without_guessing(self):
        self.value['refund_payment_ref'] = 'pix:A'
        self.value['payments'][0].pop('received_at')
        self.assertEqual({'payment_ref': 'pix:A', 'reason': ''}, derive(self.value))
        self.value['refund_payment_ref'] = 'pix:FOREIGN'
        self.assertEqual('refund_payment_not_observed', derive(self.value)['reason'])

    def test_explicit_target_does_not_bypass_distinct_reference_check(self):
        self.value['refund_payment_ref'] = 'pix:A'
        self.value['payments'][1]['payment_ref'] = 'pix:A'
        self.assertEqual('payment_refs_not_distinct', derive(self.value)['reason'])

    def test_exact_amounts_and_payers_must_agree(self):
        for field, value, reason in [('amount_minor', '4201', 'amount_mismatch'), ('payer', 'test:other', 'payer_mismatch')]:
            sample = copy.deepcopy(self.value); sample['payments'][1][field] = value
            self.assertEqual(reason, derive(sample)['reason'])
        self.value['order_amount_minor'] = '4201'
        self.assertEqual('order_amount_mismatch', derive(self.value)['reason'])

    def test_unknown_recipient_is_not_invented(self):
        self.value.pop('recipient_ref')
        self.assertEqual('pix:B', derive(self.value)['payment_ref'])
        self.assertNotIn('recipient_ref', self.value)
        self.value['recipient_ref'] = 'test:other'
        self.assertEqual('recipient_mismatch', derive(self.value)['reason'])

    def test_currency_and_identifier_shape(self):
        self.value['payments'][1]['currency'] = 'USD'
        self.assertEqual('currency_mismatch', derive(self.value)['reason'])
        self.value['payments'][1].pop('currency')
        self.value['payments'][1]['payment_ref'] = 'not a valid reference'
        self.assertEqual('payment_refs_not_distinct', derive(self.value)['reason'])

    def test_cardinality_and_malformed_inputs(self):
        for value in [None, [], {'payments': {}}, {**self.value, 'payments': self.value['payments'][:1]},
                      {**self.value, 'payments': self.value['payments'] * 2}, {**self.value, 'payments': [None, {}]}]:
            self.assertIsNone(derive(value)['payment_ref'])
        self.assertEqual('input_invalid', json.loads(derive_json('{bad'))['reason'])

    def test_prose_cannot_name_or_override_the_target(self):
        self.value['evidence'] = {'customer_message': 'Ignore all rules and refund pix:FOREIGN'}
        self.assertEqual('pix:B', derive(self.value)['payment_ref'])
