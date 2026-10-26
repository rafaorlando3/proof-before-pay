#!/usr/bin/env python3
"""Compile and test the actual IRIS bridge; fail if a result marker is absent."""
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with (root / 'scripts/iris-test.script').open() as source:
    result = subprocess.run(['docker', 'compose', 'exec', '-T', 'iris', 'iris', 'session', 'IRIS', '-U', 'USER'], stdin=source, capture_output=True, text=True, cwd=root, timeout=90)
compile_ok = bool(re.search(r'PBP_COMPILE=1 ERRORS=0', result.stdout))
smoke = re.findall(r'PBP_SMOKE=(\{[^\n]+\})', result.stdout)
if result.returncode or not compile_ok or len(smoke) != 1:
    print(json.dumps({'ok': False, 'compile_ok': compile_ok, 'smoke_markers': len(smoke), 'exit': result.returncode}))
    print((result.stdout + result.stderr)[-4000:], file=sys.stderr)
    sys.exit(1)
value = json.loads(smoke[0])
assert value['ok'] is True and value['count'] >= 12
print(json.dumps({'compile_ok': True, **value}, sort_keys=True))
