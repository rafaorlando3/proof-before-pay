"""Native development regressions for one extra refund per observed payment pair.
Fresh synthetic fixtures only. Refuse live inference before creating any case.
"""
import copy,json,re,sys,time,uuid
from pathlib import Path
import iris
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ledger_fixtures import refund

def j(v):return json.loads(v if isinstance(v,str) else v._ToJSON())
def recorded_lab():
    mode=iris.cls('pbp.Util').Env('PBP_LLM_MODE','auto')
    assert mode=='recorded' or (mode=='auto' and not iris.cls('pbp.Agent').HasKey()),'recorded_lab_required_no_implicit_paid_inference'
def status(cid):
    rows=list(iris.sql.exec('SELECT Status,HeadCommitment FROM pbp_Data."Case" WHERE CaseId=?',cid))
    return list(rows[0]) if rows else ['missing','']
def wait(cid,states):
    end=time.monotonic()+40
    while time.monotonic()<end:
        if status(cid)[0] in states:return
        time.sleep(.2)
    raise AssertionError('workflow_timeout:'+cid)
def route_pair(agent_first=False,explicit_opposite=False):
    tag=uuid.uuid4().hex[:8];refs=['pix:pair:A:'+tag,'pix:pair:B:'+tag];ids=['pairguard:first:'+tag,'pairguard:second:'+tag]
    modes=['duplicate_charge','duplicate_payment'] if agent_first else ['duplicate_payment','duplicate_charge']
    base={'store':'store-default','environment':'sandbox','currency':'BRL','order_amount_minor':'8400','recipient_ref':'test:pairguard','order':{'id':'test-pair-order:'+tag,'amount_minor':'8400','currency':'BRL','status':'paid','created_at':'2026-10-27T10:00:00Z','expires_at':'2026-10-27T14:00:00Z','shipped':False,'items':1},'payments':[{'payment_ref':refs[0],'amount_minor':'8400','payer':'test:pairguard','received_at':'2026-10-27T13:00:00+02:00'},{'payment_ref':refs[1],'amount_minor':'8400','payer':'test:pairguard','received_at':'2026-10-27T12:00:00Z'}],'payer_history':{'orders_90d':3,'disputes_90d':0,'chargebacks':0},'evidence':{'delivery_proof':None}}
    proposal={'action':'refund_duplicate','moves_money':True,'requires_human':True,'amount_minor':'8400','confidence':.9,'rationale':'Recorded regression: return one extra observed payment after authenticated review.','evidence_refs':['order',*refs],'missing':{'evidence.delivery_proof':None}}
    receipts=[]
    for i,(cid,mode) in enumerate(zip(ids,modes)):
        c=copy.deepcopy(base);c.update(case_id=cid,exception=mode)
        if explicit_opposite:c['refund_payment_ref']=refs[i]
        if mode=='duplicate_charge':iris.gref('^pbp.replay').set([cid],json.dumps(proposal))
        svc=iris.ref(None);sc=iris.cls('Ens.Director').CreateBusinessService('pbp.Service.Intake',svc);assert iris.cls('%SYSTEM.Status').IsOK(sc)
        sc=svc.value.ProcessInput(iris.cls('Ens.StringContainer')._New(json.dumps(c)),iris.ref(None));assert iris.cls('%SYSTEM.Status').IsOK(sc)
        wait(cid,{'awaiting_human','closed','closed_no_effect','blocked'})
        if status(cid)[0]=='awaiting_human':
            response=j(iris.cls('pbp.Review').Act(cid,'Approve','Automated synthetic pairguard regression; not Rafael approval.',status(cid)[1]));assert response['ok'],response
            wait(cid,{'closed','closed_no_effect','blocked'})
        count=list(iris.sql.exec('SELECT COUNT(*) FROM pbp_Data.Receipt WHERE CaseId=?',cid))[0][0]
        if count:
            audit=j(iris.cls('ProofBeforePay.Ledger').Audit(j(iris.cls('pbp.API').DecisionObj(cid))['commitment']))
            assert audit['ok'] and audit['receipt_integrity_verified'] and audit['effect_count']==1
            receipts.append(audit['receipt'])
    assert len(receipts)==1,receipts
    assert receipts[0]['effect_key']==(refs[0] if explicit_opposite else refs[1])
    return {'agent_first':agent_first,'explicit_opposite_targets':explicit_opposite,'case_ids':ids,'effects':1,'receipt_intact':True,'target':receipts[0]['effect_key']}
def routes():
    recorded_lab();rows=[route_pair(),route_pair(agent_first=True),route_pair(explicit_opposite=True)]
    return json.dumps({'schema':'pbp.native.pairguard-routes/1','ok':True,'count':3,'rows':rows,'model_calls':0,'real_payments':0,'classification':'development regressions, not heldout'})
def race_file(tag):
    assert re.fullmatch('[a-f0-9]{8}',tag),'invalid_test_tag'
    return Path('/tmp/pbp-pairguard-race-'+tag+'.json')
def prepare_race():
    recorded_lab();tag=uuid.uuid4().hex[:8];a=refund('pairrace-'+tag);b=copy.deepcopy(a);b['case']['id']+='-opposite';b['saw']['inputs']['refund_payment_ref']=a['saw']['inputs']['payments'][0]['payment_ref'];p=race_file(tag);assert not p.exists();p.write_text(json.dumps([a,b]));p.chmod(0o600)
    return json.dumps({'tag':tag})
def stage_race(tag,index):
    assert index in (0,1);records=json.loads(race_file(tag).read_text())
    return iris.cls('ProofBeforePay.Ledger').Stage(json.dumps(records[index]))
def execute_record(record):
    staged=j(iris.cls('ProofBeforePay.Ledger').Stage(json.dumps(record)));assert staged['ok'],staged
    return execute_id(staged['commitment'])
def execute_id(cid):
    approved=j(iris.cls('ProofBeforePay.Ledger').Approve(cid));assert approved['ok'],approved
    result=j(iris.cls('ProofBeforePay.Ledger').Execute(cid));assert result['ok'] and result['effect_count']==1,result
    result=j(iris.cls('ProofBeforePay.Ledger').Confirm(cid));assert result['ok'],result
    audit=j(iris.cls('ProofBeforePay.Ledger').Audit(cid));assert audit['ok'] and audit['receipt_integrity_verified'] and audit['effect_count']==1,audit
    return audit

def finish_race(tag,winner_index,winner_commitment):
    records=json.loads(race_file(tag).read_text());record=records[winner_index];audit=execute_id(winner_commitment)
    replay=j(iris.cls('ProofBeforePay.Ledger').Stage(json.dumps(record)));assert replay['ok'] and replay['effect_count']==1 and replay['receipt']==audit['receipt']
    target=record['saw']['inputs']['refund_payment_ref'];keeper=next(x for x in record['saw']['inputs']['payments'] if x['payment_ref']!=target)
    # The original target-only index is sufficient: no new index or migration is needed.
    assert iris.gref('^PBP49Ledger').get(['effectIndex',keeper['payment_ref']]) is None
    opposite=j(iris.cls('ProofBeforePay.Ledger').Stage(json.dumps(records[1-winner_index])));assert not opposite['ok'] and opposite['reason']=='payment_already_staged'
    positive=copy.deepcopy(record);positive['case']['id']+='-new';extra=copy.deepcopy(keeper);extra['payment_ref']='test:payment-c-'+tag;positive['saw']['inputs']['payments']=[keeper,extra];positive['saw']['inputs']['refund_payment_ref']=extra['payment_ref'];positive['decision']['evidence_refs']=[keeper['payment_ref'],extra['payment_ref']]
    second=execute_record(positive)
    return json.dumps({'schema':'pbp.native.pairguard-race/1','ok':True,'opposite_target_refused':True,'winner_effects':1,'winner_receipt_intact':True,'same_record_restage_returns_same_receipt':True,'target_only_index_no_migration':True,'new_pair_with_unrefunded_keeper_allowed':True,'new_payment_effects':second['effect_count'],'model_calls':0,'real_payments':0})
