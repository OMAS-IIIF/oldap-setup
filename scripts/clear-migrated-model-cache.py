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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    import redis
    client = redis.Redis.from_url(os.environ['OLDAP_REDIS_URL'])
    print(json.dumps(clear_cache(client, apply=args.apply), indent=2))
