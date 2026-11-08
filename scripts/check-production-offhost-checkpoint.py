#!/usr/bin/env python3
"""Require a verified encrypted off-host copy of this exact frozen source pair.

The trusted receiver report is copied over verified SSH into the private root-
owned checkpoint. This binds its result to every source artifact and manifest;
it does not claim to independently execute Borg from the production server.
"""
import hashlib
import json
from pathlib import Path
import sys

REPOSITORY_ID = '8fb098bbaddd2dd2e8726c667df6d6d318ca3c07abe8f1a4523a7bdc6310b55f'


def validate(manifest_bytes, receipt):
    """Reject stale, incomplete or unrelated recovery evidence before replacement."""
    manifest = json.loads(manifest_bytes)
    sid = manifest['snapshot_id']
    if manifest['status'] != 'source-frozen' or receipt.get('status') != 'passed' or receipt.get('snapshot_id') != sid:
        raise ValueError('Need exact accepted frozen checkpoint')
    if receipt.get('repository_id') != REPOSITORY_ID or receipt.get('archive') != 'cutover-' + sid:
        raise ValueError('Unexpected recovery repository/archive')
    paths = {
        f'/srv/storage/oldap-cutover-{sid}/api.tar': 'api.tar',
        f'/data/oldap-cutover-{sid}/media.tar': 'media.tar',
        f'/srv/storage/oldap-cutover-{sid}/source.trig': 'source.trig',
        f'/srv/storage/oldap-cutover-{sid}/source-compose.json': 'api-source-compose.json',
        f'/data/oldap-cutover-{sid}/source-compose.json': 'media-source-compose.json',
    }
    artifacts = manifest['artifacts']
    if len(artifacts) != len(paths) or {item['path'] for item in artifacts} != set(paths):
        raise ValueError('Unexpected frozen artifact set')
    for item in artifacts:
        expected = {'bytes': item['size'], 'sha256': item['checksum']}
        if receipt['files'].get(paths[item['path']]) != expected:
            raise ValueError('Off-host artifact differs from frozen source')
    if receipt['files'].get('manifest.json') != {'bytes': len(manifest_bytes), 'sha256': hashlib.sha256(manifest_bytes).hexdigest()}:
        raise ValueError('Off-host manifest differs from frozen source')
    return {'status': 'passed', 'snapshot_id': sid, 'source_artifacts_verified': len(paths)}


if __name__ == '__main__':
    checkpoint = Path(sys.argv[1])
    for path in (checkpoint, checkpoint/'manifest.json', checkpoint/'offhost-acceptance.json'):
        if path.is_symlink():
            raise ValueError('Checkpoint evidence must not be symlinked')
    print(json.dumps(validate((checkpoint/'manifest.json').read_bytes(), json.loads((checkpoint/'offhost-acceptance.json').read_text()))))
