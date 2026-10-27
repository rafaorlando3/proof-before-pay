#!/usr/bin/env python3
"""Reproducible source-only candidate; does not publish or submit anything."""
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    dest = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.parent / 'pbp-source-candidate'
    assert dest != ROOT and ROOT not in dest.parents, 'output_must_be_outside_source_checkout'
    assert not git('status', '--porcelain').strip(), 'commit_or_resolve_changes_before_packaging'
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_source.py')], cwd=ROOT, check=True,
                   capture_output=True)
    revision = git('rev-parse', 'HEAD').decode().strip()
    archive = git('archive', '--format=zip', 'HEAD')
    assert archive == git('archive', '--format=zip', 'HEAD'), 'source_archive_not_reproducible'
    forbidden = {'.git', 'private', 'runtime', 'hidden', '.venv', 'node_modules', '__pycache__'}
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        assert zipped.testzip() is None
        files = {}
        for name in zipped.namelist():
            if name.endswith('/'):
                continue
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts and not forbidden.intersection(path.parts)
            assert path.name != 'gabarito.json' and not path.name.startswith('.env')
            assert path.suffix not in {'.key', '.pem', '.whl', '.gz', '.tar', '.pyc'}
            files[name] = hashlib.sha256(zipped.read(name)).hexdigest()
        assert {'LICENSE', 'README.md', 'Dockerfile', 'compose.yml', 'docs/OPEN-EXCHANGE.md'} <= files.keys()
        assert len(files) == len(git('ls-files', '-z').decode().strip('\0').split('\0'))
    digest = hashlib.sha256(archive).hexdigest()
    dest.mkdir(parents=True, exist_ok=True)
    name = 'proof-before-pay-' + revision[:12] + '-source.zip'
    (dest / name).write_bytes(archive)
    manifest = {'schema': 'pbp.source-candidate/1', 'source_revision': revision, 'archive': name,
                'archive_sha256': digest, 'source_only': True, 'reproducible_archive': True,
                'vendor_image_included': False, 'private_evaluation_data_included': False,
                'submitted_to_open_exchange': False, 'files': files}
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, sort_keys=True))


if __name__ == '__main__':
    main()
