#!/usr/bin/env python3
"""Reject a snapshot whose source roots omit a running service's bind mounts.

Run before stopping services. Image cache is the only permitted named volume.
Docker environment values are read into memory but never included in the report.
This checks coverage, not whether services have been drained or archives verified.
"""
import json
from pathlib import PurePosixPath
import subprocess
import sys


def validate(containers, roots):
    """Require each bind mount to lie in an explicit relative archive root."""
    paths = []
    for root in roots:
        path = PurePosixPath(root)
        if path.is_absolute() or '..' in path.parts or str(path) in ('', '.'):
            raise ValueError('Invalid snapshot root')
        paths.append(PurePosixPath('/') / path)
    count = 0
    for container in containers:
        for mount in container.get('Mounts', []):
            if mount['Type'] == 'volume' and mount['Destination'] == '/var/cache/sipi':
                continue  # Rebuildable image cache; never database or user state.
            if mount['Type'] != 'bind':
                raise ValueError('Unreviewed persistent mount type')
            source = PurePosixPath(mount['Source'])
            if not any(source.is_relative_to(root) for root in paths):
                raise ValueError('Snapshot omits a service bind mount: '+str(source))
            count += 1
    return count


if __name__ == '__main__':
    request = json.load(sys.stdin)
    containers = json.loads(subprocess.check_output(['docker', 'inspect', *request['containers']]))
    print(json.dumps({'covered_bind_mounts': validate(containers, request['roots'])}))
