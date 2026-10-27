#!/usr/bin/env python3
"""Reproducible source-only candidate; does not publish or submit anything."""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def source_archive():
    # Git's ZIP compressor/metadata varies by Git/zlib build. Read committed blobs
    # through TAR, then write an uncompressed ZIP with explicit portable metadata.
    output = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', 'HEAD'))) as source:
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as zipped:
            for member in sorted(source.getmembers(), key=lambda item: item.name):
                if member.isdir():
                    continue
                assert member.isfile(), 'non_regular_source_entry:' + member.name
                entry = zipfile.ZipInfo(member.name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = (0o100755 if member.mode & 0o111 else 0o100644) << 16
                zipped.writestr(entry, source.extractfile(member).read())
    return output.getvalue()


def main():
    dest = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.parent / 'pbp-source-candidate'
    assert dest != ROOT and ROOT not in dest.parents, 'output_must_be_outside_source_checkout'
    assert not git('status', '--porcelain').strip(), 'commit_or_resolve_changes_before_packaging'
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_source.py')], cwd=ROOT, check=True,
                   capture_output=True)
    revision = git('rev-parse', 'HEAD').decode().strip()
    archive = source_archive()
    assert archive == source_archive(), 'source_archive_not_reproducible'
    forbidden = {'.git', 'private', 'runtime', 'hidden', '.venv', 'node_modules', '__pycache__'}
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        assert zipped.testzip() is None
        files = {}
        for name in zipped.namelist():
            if name.endswith('/'):
                continue
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts and not forbidden.intersection(path.parts)
            assert path.name != 'gabarito.json'
            assert not path.name.startswith('.env') or path.name == '.env.example'
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
                'archive_format': 'canonical-uncompressed-zip/1',
                'vendor_image_included': False, 'private_evaluation_data_included': False,
                'submitted_to_open_exchange': False, 'files': files}
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, sort_keys=True))


if __name__ == '__main__':
    main()
