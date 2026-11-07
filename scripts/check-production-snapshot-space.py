#!/usr/bin/env python3
"""Conservatively require one full source copy plus 20 percent filesystem reserve."""
from pathlib import Path
import shutil
import sys

PATHS = {
    'api': ['/srv/storage/graphdb', '/srv/storage/oldap-data', '/srv/storage/caddy', '/opt/oldap', '/etc/oldap'],
    'media': ['/data/media', '/data/oldap-ingest', '/data/oldap-import-records', '/data/oldap-exports', '/data/oldap-mobile-uploads', '/opt/oldap-mediaserver'],
}


def required_bytes(paths):
    """Count logical regular-file bytes without following directory symlinks."""
    total = 0
    for name in paths:
        root = Path(name)
        if not root.is_dir() or root.is_symlink():
            raise ValueError('Missing or symlinked source directory')
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
    return total


if __name__ == '__main__':
    role = sys.argv[1]
    size = required_bytes(PATHS[role])
    disk = shutil.disk_usage('/srv/storage' if role == 'api' else '/data')
    if disk.free < size + disk.total // 5 + 1024**3:
        raise SystemExit('Insufficient snapshot copy space and reserve')
    print('Snapshot copy-space check passed')
