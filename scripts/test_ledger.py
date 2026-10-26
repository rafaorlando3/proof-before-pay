#!/usr/bin/env python3
"""Compile in licensed IRIS, then test storage and race independent IRIS sessions.

Requires the private EAP runtime already running. Public CI runs only the offline
contract tests; absence of this marker must never count as a native runtime pass.
"""
import concurrent.futures,json,re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CMD=['docker','compose','exec','-T','iris','iris','session','IRIS','-U','USER']

def session(source,marker,timeout=90):
    p=subprocess.run(CMD,input=source+'\nhalt\n',capture_output=True,text=True,errors='replace',cwd=ROOT,timeout=timeout)
    values=re.findall(re.escape(marker)+r'=(\{[^\n]+\})',p.stdout)
    if p.returncode or len(values)!=1:
        raise RuntimeError(json.dumps({'marker':marker,'exit':p.returncode,'output':(p.stdout+p.stderr)[-3000:]}))
    return json.loads(values[0])


def action(method,commitment):
    assert re.fullmatch('[a-f0-9]{64}',commitment)
    assert method in {'Execute','Confirm','Read','Approve'}
    return session(f'write "ACTION=",##class(ProofBeforePay.Ledger).{method}("{commitment}"),!','ACTION')


def main():
    source='''set sc=$system.OBJ.LoadDir("/opt/pbp/cls/ProofBeforePay","ck",.errors)
if $system.Status.IsError(sc) do $system.Status.DisplayError(sc) halt
set sc=$system.OBJ.Load("/opt/pbp/tests/iris/LedgerProbe.cls","ck")
if $system.Status.IsError(sc) do $system.Status.DisplayError(sc) halt
set s=##class(%SYS.Python).Import("sys")
do s.path.insert(0,"/opt/pbp/tests/iris")
set m=##class(%SYS.Python).Import("ledger_smoke")
write "LEDGER=",m.run(),!
'''
    result=session(source,'LEDGER')
    assert result['ok'] and result['count']>=30
    c=result['concurrency_commitment']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        attempts=list(pool.map(lambda _:action('Execute',c),range(12)))
    assert all(v['ok'] for v in attempts),attempts
    receipts=[v['receipt'] for v in attempts]
    assert all(v==receipts[0] for v in receipts)
    assert all(v['effect_count']==1 for v in attempts)
    assert sum(not v['replayed'] for v in attempts)==1
    final=action('Confirm',c)
    assert final['state']=='confirmed' and final['effect_count']==1
    # NEW process: the original confirmed case must still be durable and intact.
    read=action('Read',result['confirmed_commitment'])
    assert read['state']=='confirmed' and read['effect_count']==1
    value={**result,'concurrent_IRIS_sessions':12,'max_parallel_sessions':3,
           'race_effect_count':final['effect_count'],'identical_receipts':True,
           'readback_confirmed':True,'cross_process_persistence':True}
    print(json.dumps(value,sort_keys=True))

if __name__=='__main__':main()
