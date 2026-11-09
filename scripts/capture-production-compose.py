#!/usr/bin/env python3
"""Capture resolved, image-pinned source Compose inputs without starting services.

Run on each production host before drain. The private output contains environment
secrets and must remain outside Git. Reject bind mounts absent from the planned
snapshot; the SIPI cache is the only disposable named-volume exception.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

DIRECTORIES = {'api': '/opt/oldap/compose', 'media': '/opt/oldap-mediaserver/compose'}
ROOTS = {
    'api': ['/srv/storage/graphdb', '/srv/storage/oldap-data', '/srv/storage/caddy', '/opt/oldap', '/etc/oldap'],
    'media': ['/data/media', '/data/oldap-ingest', '/data/oldap-import-records', '/data/oldap-exports', '/data/oldap-mobile-uploads', '/opt/oldap-mediaserver'],
}
NAMES = {
    'api': ['caddy', 'oldap-api', 'redis', 'graphdb', 'compose-archive-writer-1', 'oldap-app', 'fasnachts-page', 'compose-salsah-2-1'],
    'media': ['oldap-media-caddy', 'oldap-mediahelper', 'oldap-ingest-worker', 'oldap-export-worker', 'oldap-mobile-media-worker', 'oldap-imageserver'],
}


def pin_source(role, configuration, containers):
    """Pin only the inventoried services and require snapshot coverage of binds."""
    selected = {}
    if {row['Name'].lstrip('/') for row in containers} != set(NAMES[role]):
        raise ValueError('Source inventory differs from the approved topology')
    for row in containers:
        name = row['Config']['Labels']['com.docker.compose.service']
        if name in selected:
            raise ValueError('Duplicate Compose service')
        service = configuration['services'][name]
        for mount in service.get('volumes', []):
            if mount['type'] == 'volume' and role == 'media' and mount['target'] == '/var/cache/sipi':
                continue
            if mount['type'] != 'bind':
                raise ValueError('Unexpected source storage type')
            source = Path(mount['source'])
            if not source.exists() or source.is_symlink():
                raise ValueError('Missing or symlinked source bind')
            if not any(source.resolve().is_relative_to(Path(root).resolve()) for root in ROOTS[role]):
                raise ValueError('Source bind is not covered by the snapshot: '+str(source))
        service['image'] = row['Image']
        service['pull_policy'] = 'never'
        selected[name] = service
    configuration['services'] = selected
    return configuration


def capture(role, directory):
    """Write a new private resolved configuration; never print environment data."""
    os.umask(0o077)
    environment = {key: value for key, value in os.environ.items() if not key.startswith('COMPOSE_')}
    configuration = json.loads(subprocess.check_output(
        ['docker', 'compose', '--profile', '*', 'config', '--format', 'json'],
        cwd=DIRECTORIES[role], env=environment, stderr=subprocess.PIPE))
    rows = json.loads(subprocess.check_output(['docker', 'inspect', *NAMES[role]], stderr=subprocess.PIPE))
    configuration = pin_source(role, configuration, rows)
    with (directory/'source-compose.json').open('x') as stream:
        json.dump(configuration, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['api', 'media'])
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    capture(args.role, args.directory)
