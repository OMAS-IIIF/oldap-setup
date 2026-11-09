#!/usr/bin/env python3
"""Discard derived OLDAP objects from the PRIVATE target Redis copy before startup.

Never FLUSHDB: the same database can contain authentication/revocation records.
Only explicit library object classes serialized by CacheSingletonRedis qualify.
Run with all target clients stopped and independently verify the target Redis
container's bind path. Source Redis must remain untouched for rollback. The URL
comes from OLDAP_REDIS_URL; credentials and cache values are never printed.
"""
import argparse
from collections import Counter
import json
import os

DERIVED_CLASSES = frozenset({'DataModel','ResourceClass','PropertyClass','ExternalOntology',
                             'Project','User','Role','OldapList','OldapListNode'})
COMPARE_DELETE = "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) else return -1 end"


def derived_class(value):
    """Identify only explicitly recognized top-level library cache objects."""
    try:
        value = json.loads(value)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    if not isinstance(value, dict): return None
    name = value.get('__class__')
    return name if isinstance(name, str) and name in DERIVED_CLASSES else None


def clear_cache(client, *, apply=False):
    """Scan one database; delete recognized objects only if their value is unchanged.

    The default is a read-only plan. A concurrent change aborts apply, preserving
    the changed entry. Durable keys, other Redis databases and unknown formats
    are never modified. Counts intentionally omit key names and values.
    """
    seen = set(); counts = Counter(); retained = 0
    for key in client.scan_iter(count=200):
        if key in seen: continue
        seen.add(key)
        if client.type(key) not in (b'string','string'):
            retained += 1; continue
        value = client.get(key)
        name = derived_class(value)
        if name is None:
            retained += 1; continue
        if apply and client.eval(COMPARE_DELETE, 1, key, value) != 1:
            raise RuntimeError('Cache changed during migration; keep target clients stopped')
        counts[name] += 1
    return {'status':'applied' if apply else 'planned','derived_objects':dict(sorted(counts.items())),
            'retained_entries':retained,'other_databases_untouched':True}


def clear_private_production(target_root):
    """Run both cache passes only on newly bound Redis with all clients stopped.

    Called by the private cutover play before identity/API startup. Inspect actual
    Docker mounts and process states; never trust the desired Compose file alone.
    The existing API image supplies Python/redis; no host package install needed.
    """
    from pathlib import Path
    import re
    import socket
    import subprocess
    if os.geteuid() != 0 or socket.gethostname().split('.')[0] != 'dhlab-oldap':
        raise ValueError('Private production cleanup requires API-host root')
    root = Path(target_root)
    if not re.fullmatch(r'/srv/storage/oldap-jena-production-[a-zA-Z0-9_-]+', str(root)) or root.resolve() != root:
        raise ValueError('Invalid private production root')
    running = set(subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).split())
    if running != {'redis', 'compose-oldap-jena-1'}:
        raise ValueError('Keep all target clients and public services stopped')
    rows = json.loads(subprocess.check_output(['docker', 'inspect', 'redis', 'oldap-api', 'compose-oldap-jena-identity-1']))
    by_name = {row['Name'].lstrip('/'): row for row in rows}
    for name in ('oldap-api', 'compose-oldap-jena-identity-1'):
        if by_name[name]['State']['Running']:
            raise ValueError('Target client is already running')
    mounts = [m for m in by_name['redis']['Mounts'] if m['Destination'] == '/data']
    if len(mounts) != 1 or mounts[0]['Type'] != 'bind' or mounts[0]['Source'] != str(root/'data/redis'):
        raise ValueError('Redis is not the isolated target copy')
    if (root/'data/redis').resolve() != root/'data/redis':
        raise ValueError('Target Redis path resolves outside reviewed storage')
    api = by_name['oldap-api']
    environment = dict(item.split('=', 1) for item in api['Config']['Env'])
    if environment.get('OLDAP_BACKEND') != 'jena' or environment.get('OLDAP_REDIS_URL') not in ('redis://redis:6379', 'redis://redis:6379/0'):
        raise ValueError('Unexpected target backend/Redis database')
    env = dict(os.environ, OLDAP_REDIS_URL='redis://127.0.0.1:6379/0')
    command = ['docker', 'run', '--rm', '--network', 'container:redis',
               '--mount', f'type=bind,src={Path(__file__).resolve()},dst=/clear-cache.py,readonly',
               '-e', 'OLDAP_REDIS_URL', api['Image'], 'python', '/clear-cache.py']
    results = []
    for arguments in ([], ['--apply']):
        result = subprocess.check_output(command + arguments, env=env)
        results.append(json.loads(result))
    if results[0]['derived_objects'] != results[1]['derived_objects']:
        raise ValueError('Derived cache changed between plan and application')
    return {'status': 'passed', 'target_root': str(root), 'passes': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--private-production-root')
    args = parser.parse_args()
    if args.private_production_root:
        print(json.dumps(clear_private_production(args.private_production_root), indent=2))
        raise SystemExit(0)
    import redis
    client = redis.Redis.from_url(os.environ['OLDAP_REDIS_URL'])
    print(json.dumps(clear_cache(client, apply=args.apply), indent=2))
