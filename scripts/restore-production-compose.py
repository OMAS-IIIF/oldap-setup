#!/usr/bin/env python3
"""Restore only original Compose inputs from a verified frozen checkpoint.

All containers must be stopped by the caller. Persistent GraphDB, Redis and media
state is NOT extracted or overwritten. The source's resolved, image-pinned JSON
is used for recreation, avoiding mutable tags. Partial failures remain closed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


def restore(role, checkpoint):
    """Verify archive/config bytes and restore the bounded original Compose tree."""
    manifest=json.loads((checkpoint/'manifest.json').read_text())
    if manifest['status']!='source-frozen':
        raise ValueError('Require a held final source checkpoint')
    archive=checkpoint/(role+'.tar')
    config=checkpoint/'source-compose.json'
    indices=(0,3) if role=='api' else (1,4)
    for path,index in zip([archive,config],indices):
        expected=manifest['artifacts'][index]
        if path.is_symlink() or path.stat().st_size!=expected['size']:
            raise ValueError('Checkpoint artifact size/type mismatch')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=expected['checksum']:
                raise ValueError('Checkpoint artifact checksum mismatch')
    prefix='opt/oldap/compose' if role=='api' else 'opt/oldap-mediaserver/compose'
    excluded='opt/oldap/compose/redis-data'
    names=[]
    with tarfile.open(archive) as stream:
        for member in stream:
            name=PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts:
                raise ValueError('Unsafe snapshot member')
            value=str(name)
            if value==excluded or value.startswith(excluded+'/'):
                continue
            if value!=prefix and not value.startswith(prefix+'/'):
                continue
            if not (member.isfile() or member.isdir()):
                raise ValueError('Unexpected link/special Compose input')
            # Existing symlinks could redirect an otherwise safe extraction.
            destination=Path('/')/name
            if any(path.is_symlink() for path in [destination,*destination.parents]):
                raise ValueError('Source Compose destination contains a symlink')
            names.append(member.name)
    if prefix+'/.env' not in names or prefix+'/docker-compose.yml' not in names:
        raise ValueError('Incomplete original Compose configuration')
    os.umask(0o077)
    selection=checkpoint/'rollback-config-members.list'
    selection.write_bytes(b''.join(name.encode()+b'\0' for name in names))
    subprocess.run(['tar','--acls','--xattrs','--same-owner','--numeric-owner','--no-recursion',
                    '-xpf',str(archive),'-C','/','--null','-T',str(selection)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    print('Original Compose inputs restored; persistent data and services unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=['api','media'])
    parser.add_argument('checkpoint',type=Path)
    args=parser.parse_args()
    expected_parent=Path('/srv/storage') if args.role=='api' else Path('/data')
    if args.checkpoint.parent!=expected_parent or not args.checkpoint.name.startswith('oldap-cutover-') or args.checkpoint.resolve()!=args.checkpoint:
        raise ValueError('Invalid production checkpoint path')
    restore(args.role,args.checkpoint)
