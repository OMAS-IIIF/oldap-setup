#!/usr/bin/env python3
"""Restore the paired production checkpoint into a network-isolated rehearsal.

Run on the home Linux VM, never with live source paths as the destination. No
container is started by this script. Source configuration is already resolved and
image-pinned at capture; only cloned state is mounted. Workers and external mail
are excluded from the initial source comparison.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

spec = importlib.util.spec_from_file_location('home_restore', Path(__file__).with_name('prepare-home-restore.py'))
home = importlib.util.module_from_spec(spec)
spec.loader.exec_module(home)

spec = importlib.util.spec_from_file_location('image_archive', Path(__file__).with_name('verify-rollback-image-archive.py'))
image_archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_archive)

PREFIXES = {
    'api': ('srv/storage/graphdb', 'srv/storage/oldap-data/oldap-api',
            'srv/storage/oldap-data/archive-writer', 'srv/storage/caddy', 'opt/oldap', 'etc/oldap'),
    'media': ('data/media', 'data/oldap-ingest', 'data/oldap-import-records',
              'data/oldap-exports', 'data/oldap-mobile-uploads', 'opt/oldap-mediaserver'),
}


def safe_members(members, role):
    """Select runtime paths; reject unsafe selected entries before extracting any."""
    selected = []
    seen = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError('Unsafe snapshot path')
        if not any(str(path) == prefix or str(path).startswith(prefix+'/') for prefix in PREFIXES[role]):
            continue
        if not (member.isfile() or member.isdir()) or str(path) in seen:
            raise ValueError('Runtime snapshot contains links, special or duplicate members')
        seen.add(str(path))
        selected.append(member)
    if not selected:
        raise ValueError('No runtime files in snapshot')
    return selected


def verify_inputs(root):
    """Bind both archives and resolved configuration to the completion manifest."""
    incoming = root/'incoming'
    manifest = json.loads((incoming/'manifest.json').read_text())
    if manifest['status'] != 'source-recovered-checkpoint-complete':
        raise ValueError('Require a completed rehearsal checkpoint with recovered source')
    filenames = ['api.tar', 'media.tar', 'source.trig', 'api-source-compose.json', 'media-source-compose.json']
    if len(manifest['artifacts']) != len(filenames):
        raise ValueError('Incomplete source artifact manifest')
    for filename, evidence in zip(filenames, manifest['artifacts']):
        path = incoming/filename
        if path.is_symlink() or path.stat().st_size != evidence['size']:
            raise ValueError('Source artifact size/type mismatch')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != evidence['checksum']:
                raise ValueError('Source artifact checksum mismatch')
    return manifest


def extract(root):
    """Verify the complete pair, then restore runtime files into a NEW tree."""
    manifest = verify_inputs(root)
    # Validate both archives before writing either tree. GNU tar preserves owners
    # and ACLs; only prevalidated ordinary runtime members are selected.
    for role in PREFIXES:
        with tarfile.open(root/'incoming'/f'{role}.tar') as archive:
            safe_members(archive.getmembers(), role)
    tree = root/'tree'
    tree.mkdir(mode=0o755, exist_ok=False)
    for role in PREFIXES:
        with tarfile.open(root/'incoming'/f'{role}.tar') as archive:
            selected = safe_members(archive.getmembers(), role)
            names = root/f'{role}-members.list'
            names.write_bytes(b''.join(member.name.encode()+b'\0' for member in selected))
        subprocess.run(['tar', '--acls', '--xattrs', '--same-owner', '--numeric-owner',
                        '--no-recursion', '-xpf', str(root/'incoming'/f'{role}.tar'),
                        '-C', str(tree), '--null', '-T', str(names)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    (root/'extracted.json').write_text(json.dumps(manifest, indent=2)+'\n')


def configuration(root, project):
    """Generate an isolated GraphDB source, preserving exact retained images."""
    if not (root/'extracted.json').is_file():
        raise ValueError('Extract and verify first')
    tree = root/'tree'
    api = json.loads((root/'incoming/api-source-compose.json').read_text())['services']
    media = json.loads((root/'incoming/media-source-compose.json').read_text())['services']
    services = {name: home.isolated_service(api[name], root, tree)
                for name in ['graphdb', 'redis', 'archive-writer', 'oldap-api']}
    for original, name in [('mediaserver','oldap-mediahelper'), ('imageserver','oldap-imageserver')]:
        services[name] = home.isolated_service(media[original], root, tree)
    services['graphdb'].update(mem_limit='2048m', memswap_limit='2048m')
    services['graphdb'].setdefault('environment', {})['GDB_JAVA_OPTS'] = '-Xms512m -Xmx1536m'
    for name in ['redis', 'archive-writer']:
        services[name].update(mem_limit='256m', memswap_limit='256m')
    services['archive-writer']['networks'] = {'default': {'aliases':['archive-writer.internal']}}
    env = services['oldap-api']['environment']
    env.update(OLDAP_TS_SERVER='http://graphdb:7200', OLDAP_MEDIA_INTERNAL_URL='http://oldap-mediahelper:8000',
               OLDAP_MEDIA_INGEST_URL='http://oldap-mediahelper:8000', OLDAP_MEDIA_EXPORT_URL='http://oldap-mediahelper:8000',
               OLDAP_MAIL_HOST='disabled.invalid', OLDAP_MAIL_USERNAME='', OLDAP_MAIL_PASSWORD='')
    for key in ['OLDAP_PASSWORD_RESET_EMAIL_BACKEND','OLDAP_IMPORT_EMAIL_BACKEND','OLDAP_EXPORT_EMAIL_BACKEND']:
        env[key] = 'console'
    for name in ['oldap-mediahelper', 'oldap-imageserver']:
        services[name].setdefault('environment', {}).update(OLDAP_API_URL='http://oldap-api:8000', OLDAP_IMPORT_CALLBACK_RECONCILE_SECONDS='0')
    services['oldap-mediahelper']['environment'].update(MEDIA_BASE_URL='http://oldap-mediahelper:8000/', IIIF_BASE_URL='http://oldap-imageserver:8182/iiif/3/')
    images = {}
    for name, service in services.items():
        selected = service['image']
        if not re.fullmatch('sha256:[a-f0-9]{64}', selected):
            raise ValueError('Unpinned source image')
        role = 'media' if name in {'oldap-mediahelper', 'oldap-imageserver'} else 'api'
        installed = image_archive.resolve_source_image(selected, role)
        service['image'] = installed
        service['pull_policy'] = 'never'
        images[name] = {'source_image_id': selected, 'installed_id': installed, 'verification': ('exact-source-id' if installed == selected else 'config-and-layers-reexport')}
    result = {'name':project, 'services':services, 'networks':{'default':{
        'internal':True, 'driver':'bridge',
        'driver_opts':{'com.docker.network.bridge.gateway_mode_ipv4':'isolated'}}}}
    (root/'source-images.json').write_text(json.dumps(images, indent=2)+'\n')
    with (root/'source-compose.json').open('x') as stream:
        json.dump(result, stream, indent=2)


def main():
    """Require an explicit fresh rehearsal root/project; never start containers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['extract','compose'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    if args.root.parent != Path('/srv/storage') or not args.root.name.startswith('oldap-restore-rehearsal-') or args.root.resolve() != args.root:
        raise ValueError('Invalid rehearsal root')
    if not re.fullmatch('oldap-restore-[a-z0-9-]+', args.project):
        raise ValueError('Invalid isolated project')
    os.umask(0o077)
    if args.action == 'extract':
        extract(args.root)
    else:
        configuration(args.root, args.project)


if __name__ == '__main__':
    main()
