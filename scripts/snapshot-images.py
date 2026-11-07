#!/usr/bin/env python3
"""Print credential-free provenance for explicitly named snapshot containers.

Run on the Docker host while deployments are excluded. Content IDs identify local
images; repository digests, when available, allow pulling the same image again.
No environment variables, labels, mounts or resolved Compose secrets are emitted.
"""
import json
import subprocess
import sys


def inspect(kind, names):
    """Read Docker metadata privately; suppress potentially sensitive diagnostics."""
    result = subprocess.run(
        ['docker', kind, 'inspect', *names], capture_output=True, text=True
    )
    if result.returncode:
        raise RuntimeError(f'Docker {kind} inspection failed')
    return json.loads(result.stdout)


def inventory(names):
    """Return runtime image identities, registry references and platform metadata."""
    if not names or any(name.startswith('-') for name in names):
        raise ValueError('Explicit container names are required')
    containers = inspect('container', names)
    images = inspect('image', sorted({item['Image'] for item in containers}))
    by_id = {item['Id']: item for item in images}
    result = {}
    for container in containers:
        image = by_id[container['Image']]
        result[container['Name'].lstrip('/')] = {
            'configured_reference': container['Config']['Image'],
            'image_id': image['Id'],
            'repo_digests': sorted(image.get('RepoDigests') or []),
            'os': image['Os'],
            'architecture': image['Architecture'],
            'variant': image.get('Variant', ''),
        }
    return result


if __name__ == '__main__':
    print(json.dumps(inventory(sys.argv[1:]), sort_keys=True))
