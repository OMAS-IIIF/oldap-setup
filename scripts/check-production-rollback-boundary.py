#!/usr/bin/env python3
"""Read-only admission for rollback of a private, never-opened production target.

Permit partial candidate startup, but refuse public ingress, media workers,
unknown running containers or a running/missing source GraphDB. The durable
opening marker is checked separately on the API host before either host changes.
"""
import json
import subprocess
import sys


def validate(role, rows):
    """Allow only the private API/storage consumers; media must remain stopped."""
    by_name={row['Name'].lstrip('/'):row for row in rows}
    running={name for name,row in by_name.items() if row['State']['Running']}
    allowed={'oldap-api','redis','compose-oldap-jena-1','compose-oldap-jena-identity-1'} if role=='api' else set()
    if not running.issubset(allowed):
        raise ValueError('Public, source or unknown writers are running; do not roll back')
    if role=='api':
        graphdb=by_name.get('graphdb')
        if not graphdb or graphdb['State']['Running'] or graphdb['State'].get('OOMKilled') or graphdb['State'].get('ExitCode') not in {0,143}:
            raise ValueError('Retained source GraphDB is not cleanly stopped')


if __name__=='__main__':
    role=sys.argv[1]
    if role not in {'api','media'}:
        raise ValueError('Unknown role')
    ids=subprocess.check_output(['docker','ps','-aq'],text=True).split()
    rows=json.loads(subprocess.check_output(['docker','inspect',*ids])) if ids else []
    validate(role,rows)
    print('Private rollback boundary passed')
