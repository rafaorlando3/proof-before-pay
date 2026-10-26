"""Check imported S0 seal bytes and prevent private build inputs entering Git."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = json.loads((root / 'docs/PROVENANCE.json').read_text())
for name, expected in source['seal_files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
patterns = [r'sk-or-v1-[A-Za-z0-9_-]{30,}', r'sk-proj-[A-Za-z0-9_-]{30,}', r'sk-svcacct-[A-Za-z0-9_-]{30,}', r'AIza[0-9A-Za-z_-]{35}', r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{40,}', r'sk-ant-[A-Za-z0-9_-]{30,}', r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'AKIA[0-9A-Z]{16}']
for name in subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0'):
    if not name:
        continue
    text = (root / name).read_text(errors='replace')
    assert not any(re.search(pattern, text) for pattern in patterns), 'possible_secret:' + name
    assert not name.endswith(('.key','.pem','.whl','.tar','.tar.gz','.pyc')), name
    assert not any(p in {'.venv','node_modules','__pycache__','private','runtime'} for p in Path(name).parts), name
    assert not Path(name).name.startswith('.env') or Path(name).name=='.env.example', name
print(json.dumps({'ok':True,'S0_seal_files_unchanged':len(source['seal_files']),'private_build_inputs_tracked':False}))
