"""Entirely synthetic, opaque references for native effect-binding tests."""
from s0_fixtures import decision


def refund(suffix='base'):
    r=decision()
    r['case']['id']='test:case-'+suffix
    i=r['saw']['inputs']
    i.update(environment='sandbox',currency='BRL',recipient_ref='test:payer-'+suffix,
             refund_payment_ref='test:payment-b-'+suffix)
    i['payments']=[{'payment_ref':'test:payment-'+p+'-'+suffix,
                    'amount_minor':'15990','payer':'test:payer-'+suffix} for p in ('a','b')]
    r['decision']['evidence_refs']=[p['payment_ref'] for p in i['payments']]
    return r
