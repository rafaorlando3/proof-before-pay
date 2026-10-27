#!/usr/bin/env python3
"""Licensed-IRIS recorded-mode route and concurrent Stage regression gate."""
import concurrent.futures,json
from test_ledger import session

IMPORT='set s=##class(%SYS.Python).Import("sys")\ndo s.path.insert(0,"/opt/pbp/tests/iris")\nset m=##class(%SYS.Python).Import("pairguard_smoke")\n'
def call(expression,marker,timeout=160):return session(IMPORT+'write "'+marker+'=",'+expression+',!\n',marker,timeout)
def main():
    routes=call('m.routes()','PAIR_ROUTES',300);assert routes['ok'] and routes['count']==3
    tag=call('m."prepare_race"()','PAIR_PREP')['tag']
    def stage(index):return call('m."stage_race"("'+tag+'",'+str(index)+')','PAIR_STAGE')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(stage,[0,1]))
    winners=[i for i,r in enumerate(rows) if r.get('ok') is True];assert len(winners)==1,rows
    assert rows[1-winners[0]]['reason']=='payment_already_staged',rows
    i=winners[0];race=call('m."finish_race"("'+tag+'",'+str(i)+',"'+rows[i]['commitment']+'")','PAIR_RACE');assert race['ok']
    print(json.dumps({'schema':'pbp.native.pairguard-tests/1','ok':True,'routes':routes,'concurrent_IRIS_Stage_sessions':2,'stage_successes':1,'race':race,'live_inference_tested':False},sort_keys=True))
if __name__=='__main__':main()
