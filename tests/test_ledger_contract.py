import copy,json,unittest
from pbp_ledger.contract import plan_json
from ledger_fixtures import refund


class EffectBindingTests(unittest.TestCase):
    def response(self,r):return json.loads(plan_json(json.dumps(r)))

    def test_derives_all_effect_fields_from_exact_record(self):
        r=refund();p=self.response(r)
        self.assertTrue(p['ok']);self.assertEqual(p['state'],'awaiting_approval')
        self.assertEqual((p['effect_key'],p['recipient_ref'],p['amount_minor'],p['currency']),
                         ('test:payment-b-base','test:payer-base','15990','BRL'))
        self.assertFalse(p['authorizes_real_payment']);self.assertFalse(p['on_chain_verified'])

    def test_effect_boundary_rejects_twenty_adversarial_variants(self):
        def at(r,path,value):
            target=r
            for k in path[:-1]:target=target[k]
            target[path[-1]]=value
        cases=[
            (['saw','inputs','environment'],'live'),
            (['saw','inputs','recipient_ref'],'real:account'),
            (['saw','inputs','recipient_ref'],'test:other-payer'),
            (['saw','inputs','refund_payment_ref'],'test:not-evidence'),
            (['saw','inputs','refund_payment_ref'],'x'*65),
            (['saw','inputs','currency'],'USD'),
            (['limits','currency'],'USD'),
            (['decision','amount_minor'],'0'),
            (['decision','amount_minor'],'15991'),
            (['decision','amount_minor'],'100001'),
            (['decision','amount_minor'],15990),
            (['decision','amount_minor'],'0015990'),
            (['decision','action'],'credit_customer'),
            (['decision','action'],'send_payment'),
            (['case','exception'],'underpayment'),
            (['saw','inputs','payments'],[]),
            (['saw','inputs','payments',1,'payment_ref'],'test:payment-a-base'),
            (['saw','inputs','payments',1,'amount_minor'],'15991'),
            (['saw','inputs','payments',1,'payer'],'test:other'),
            (['decision','evidence_refs'],['test:payment-a-base']),
        ]
        for path,value in cases:
            with self.subTest(path=path,value=value):
                r=refund();at(r,path,value);self.assertFalse(self.response(r)['ok'])

    def test_model_cannot_waive_human_by_raising_its_own_limit(self):
        r=refund();r['limits']['autonomous_minor']='999999';r['decision']['requires_human']=False
        p=self.response(r);self.assertFalse(p['ok']);self.assertEqual(p['reason'],'human_required')

    def test_critical_missing_evidence_cannot_be_approved(self):
        for key in ('order_lookup','refund_target','payment_status'):
            r=refund();r['missing'][key]=None
            self.assertEqual(self.response(r)['reason'],'required_evidence_missing')

    def test_filling_sealed_missing_is_invalid(self):
        r=refund();r['missing']['delivery_photo']='added later'
        self.assertFalse(self.response(r)['ok'])

    def test_nonfinancial_outcomes_have_no_effect_key(self):
        for action in ('hold','escalate','request_information'):
            r=refund();r['decision'].update(action=action,moves_money=False)
            p=self.response(r);self.assertTrue(p['ok']);self.assertEqual(p['effect_key'],'')
            self.assertEqual(p['state'],'sealed');self.assertFalse(p['requires_human'])

    def test_cannot_hide_refund_as_nonfinancial(self):
        r=refund();r['decision']['moves_money']=False
        self.assertEqual(self.response(r)['reason'],'unsupported_action')

    def test_error_contains_no_private_values_or_paths(self):
        r=refund();r['saw']['inputs']['private@example.invalid']='synthetic'
        raw=plan_json(json.dumps(r));self.assertNotIn('private@example.invalid',raw)
        self.assertEqual(json.loads(raw)['reason'],'invalid_record')

    def test_duplicate_json_and_oversized_input_are_closed(self):
        for raw in ('{"prev":null,"prev":null}', ' '*32769):
            self.assertFalse(json.loads(plan_json(raw))['ok'])
