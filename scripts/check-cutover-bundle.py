#!/usr/bin/env python3
"""Validate a reviewed Compose input archive before extraction into production.

Archives contain only regular files/directories relative to the Compose directory.
Links, device files, traversal and source Redis data are refused. The operator's
checksum binds the exact privately reviewed environment and configuration bytes.
"""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import tarfile


def validate(path, expected, destination=None):
    """Check archive checksum and paths without extracting or printing secrets."""
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            raise ValueError('Candidate archive checksum differs from review')
    seen = set()
    regular = set()
    with tarfile.open(path) as archive:
        for item in archive:
            name = PurePosixPath(item.name)
            if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] == 'redis-data':
                raise ValueError('Unsafe candidate member path')
            if not (item.isdir() or item.isfile()) or str(name) in seen:
                raise ValueError('Links, special files or duplicate members are forbidden')
            if item.mode & 0o7022:
                raise ValueError('Special bits and group/world-writable members are forbidden')
            if item.isdir() and not item.mode & 0o100:
                raise ValueError('Candidate directories must be traversable by their owner')
            if name.name.startswith('.env') and item.mode & 0o077:
                raise ValueError('Environment files must be private')
            if item.isfile():
                regular.add(str(name))
            if destination is not None:
                # Existing links can redirect tar extraction even if the archive
                # contains no links. Check every component, including the leaf.
                current = destination
                for part in (None, *name.parts):
                    if part is not None:
                        current = current/part
                    if current.is_symlink():
                        raise ValueError('Candidate destination contains a symlink')
            seen.add(str(name))
    if not {'docker-compose.yml', '.env'}.issubset(regular):
        raise ValueError('A complete reviewed Compose selection and environment are required')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('sha256')
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    validate(args.archive, args.sha256, args.destination)
