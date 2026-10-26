"""Actual HTTP contract test against an authenticated, private synthetic lab.
No model key or public endpoint is required. The optional local proxy supplies the disposable lab login.
"""
import base64, copy, json, os, sys, time, uuid
from pathlib import Path
from urllib.parse import urlparse, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE=os.environ.get('PBP_TEST_BASE_URL','http://127.0.0.1:8878').rstrip('/')
assert urlparse(BASE).hostname in {'127.0.0.1','localhost','::1'}, 'private_loopback_lab_required'

def request(path, data=None, custom=True):
    headers={}
    if custom:headers.update({'Content-Type':'application/json','X-PBP-Request':'1'})
    user=os.environ.get('PBP_TEST_USER');password=os.environ.get('PBP_TEST_PASSWORD')
    if user and password:headers['Authorization']='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    body=json.dumps(data).encode() if data is not None else None
    req=Request(BASE+'/pbp/api'+path,data=body,headers=headers,method='POST' if data is not None else 'GET')
    try:r=urlopen(req,timeout=30)
    except HTTPError as e:r=e
    result=json.loads(r.read())
    return r.code,result

def wait_case(cid,statuses,seconds=75):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        status,data=request('/cases/'+quote(cid,safe=''))
        if status==200 and data['case']['status'] in statuses:return data
        time.sleep(.6)
    raise AssertionError('case_did_not_reach_expected_state:'+cid)

def seed_case():
    data=json.loads((Path(__file__).parents[1]/'fixtures/cases/pix-0001.json').read_text())
    tag=uuid.uuid4().hex[:10]
    data['case_id']='ui-refund:'+tag
    for p in data['payments']:p['payment_ref']+=':'+tag
    status,response=request('/cases',data)
    assert status==202 and response['ok'],response
    detail=wait_case(data['case_id'],{'awaiting_human'})
    return data,detail

def run():
    checks=[]
    def check(name,condition,detail=''):
        assert condition,name+':'+str(detail)
        checks.append(name)
    status,health=request('/health')
    check('health_production_running',status==200 and health['production_running'])
    check('recorded_not_live_proof',health['mode']=='recorded' and health['last_live_call_ok'] is False)
    status,me=request('/whoami')
    check('authenticated_test_reviewer',status==200 and bool(me['can_review']) and me['user'].startswith('PBP'))
    payload,detail=seed_case();cid=payload['case_id'];commit=detail['case']['commitment']
    check('awaiting_native_reviewer',detail['case']['status']=='awaiting_human')
    check('sealed_before_permit',len(detail['seals'])==1 and not detail['permit'] and not detail['receipt'])
    status,pending=request('/review')
    check('task_discoverable',status==200 and any(v['case_id']==cid and v['task_id'] for v in pending['pending']))
    status,blocked=request('/review/'+quote(cid,safe=''),{'action':'Approve','note':'synthetic HTTP check','commitment':commit},custom=False)
    check('csrf_header_required',status==400 and blocked['reason']=='same_origin_header_required',blocked)
    status,blocked=request('/review/'+quote(cid,safe=''),{'action':'Approve','note':'','commitment':'0'*64})
    check('stale_displayed_hash_denied',status==409 and blocked['reason']=='reviewed_version_changed',blocked)
    status,blocked=request('/review/'+quote(cid,safe=''),{'action':'Approve','note':''})
    check('missing_displayed_hash_denied',status==409 and blocked['reason']=='expected_commitment_required',blocked)
    status,result=request('/review/'+quote(cid,safe=''),{'action':'Approve','note':'Automated synthetic reviewer test; not Rafael approval.','commitment':commit})
    check('review_in_authenticated_http_session',status==200 and result['ok'] and result['user']==me['user'],result)
    detail=wait_case(cid,{'closed','blocked'})
    check('workflow_closed_after_effect',detail['case']['status']=='closed',detail['case']['reason'])
    status,ledger=request('/ledger/'+commit)
    check('readback_confirms_one_effect',status==200 and ledger['state']=='confirmed' and ledger['effect_count']==1,ledger)
    check('receipt_identity_is_http_reviewer',ledger['approved_by']==me['user'])
    receipt=ledger['receipt']
    check('seal_authorization_effect_order',receipt['sealed_seq']<receipt['authorized_seq']<receipt['executed_seq'])
    check('no_real_payment_or_chain_claim',ledger['authorizes_real_payment'] is False and ledger['on_chain_verified'] is False)
    check('permit_consumed',detail['permit']['status']=='consumed')
    check('receipt_projection_verified',detail['receipt']['verification']=='intact')
    check('timeline_contains_review_and_effect',len(detail['events'])>=8 and any(e['kind']=='ledger_authorized' for e in detail['events']))
    check('approval_record_chained',len(detail['seals'])==2 and detail['seals'][1]['prev']==commit)
    status,seal=request('/seals/'+commit)
    check('local_verification_labelled',status==200 and seal['verification']['state']=='intact' and seal['verification']['on_chain_verified'] is False)
    altered=copy.deepcopy(seal['record']);altered['decision']['amount_minor']='1'
    status,verdict=request('/seals/'+commit+'/verify',{'record':altered})
    check('edited_copy_tampered',status==200 and verdict['state']=='tampered',verdict)
    status,verdict=request('/seals/'+commit+'/verify',{'record':seal['record']})
    check('stored_record_still_intact',status==200 and verdict['state']=='intact',verdict)
    status,again=request('/cases',payload)
    check('retry_intake_accepted_idempotently',status==202 and again['ok'])
    time.sleep(2)
    status,again=request('/ledger/'+commit)
    check('retry_keeps_same_receipt_and_count',again['effect_count']==1 and again['receipt']==receipt)
    status,replay=request('/cases/'+quote(cid,safe='')+'/replay')
    check('forensic_replay_matches_seal',status==200 and replay['steps'][0]['record']==seal['record'])
    status,stats=request('/stats')
    check('stats_case_sensitive_keys_normalized',status==200 and 'closed' in stats['cases_by_status'] and 'rules' in stats['decisions_by_source'])
    # A missing tape must fail closed without fabricating an inference or a tool call.
    hard=json.loads((Path(__file__).parents[1]/'fixtures/cases/pix-0005.json').read_text())
    hard['case_id']='missing-tape:'+uuid.uuid4().hex[:10]
    status,reply=request('/cases',hard)
    check('ambiguous_case_received',status==202)
    hard_detail=wait_case(hard['case_id'],{'awaiting_human','blocked'})
    check('missing_replay_fails_closed',hard_detail['case']['status']=='awaiting_human' and not hard_detail['permit'] and not hard_detail['receipt'])
    status,hard_replay=request('/cases/'+quote(hard['case_id'],safe='')+'/replay')
    check('missing_tape_not_fabricated_as_tools',status==200 and len(hard_replay['tool_calls'])==0)
    check('missing_tape_reason_visible','no_recorded_decision_for_case' in hard_replay['decision']['rationale'])
    recorded=json.loads((Path(__file__).parents[1]/'fixtures/cases/pix-0005.json').read_text())
    status,reply=request('/cases',recorded)
    wait_case(recorded['case_id'],{'awaiting_human','closed','rejected'})
    status,tape=request('/cases/'+recorded['case_id']+'/replay')
    check('recorded_forensic_tool_outputs_retrievable',status==200 and len(tape['tool_calls'])==5)
    check('replay_snapshot_covers_five_tools',len(tape['steps'][0]['record']['saw']['tools'])==5)
    status,reply=request('/review/'+quote(hard['case_id'],safe=''),{'action':'Reject','note':'Synthetic missing-tape test closed without effect.','commitment':hard_detail['case']['commitment']})
    check('ambiguous_case_rejected',status==200 and reply['ok'])
    rejected=copy.deepcopy(payload);rejected['case_id']='guard:'+uuid.uuid4().hex[:10];rejected['environment']='production'
    status,reply=request('/cases',rejected)
    check('production_input_refused',status==400 and not reply['ok'])
    return {'schema':'pbp.http.workflow-tests/1','ok':True,'count':len(checks),'checks':checks,'case_id':cid,'decision_commitment':commit,'test_reviewer':me['user'],'live_inference_tested':False}

if __name__=='__main__':
    if '--seed' in sys.argv:
        payload,detail=seed_case();print(json.dumps({'case_id':payload['case_id'],'commitment':detail['case']['commitment']}))
    else:print(json.dumps(run(),sort_keys=True))
