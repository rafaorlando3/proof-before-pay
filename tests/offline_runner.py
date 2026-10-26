"""Offline test entrypoint. Network and child processes are denied before imports."""
import json
import pathlib
import socket
import subprocess
import sys
import unittest
import urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'python'),str(root/'tests')]
attempts=[]
def denied(*args,**kwargs):
    attempts.append('forbidden_io')
    raise RuntimeError('offline_io_denied')
socket.socket=denied;socket.create_connection=denied
urllib.request.urlopen=denied;subprocess.Popen=denied
suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_*.py')
result=unittest.TestResult();suite.run(result)
value={'schema':'pbp.witness.offline-tests/1','ok':result.wasSuccessful() and not attempts,'tests':result.testsRun,'failures':[t.id()for t,_ in result.failures],'errors':[t.id()for t,_ in result.errors],'forbidden_IO_attempts':len(attempts),'Solana_RPC_requests':0,'IRIS_executed':False,'Witness_compiled':False,'interop_verified':False}
print(json.dumps(value,sort_keys=True));sys.exit(0 if value['ok'] else 1)
