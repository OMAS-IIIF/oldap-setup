#!/usr/bin/env python3
"""Persist the irreversible public-write boundary, or refuse automatic rollback.

Use a private existing cutover directory on durable storage. The marker is written
and fsynced before enabling any target writer/ingress. Presence alone fences old
snapshot rollback, including an interrupted or partial opening. Never delete it
as a way to permit rollback; post-opening recovery needs reconciliation.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat


def boundary(directory, action, acceptance_sha256=None):
    """Check rollback admissibility or atomically create a durable opening intent.

    Args:
        directory: Existing private cutover directory on the API host.
        action: check-rollback or mark-opening.
        acceptance_sha256: Exact reviewed private acceptance report checksum.

    Raises:
        ValueError: Directory permissions or the supplied checksum are invalid.
        FileExistsError: Opening may already have happened; rollback is fenced.
    """
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.geteuid():
        raise ValueError('Require an owned private directory, not a symlink')
    marker = directory/'target-opened.json'
    if marker.exists() or marker.is_symlink():
        raise FileExistsError('Target writes may exist; automatic GraphDB rollback is forbidden')
    if action == 'check-rollback':
        return
    if action != 'mark-opening' or not acceptance_sha256 or len(acceptance_sha256) != 64 or any(c not in '0123456789abcdef' for c in acceptance_sha256):
        raise ValueError('Require the reviewed acceptance report SHA-256')
    # O_EXCL prevents concurrent operators from silently overwriting the boundary.
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'state':'target-writes-possible', 'created_at':datetime.now(timezone.utc).isoformat(),
                   'acceptance_sha256':acceptance_sha256}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('action', choices=['check-rollback', 'mark-opening'])
    parser.add_argument('--acceptance-sha256')
    args = parser.parse_args()
    boundary(args.directory, args.action, args.acceptance_sha256)
