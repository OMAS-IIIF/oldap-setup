#!/usr/bin/env python3
"""Read-only source/target lifecycle gates for the two production hosts.

No environment values or raw Docker metadata are printed. Run on each host before
snapshot, private acceptance or source recovery. This validates lifecycle only;
coordination, archive checksums and domain acceptance are separate mandatory gates.
"""
import argparse
import json
import subprocess

API = {'caddy', 'oldap-api', 'redis', 'graphdb', 'compose-archive-writer-1',
       'oldap-app', 'fasnachts-page', 'compose-salsah-2-1'}
MEDIA = {'oldap-media-caddy', 'oldap-mediahelper', 'oldap-ingest-worker',
         'oldap-export-worker', 'oldap-mobile-media-worker', 'oldap-imageserver'}
STATIC = {'oldap-app', 'fasnachts-page', 'compose-salsah-2-1'}
TARGET = {'compose-oldap-jena-1', 'compose-oldap-jena-identity-1'}


def inspect_containers():
    """Return only container identities, image IDs and lifecycle state."""
    names = subprocess.check_output(['docker', 'ps', '-aq'], text=True).split()
    if not names:
        raise RuntimeError('No source containers found')
    rows = json.loads(subprocess.check_output(['docker', 'inspect', *names]))
    return {row['Name'].lstrip('/'): {'id': row['Id'], 'image': row['Image'],
                                    'state': row['State']} for row in rows}


def validate(role, phase, containers):
    """Reject missing services, unexpected running writers or unclean shutdown.

    A frozen media source includes the image server: close every possible media
    writer, not merely the upload routes. Stopped unrelated retained containers
    are allowed; unexpected running containers require inventory review.
    """
    required = API if role == 'api' else MEDIA
    if phase == 'target-private' and role == 'api':
        required = (API - {'compose-archive-writer-1'}) | TARGET
        running = TARGET | {'oldap-api', 'redis'}
    elif phase == 'online':
        running = required
    else:
        running = set()
    if not required.issubset(containers):
        raise ValueError('Required containers are missing')
    actual = {name for name, row in containers.items() if row['state']['Running']}
    if actual != running:
        raise ValueError('Unexpected running or stopped containers')
    for name in required - running:
        state = containers[name]['state']
        if state.get('OOMKilled') or state.get('Restarting') or state.get('ExitCode') not in {0, 130, 143}:
            raise ValueError('Unclean container shutdown: '+name)
    if phase == 'target-private' and role == 'api' and containers.get('compose-archive-writer-1', {}).get('state', {}).get('Running'):
        raise ValueError('Source writer coordinator still running')
    return {'role': role, 'phase': phase, 'status': 'passed',
            'containers': {name: {'id': containers[name]['id'], 'image': containers[name]['image']}
                           for name in sorted(required)}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['api', 'media'])
    parser.add_argument('phase', choices=['online', 'frozen', 'target-private'])
    args = parser.parse_args()
    print(json.dumps(validate(args.role, args.phase, inspect_containers()), sort_keys=True))
