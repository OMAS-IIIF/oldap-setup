#!/usr/bin/env python3
"""Prepare and reversibly swap a production source clone onto the home hosts.

Run as root only on the explicitly identified home machines. The caller drains
all services first. Home directories are renamed, never overwritten. A durable
path journal makes an interrupted swap recoverable. No service is started here.
The rollback fixture contains configuration-only archives; original full paired
production snapshots and the fresh home backup are retained independently.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tarfile

PREFIXES = {
    'api': ['srv/storage/graphdb', 'srv/storage/oldap-data', 'srv/storage/caddy', 'opt/oldap', 'etc/oldap'],
    'media': ['data/media', 'data/oldap-ingest', 'data/oldap-import-records', 'data/oldap-exports', 'data/oldap-mobile-uploads', 'opt/oldap-mediaserver'],
}
SOURCE_NAMES = {
    'api': ['graphdb','redis','compose-archive-writer-1','oldap-api','caddy','oldap-app','fasnachts-page','compose-salsah-2-1'],
    'media': ['oldap-imageserver','oldap-mediahelper','oldap-ingest-worker','oldap-export-worker','oldap-mobile-media-worker','oldap-media-caddy'],
}
HOME_NAMES = {**SOURCE_NAMES, 'api': ['redis','compose-oldap-jena-1','compose-oldap-jena-identity-1','oldap-api','caddy','oldap-app','fasnachts-page','compose-salsah-2-1']}
DIRECTORIES = {'api':'/opt/oldap/compose','media':'/opt/oldap-mediaserver/compose'}
HOSTS = {'api':'api', 'media':'media'}
HOST_REPLACEMENTS = {'api.salsah.org':'api.home.org', 'www.salsah.org':'www.salsah.home.org',
    'salsah.org':'salsah.home.org', 'fasnacht.oldap.org':'fasnacht-alias.home.org',
    'fasnacht.digital':'fasnacht.home.org', 'api.oldap.org':'api.home.org',
    'media.oldap.org':'media.home.org', 'app.oldap.org':'app.home.org', 'graphdb.oldap.org':'graphdb.home.org'}


def write_json(path, value):
    """Persist private state before moving any live path."""
    with path.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    fd=os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def home_url(value):
    """Rewrite transport hosts only; callers must exclude RDF identifiers/secrets."""
    for source, destination in HOST_REPLACEMENTS.items():
        value=value.replace(source,destination)
    return value


def require_stopped():
    """Refuse path changes while any container could still write host state."""
    if subprocess.check_output(['docker','ps','-q']).strip():
        raise ValueError('Every home service must be drained before swapping paths')


def prepare(role, root, source_tree, source_config):
    """Copy source state and capture immutable home recovery configuration."""
    if (root/'prepared.json').exists():
        raise FileExistsError('Rehearsal already prepared')
    spec=importlib.util.spec_from_file_location('images',Path(__file__).with_name('verify-rollback-image-archive.py'))
    images=importlib.util.module_from_spec(spec);spec.loader.exec_module(images)
    home=json.loads(subprocess.check_output(['docker','compose','--profile','*','config','--format','json'],cwd=DIRECTORIES[role],stderr=subprocess.PIPE))
    rows=json.loads(subprocess.check_output(['docker','inspect',*HOME_NAMES[role]]))
    selected={}
    for row in rows:
        name=row['Config']['Labels']['com.docker.compose.service']
        service=home['services'][name]
        service.update(image=row['Image'],pull_policy='never')
        selected[name]=service
    home['services']=selected
    write_json(root/'home-compose.json',home)
    write_json(root/'home-images.json',{r['Name'].lstrip('/'):r['Image'] for r in rows})
    config=json.loads(source_config.read_text())
    for service in config['services'].values():
        service['image']=images.resolve_source_image(service['image'],role)
        service['pull_policy']='never'
        for key,value in service.get('environment',{}).items():
            if isinstance(value,str) and any(word in key for word in ['URL','ORIGIN']):
                service['environment'][key]=home_url(value)
        # Internal HTTP is restricted to the home rehearsal; avoid relying on
        # production public certificates or mutating the hosts' trust stores.
        for key in ['OLDAP_API_URL','OLDAP_MEDIA_INTERNAL_URL','OLDAP_MEDIA_EXPORT_URL','OLDAP_MEDIA_INGEST_URL']:
            if key in service.get('environment',{}):
                service['environment'][key]=service['environment'][key].replace('https://','http://')
        for key in ['OLDAP_EXPORT_EMAIL_BACKEND','OLDAP_IMPORT_EMAIL_BACKEND','OLDAP_PASSWORD_RESET_EMAIL_BACKEND']:
            if key in service.get('environment',{}): service['environment'][key]='console'
    write_json(root/'source-compose.json',config)
    tree=root/'source-tree';tree.mkdir()
    for prefix in PREFIXES[role]:
        source=source_tree/prefix
        if not source.exists(): continue
        destination=tree/prefix;destination.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['cp','-a','--reflink=auto',str(source),str(destination)],check=True)
    # Never renew production certificates from the rehearsal hosts. New local
    # Caddy state is disposable; the original home CA remains in retained roots.
    caches = ['srv/storage/caddy/data','srv/storage/caddy/conf'] if role=='api' else ['opt/oldap-mediaserver/caddy-data','opt/oldap-mediaserver/caddy-config']
    for prefix in caches:
        cache=tree/prefix
        if cache.exists(): shutil.rmtree(cache)
        cache.mkdir(parents=True,mode=0o755)
    caddy=tree/DIRECTORIES[role].lstrip('/')/'Caddyfile'
    text=home_url(caddy.read_text())
    text=text.replace('{','{\n    local_certs',1)
    host='api.home.org' if role=='api' else 'media.home.org'
    text=text.replace(host+' {','http://'+host+', https://'+host+' {',1)
    caddy.write_text(text)
    # Configure only harmless transport differences. The archived home-specific
    # Caddyfile must survive the actual production rollback extraction.
    prefix=DIRECTORIES[role].lstrip('/')
    with tarfile.open(root/(role+'.tar'),'w') as archive:
        def exclude_redis(info):
            return None if '/redis-data' in info.name else info
        archive.add(tree/prefix,arcname=prefix,filter=exclude_redis)
    write_json(root/'prepared.json',{'role':role,'source_tree':str(source_tree),'source_config':str(source_config)})


def swap(role,root):
    """Retain home roots and install prepared source roots, journaling first."""
    require_stopped()
    if not (root/'prepared.json').exists() or (root/'home-paths.json').exists():
        raise ValueError('Require a new prepared swap')
    paths=[]
    for prefix in PREFIXES[role]:
        live=Path('/')/prefix
        source=root/'source-tree'/prefix
        if live.is_symlink() or source.is_symlink(): raise ValueError('Symlinked root')
        paths.append({'prefix':prefix,'home_existed':live.exists(),'source_exists':source.exists()})
    write_json(root/'home-paths.json',paths)
    for item in paths:
        prefix=item['prefix']; live=Path('/')/prefix; saved=live.with_name(live.name+'.'+root.name+'.retained')
        if saved.exists(): raise FileExistsError(saved)
        if item['home_existed']: live.rename(saved)
        if item['source_exists']:
            live.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['cp','-a','--reflink=auto',str(root/'source-tree'/prefix),str(live)],check=True)
    write_json(root/'home-rehearsal.json',{'snapshot_id':root.name.removeprefix('oldap-cutover-'),'home_retained':True})


def restore(role,root):
    """Recover retained home roots, including an interrupted partial swap."""
    require_stopped()
    if (root/'home-paths-restored.json').exists():
        raise FileExistsError('Home paths already restored')
    paths=json.loads((root/'home-paths.json').read_text())
    for item in reversed(paths):
        prefix=item['prefix'];live=Path('/')/prefix;saved=live.with_name(live.name+'.'+root.name+'.retained')
        if saved.exists() or not item['home_existed']:
            if live.exists():
                retired=live.with_name(live.name+'.'+root.name+'.retired')
                retired.parent.mkdir(parents=True,exist_ok=True)
                if retired.exists(): raise FileExistsError(retired)
                live.rename(retired)
            if saved.exists(): saved.rename(live)
    write_json(root/'home-paths-restored.json',{'status':'restored'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','swap','restore'])
    parser.add_argument('role',choices=['api','media'])
    parser.add_argument('root',type=Path)
    parser.add_argument('--source-tree',type=Path)
    parser.add_argument('--source-config',type=Path)
    args=parser.parse_args()
    if socket.gethostname().split('.')[0] != HOSTS[args.role]: raise ValueError('Home host only')
    parent=Path('/srv/storage') if args.role=='api' else Path('/data')
    if args.root.parent!=parent or not args.root.name.startswith('oldap-cutover-home-rehearsal-') or args.root.resolve()!=args.root:
        raise ValueError('Explicit home rehearsal root required')
    if os.geteuid()!=0: raise ValueError('Root ownership is required')
    os.umask(0o077);args.root.mkdir(mode=0o700,exist_ok=True)
    if args.action=='prepare': prepare(args.role,args.root,args.source_tree,args.source_config)
    elif args.action=='swap': swap(args.role,args.root)
    else: restore(args.role,args.root)
