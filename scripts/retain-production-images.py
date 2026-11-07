#!/usr/bin/env python3
"""Retain exact running production image bytes locally without changing services.

The destination must be new, private and outside Git. SSH uses existing trust and
agent credentials. A completion manifest is written only after Docker load/ID
verification and unchanged source-container checks. This is image retention,
not a coordinated database/media backup. Local Docker load does not start images.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

HOSTS = {'api': 'dhlab-oldap.dhlab.unibas.ch', 'media': 'dhlab-iii.dhlab.unibas.ch'}
EXPECTED = {
    'api': {'fasnachts-page', 'oldap-api', 'compose-salsah-2-1', 'oldap-app',
            'compose-archive-writer-1', 'caddy', 'redis', 'graphdb'},
    'media': {'oldap-imageserver', 'oldap-mediahelper', 'oldap-ingest-worker',
              'oldap-export-worker', 'oldap-mobile-media-worker', 'oldap-media-caddy'},
}
PROBE = '''import json,subprocess
ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
items=json.loads(subprocess.check_output(['docker','inspect',*ids]))
print(json.dumps({c['Name'].lstrip('/'): {'container_id':c['Id'],'image_id':c['Image'],
 'reference':c['Config']['Image'],'started_at':c['State']['StartedAt']} for c in items}))
'''


def ssh(host, command, **kwargs):
    """Execute through trusted SSH; retain errors privately at the caller."""
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                           'rosenth@'+host, command], check=True, **kwargs)


def retain(destination):
    """Save and verify both source image sets; fail closed on inventory drift."""
    destination = destination.resolve()
    if any((p/'.git').exists() for p in [destination, *destination.parents]):
        raise ValueError('Use a destination outside Git')
    os.umask(0o077)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'running production images only; no data snapshot', 'hosts': {}}
    for role, host in HOSTS.items():
        before = json.loads(ssh(host, 'python3 -', input=PROBE, capture_output=True, text=True).stdout)
        if set(before) != EXPECTED[role]:
            raise RuntimeError('Review changed running container inventory: '+role)
        ids = sorted({c['image_id'] for c in before.values()})
        if any(len(i) != 71 or not i.startswith('sha256:') or
               any(c not in '0123456789abcdef' for c in i[7:]) for i in ids):
            raise ValueError('Invalid image identity')
        archive = destination/(role+'-images.tar')
        with archive.open('xb') as out:
            ssh(host, 'docker image save '+' '.join(ids), stdout=out, stderr=subprocess.PIPE)
        with archive.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        subprocess.run(['docker', 'image', 'load', '-i', str(archive)], check=True,
                       capture_output=True)
        for identity in ids:
            found = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', identity], text=True).strip()
            if found != identity:
                raise RuntimeError('Loaded image mismatch')
        after = json.loads(ssh(host, 'python3 -', input=PROBE, capture_output=True, text=True).stdout)
        if before != after:
            raise RuntimeError('Source changed during retention: '+role)
        report['hosts'][role] = {'host': host, 'containers': before,
                                 'archive': archive.name, 'bytes': archive.stat().st_size,
                                 'sha256': digest, 'docker_load_verified': True}
        (destination/(role+'-verified.json')).write_text(json.dumps(report['hosts'][role], indent=2)+'\n')
        print(role+': saved, loaded and verified', flush=True)
    (destination/'images-complete.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    retain(args.destination)
