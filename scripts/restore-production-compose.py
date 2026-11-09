#!/usr/bin/env python3
"""Restore only original Compose inputs from a verified frozen checkpoint.

All containers must be stopped by the caller. Persistent GraphDB, Redis and media
state is NOT extracted or overwritten. Target-only configuration is quarantined
outside the active Compose directory, preventing stale automatic overrides. The source's resolved, image-pinned JSON
is used for recreation, avoiding mutable tags. Partial failures remain closed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import stat
import tempfile
import tarfile


REQUIRED_FILES = {
    'api': {'.env', 'docker-compose.yml', 'Caddyfile'},
    'media': {'docker-compose.yml', 'Caddyfile', 'mediaserver.env',
              'mediahelper-access.env', 'ingest-worker.env', 'export-worker.env',
              'mobile-media-worker.env'},
}


def unexpected_inputs(directory, expected, excluded=None):
    """Find target-only inputs without traversing preserved Redis state or links.

    expected contains paths relative to the Compose directory, including their
    parent directories. Unknown directories are moved as units, not traversed.
    """
    extras=[]
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError('Current Compose root is not an ordinary directory')
    if not directory.exists(): return extras
    for parent, directories, files in os.walk(directory, followlinks=False):
        for name in directories[:] + files:
            path=Path(parent)/name
            relative=path.relative_to(directory)
            if excluded is not None and (relative==excluded or excluded in relative.parents):
                if name in directories: directories.remove(name)
                continue
            mode=path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError('Unexpected link or special current Compose input')
            if relative not in expected:
                extras.append(path)
                if name in directories: directories.remove(name)
    return extras


def quarantine_inputs(directory, extras, checkpoint):
    """Atomically move target-only inputs outside Compose, retaining private evidence.

    A sibling directory keeps every rename on the same filesystem, even when
    /opt and the checkpoint live on different disks. No source data is deleted.
    """
    if not extras: return
    quarantine=Path(tempfile.mkdtemp(prefix='.rollback-config-'+checkpoint.name+'-',dir=directory.parent))
    for path in extras:
        target=quarantine/path.relative_to(directory)
        target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        path.rename(target)
    (checkpoint/'rollback-config-quarantine.json').write_text(json.dumps(
        {'path':str(quarantine),'inputs':[str(p.relative_to(directory)) for p in extras]},indent=2)+'\n')


def restore(role, checkpoint, *, check_only=False):
    """Verify inputs, optionally restoring only the bounded original Compose tree.

    check_only performs no writes.
    """
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
    seen=set()
    regular=set()
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
            if value in seen:
                raise ValueError('Duplicate Compose input')
            seen.add(value)
            if member.isfile():
                regular.add(value)
            if not (member.isfile() or member.isdir()):
                raise ValueError('Unexpected link/special Compose input')
            # Existing symlinks could redirect an otherwise safe extraction.
            destination=Path('/')/name
            if any(path.is_symlink() for path in [destination,*destination.parents]):
                raise ValueError('Source Compose destination contains a symlink')
            names.append(member.name)
    if not {prefix+'/'+name for name in REQUIRED_FILES[role]}.issubset(regular):
        raise ValueError('Incomplete original Compose configuration for '+role)
    directory=Path('/')/prefix
    expected={Path(name).relative_to(prefix) for name in seen}
    for name in list(expected): expected.update(name.parents)
    extras=unexpected_inputs(directory,expected,Path('redis-data') if role=='api' else None)
    if check_only:
        print('Original Compose inputs verified; no files or services changed')
        return
    os.umask(0o077)
    quarantine_inputs(directory,extras,checkpoint)
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
    parser.add_argument('--check-only', action='store_true')
    args=parser.parse_args()
    expected_parent=Path('/srv/storage') if args.role=='api' else Path('/data')
    if args.checkpoint.parent!=expected_parent or not args.checkpoint.name.startswith('oldap-cutover-') or args.checkpoint.resolve()!=args.checkpoint:
        raise ValueError('Invalid production checkpoint path')
    restore(args.role,args.checkpoint, check_only=args.check_only)
