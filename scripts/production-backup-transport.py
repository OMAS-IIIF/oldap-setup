#!/usr/bin/env python3
"""Confirm and retire immutable production transport files, never live data.

Executed over pinned SSH with a JSON request on stdin. Roots and archive names
are fixed here. Receipts survive deletion for audit and interrupted-job retries.
Only automatic snapshot IDs are eligible; manual checkpoints are never pruned.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ID_PATTERN = r'[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}'
ROOTS = {'api': Path('/srv/storage'), 'media': Path('/data')}
REPOSITORY_ID = '8fb098bbaddd2dd2e8726c667df6d6d318ca3c07abe8f1a4523a7bdc6310b55f'


def validate_receipt(receipt):
    """Require a verified Borg identity and the exact fixed production pair."""
    manifest = receipt['manifest']
    sid = manifest['snapshot_id']
    if not re.fullmatch(ID_PATTERN, sid) or manifest.get('status') != 'offline-compared':
        raise ValueError('Invalid production snapshot identity')
    if receipt.get('repository_id') != REPOSITORY_ID or receipt.get('archive') != 'production-' + sid:
        raise ValueError('Unexpected Borg repository/archive')
    if not re.fullmatch('[0-9a-f]{64}', receipt.get('archive_id', '')) or not receipt.get('verified_at'):
        raise ValueError('Missing Borg verification')
    for role, root in ROOTS.items():
        entry = manifest[role]
        if entry.get('path') != f'{root}/oldap-jena-snapshot-{sid}/{role}.tar':
            raise ValueError('Unexpected transport path')
        if type(entry.get('bytes')) is not int or entry['bytes'] <= 0:
            raise ValueError('Invalid transport length')
        if not re.fullmatch('[0-9a-f]{64}', entry.get('sha256', '')):
            raise ValueError('Invalid transport digest')
    if manifest['media'].get('host') != 'dhlab-iii.dhlab.unibas.ch':
        raise ValueError('Unexpected media host')
    return sid


def read_json(path):
    """Read only ordinary files; refuse symlinks before any destructive action."""
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected ordinary JSON file')
    return json.loads(path.read_text())


def atomic_json(path, value):
    """Publish a private durable receipt by atomic replacement."""
    descriptor, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)



def snapshot_directory(role, sid):
    """Resolve only the fixed auto-ID namespace, without following links."""
    if not re.fullmatch(ID_PATTERN, sid):
        raise ValueError('Not an automatic snapshot ID')
    path = ROOTS[role] / ('oldap-jena-snapshot-' + sid)
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Invalid snapshot directory')
    return path


def verify_archive(path, entry):
    """Verify bytes before acknowledging or deleting an immutable transport."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size != entry['bytes']:
        raise ValueError('Transport type/length mismatch')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != entry['sha256']:
            raise ValueError('Transport digest mismatch')


def operate(role, request):
    """List receipts, acknowledge a pair, or remove only a verified tar file.

    The receiver compares both inventories and retains three pairs before asking
    either host to retire a tar. Missing tar on retry is safe only with the same
    receipt; unknown or unacknowledged files are never removed.
    """
    action = request['action']
    if action == 'inventory':
        found = {}
        for path in ROOTS[role].glob('oldap-jena-snapshot-*'):
            sid = path.name.removeprefix('oldap-jena-snapshot-')
            if not re.fullmatch(ID_PATTERN, sid):
                continue
            snapshot_directory(role, sid)
            marker = path / 'received.json'
            if not marker.exists() and not marker.is_symlink():
                continue
            receipt = read_json(marker)
            if validate_receipt(receipt) != sid:
                raise ValueError('Receipt directory mismatch')
            if role == 'api' and read_json(path / 'ready.json') != receipt['manifest']:
                raise ValueError('Receipt differs from producer publication')
            found[sid] = receipt
        return found
    receipt = request['receipt']
    sid = validate_receipt(receipt)
    path = snapshot_directory(role, sid)
    archive = path / (role + '.tar')
    marker = path / 'received.json'
    if role == 'api' and read_json(path / 'ready.json') != receipt['manifest']:
        raise ValueError('Receipt differs from producer publication')
    if action == 'acknowledge':
        if marker.exists():
            if read_json(marker) != receipt:
                raise ValueError('Conflicting acknowledgement')
        else:
            verify_archive(archive, receipt['manifest'][role])
            atomic_json(marker, receipt)
    elif action in ('validate-retirement', 'retire'):
        if read_json(marker) != receipt:
            raise ValueError('Unconfirmed retirement')
        if archive.exists() or archive.is_symlink():
            verify_archive(archive, receipt['manifest'][role])
            if action == 'retire':
                archive.unlink()
        # Keep directory, producer metadata and receipt as a tiny audit record.
    else:
        raise ValueError('Unknown transport action')
    return {'snapshot_id': sid, 'action': action}


if __name__ == '__main__':
    os.umask(0o077)
    print(json.dumps(operate(sys.argv[1], json.load(sys.stdin))))
