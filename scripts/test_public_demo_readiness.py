#!/usr/bin/env python3
"""Native expiry regression only; no model, intake, state reset or role change."""
from pathlib import Path
import json
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
script = (root / "scripts/public-demo-readiness.script").read_text()
reply = subprocess.run(["docker", "compose", "exec", "-T", "iris", "iris", "session", "IRIS", "-U", "USER"],
                       input=script, cwd=root, capture_output=True, text=True, timeout=30)
matches = re.findall(r"PUBLIC_DEMO_READINESS=(\{[^\n]+\})", reply.stdout)
if reply.returncode or len(matches) != 1:
    print(json.dumps({"ok": False, "native_marker_count": len(matches), "exit": reply.returncode}))
    sys.exit(1)
result = json.loads(matches[0])
if result.get("ok") is not True or result.get("cases") != 6 or result.get("provider_calls") != 0 or result.get("native_intakes") != 0:
    print(json.dumps({"ok": False, "reason": "native_expiry_regression_failed"}))
    sys.exit(1)
print(json.dumps(result))
