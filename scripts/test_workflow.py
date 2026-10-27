#!/usr/bin/env python3
"""Private native runtime gate. Run only in the synthetic replay lab.

A successful IRIS session or RunTest status alone does not prove tests passed.
This runner verifies the framework's result and the independent E2E JSON marker.
"""
import json
import re
import subprocess
from pathlib import Path
from test_ledger import session

ROOT=Path(__file__).resolve().parents[1]

def main():
    cmd=['docker','compose','exec','-T','iris','iris','session','IRIS','-U','USER']
    unit='''set ^UnitTestRoot="/opt/pbp/cls"
set sc=##class(%UnitTest.Manager).RunTest("pbp/Test","/noload/nodelete")
write "PBP_UNIT_SC=",$system.Status.IsOK(sc),!
halt
'''
    p=subprocess.run(cmd,input=unit,capture_output=True,text=True,errors='replace',cwd=ROOT,timeout=110)
    text=p.stdout+p.stderr
    passed=re.findall(r'^      (Test\w+) passed\s*$', text, re.M)
    assert p.returncode==0 and 'All PASSED' in text and 'PBP_UNIT_SC=1' in text, text[-5000:]
    assert not re.search(r'FAILED|<THROW>|<UNDEFINED>|\(failed\)|AssertSkipped', text),text[-5000:]
    assert len(passed)>=31 and {"TestReceiptProjectionTamperIsVisible","TestToolCaseIsolation","TestGeminiPrivateBaseConfiguration","TestDuplicateOffsetsSelectTheSameInstantRegardlessOfArrayOrder","TestDuplicateAmbiguousTimeDoesNotInventATarget"} <= set(passed), passed
    source='''set s=##class(%SYS.Python).Import("sys")
do s.path.insert(0,"/opt/pbp/tests/iris")
set m=##class(%SYS.Python).Import("production_smoke")
set result=m.run("/opt/pbp")
write "E2E=",result,!
'''
    result=session(source,'E2E',timeout=180)
    assert result['ok'] is True and result['count']>=48,result
    assert {'review_note_sealed','rejection_note_sealed'} <= set(result['checks']),result
    adversarial_source='set s=##class(%SYS.Python).Import("sys")\ndo s.path.insert(0,"/opt/pbp/tests/iris")\nset m=##class(%SYS.Python).Import("adversarial_smoke")\nset result=m.run()\nwrite "ADVERSARIAL=",result,!\n'
    adversarial=session(adversarial_source,'ADVERSARIAL',timeout=90)
    assert adversarial['all_safe'] and adversarial['count']==3,adversarial
    print(json.dumps({'schema':'pbp.native.workflow-tests/1','ok':True,'adversarial':adversarial,'native_unit_methods':len(passed),'unit_method_names':passed,'e2e':result,'live_inference_tested':False},sort_keys=True))

if __name__=='__main__':main()
