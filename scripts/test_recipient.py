#!/usr/bin/env python3
"""Licensed-IRIS destination-observation and recorded financial-path gate. No model."""
import json,re
from test_ledger import session

IMPORT='set s=##class(%SYS.Python).Import("sys")\ndo s.path.insert(0,"/opt/pbp/tests/iris")\n'
def main():
    code=IMPORT+'''set m=##class(%SYS.Python).Import("recipient_observation_probe")
if $TLEVEL'=0 halt
set result=""
TSTART
try { set result=m.run() } catch ex { write "RECIPIENT_ERROR=",ex.DisplayString(),! }
TROLLBACK
if result'="" write "RECIPIENT_PROJECTION=",result,!
'''
    probe=session(code,'RECIPIENT_PROJECTION');assert probe['accepted'] and len(probe['scenarios'])==8,probe
    ids=probe['fixture_case_ids'];assert all(re.fullmatch(r'recipient-probe:[a-z0-9:_-]{1,48}',cid) for cid in ids)
    expr='+'.join('$ISOBJECT(##class(pbp.Data.Case).Find("'+cid+'"))' for cid in ids)
    rollback=session('set result={"remaining":('+expr+')}\nwrite "RECIPIENT_ROLLBACK=",result.%ToJSON(),!','RECIPIENT_ROLLBACK');assert rollback['remaining']==0
    code=IMPORT+'set m=##class(%SYS.Python).Import("recipient_flow_smoke")\nwrite "RECIPIENT_FLOW=",m.run(),!\n'
    flow=session(code,'RECIPIENT_FLOW',240);assert flow['accepted'] and flow['cases']==3
    print(json.dumps({'schema':'pbp.native.recipient-tests/1','accepted':True,'projection':probe,'fixtures_rolled_back_and_verified':True,'recorded_flow':flow,'model_calls':0,'real_payments':0,'live_model_acceptance_tested':False},sort_keys=True))
if __name__=='__main__':main()
