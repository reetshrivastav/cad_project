"""Verify the retained native archive or a lab directory without unpickling."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/evidence/native_model_20261018'
METADATA = ROOT / 'reports/evidence/native_burst_20261018/lab_native_v1_metadata.json'


def verify(archive=None, model_dir=None):
    metadata = json.loads(METADATA.read_text())
    expected = metadata['artifact_sha256']
    names = set(expected) | {'model_metadata.json'}
    if model_dir is not None:
        payloads = {name: (Path(model_dir) / name).read_bytes() for name in names}
    else:
        manifest = json.loads((EVIDENCE / 'archive_manifest.json').read_text())
        archive = Path(archive) if archive else EVIDENCE / manifest['archive']
        if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['archive_sha256']:
            raise ValueError('Archive checksum differs from retained manifest')
        with tarfile.open(archive, 'r:gz') as handle:
            members = handle.getmembers()
            prefix = 'models/lab_native_v1/'
            files = [member for member in members if member.isfile()]
            if (any(not (m.isfile() or m.isdir()) for m in members)
                    or any(m.isdir() and m.name.rstrip('/') != prefix.rstrip('/') for m in members)
                    or len(files) != len(names)
                    or {m.name for m in files} != {prefix + name for name in names}):
                raise ValueError('Unexpected archive members; archive was not extracted')
            payloads = {name: handle.extractfile(prefix + name).read() for name in names}
    hashes = {name: hashlib.sha256(payloads[name]).hexdigest() for name in expected}
    if hashes != expected:
        raise ValueError('Native artifact hash mismatch')
    if json.loads(payloads['model_metadata.json']) != metadata:
        raise ValueError('Native metadata differs from recorded experiment')
    return {'verified_artifacts': hashes, 'metadata_matches': True,
            'deserialized_models': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--archive', type=Path)
    source.add_argument('--model-dir', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.archive, args.model_dir), indent=2))
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f'Verification failed: {exc}\n')


if __name__ == '__main__':
    main()
