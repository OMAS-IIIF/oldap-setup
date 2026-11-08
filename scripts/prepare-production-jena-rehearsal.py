#!/usr/bin/env python3
"""Prepare a separate Jena candidate from the accepted production source clone.

No containers are started. Copy static files from the accepted home release and
operational state from the STOPPED source clone into a new candidate directory.
Source and candidate can then replace one another under the same isolated project
without sharing writable state. Live home data is never copied or mounted.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

spec = importlib.util.spec_from_file_location('restore', Path(__file__).with_name('prepare-home-restore.py'))
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


def copy_owned(source, destination):
    """Preserve filesystem owners/modes; require a new destination."""
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(destination)], check=True, capture_output=True)


def prepare(root, project, media_image):
    """Bind new Jena transport to source accounts/policy and cloned media state."""
    accepted = json.loads((root/'source-acceptance.json').read_text())
    if accepted['status'] != 'passed':
        raise ValueError('Accept the restored source before preparing Jena')
    running = subprocess.check_output(['docker','ps','-q','--filter','label=com.docker.compose.project='+project], text=True).strip()
    if running:
        raise ValueError('Stop the isolated source before copying its state')
    candidate = root/'candidate'
    if candidate.exists():
        raise FileExistsError('Candidate must be new')
    if shutil.disk_usage(root).free < 25*1024**3 + shutil.disk_usage(root).total//5:
        raise ValueError('Insufficient candidate-copy space plus filesystem reserve')
    current = restore.read_compose(Path('/opt/oldap/compose'))['services']
    rows = json.loads(subprocess.check_output(['docker','inspect','compose-oldap-jena-1','compose-oldap-jena-identity-1','oldap-api','redis']))
    images = {r['Config']['Labels']['com.docker.compose.service']:r['Image'] for r in rows}
    source_api = json.loads((root/'incoming/api-source-compose.json').read_text())['services']['oldap-api']
    source_config = json.loads((root/'source-compose.json').read_text())
    candidate.mkdir(mode=0o700)
    os.chown(candidate,1000,1000)
    (candidate/'config').mkdir(mode=0o755)
    data = candidate/'data'
    data.mkdir(mode=0o755)
    native = data/'native'
    native.mkdir(mode=0o700)
    os.chown(native,1000,1000)
    # Snapshot-derived state, never the live home dataset or its Redis store.
    copy_owned(root/'tree/srv/storage/oldap-data/oldap-api', data/'api')
    copy_owned(root/'tree/opt/oldap/compose/redis-data', data/'redis')
    copy_owned(root/'tree/data', candidate/'media-state')
    copy_owned(root/'tree/opt/oldap/.env/archive-writer-client/archive-policy.json', candidate/'config/archive-policy.json')
    approved = {}
    for name in ['oldap-jena','oldap-jena-identity','oldap-api','redis']:
        service = copy.deepcopy(current[name])
        service['image'] = images[name]
        for mount in service.get('volumes', []):
            target = mount['target']
            if name == 'oldap-jena' and target == '/var/lib/oldap-jena':
                mount['source'] = str(native)
            elif name == 'oldap-api' and target == '/data':
                mount['source'] = str(data/'api')
            elif name == 'redis' and target == '/data':
                mount['source'] = str(data/'redis')
            elif name == 'oldap-api' and target == '/run/oldap-policy/archive-policy.json':
                mount['source'] = str(candidate/'config/archive-policy.json')
            elif mount.get('read_only'):
                # Static approved release/identity/config inputs only. Every
                # writable mount must match one of the explicit state paths.
                destination = candidate/'static'/name/Path(mount['source']).name
                copy_owned(Path(mount['source']), destination)
                if name == 'oldap-jena' and target == '/run/oldap-jena/service.properties':
                    os.chown(destination,1000,1000)
                mount['source'] = str(destination)
            else:
                raise ValueError('Unexpected writable accepted-home mount')
        approved[name] = restore.isolated_service(service, root, root/'tree', allowed_root=root)
        approved[name]['pull_policy'] = 'never'
    backend = approved['oldap-jena']
    backend.update(mem_limit='2048m', memswap_limit='2048m')
    backend['environment'].update(JAVA_HEAP_MB='1024', JAVA_TOOL_OPTIONS='-XX:MaxDirectMemorySize=256m')
    backend['networks'] = {'default':{'aliases':['oldap-api']}}
    approved['redis'].update(mem_limit='256m', memswap_limit='256m')
    approved['oldap-jena-identity'].update(mem_limit='128m', memswap_limit='128m')
    for name in ['oldap-api','oldap-jena-identity']:
        approved[name].pop('networks')
        approved[name]['network_mode'] = 'service:oldap-jena'
    env = approved['oldap-api']['environment']
    transport = {'OLDAP_BACKEND','OLDAP_TS_SERVER','OLDAP_TS_USER','OLDAP_TS_PASSWORD',
                 'OLDAP_STAGING_LOCK_REDIS_URL','OLDAP_ARCHIVE_POLICY_FILE','OLDAP_REDIS_URL'}
    for key,value in source_api['environment'].items():
        if key.startswith('OLDAP_') and key not in transport and not key.startswith(('OLDAP_JENA_', 'OLDAP_WRITER_')):
            env[key] = value
    env.update(OLDAP_BACKEND='jena', OLDAP_TS_SERVER='http://127.0.0.1:3031',
               OLDAP_REDIS_URL='redis://redis:6379', OLDAP_STAGING_LOCK_REDIS_URL='redis://redis:6379/1',
               OLDAP_ARCHIVE_POLICY_FILE='/run/oldap-policy/archive-policy.json',
               OLDAP_MEDIA_INTERNAL_URL='http://oldap-mediahelper:8000',
               OLDAP_MEDIA_INGEST_URL='http://oldap-mediahelper:8000', OLDAP_MEDIA_EXPORT_URL='http://oldap-mediahelper:8000',
               OLDAP_MAIL_HOST='disabled.invalid', OLDAP_MAIL_USERNAME='', OLDAP_MAIL_PASSWORD='')
    for key in ['OLDAP_PASSWORD_RESET_EMAIL_BACKEND','OLDAP_IMPORT_EMAIL_BACKEND','OLDAP_EXPORT_EMAIL_BACKEND']:
        env[key] = 'console'
    for key in ['OLDAP_ACCESS_JWT_SECRET','OLDAP_JWT_ISSUER','OLDAP_JWT_AUDIENCE']:
        approved['oldap-jena-identity']['environment'][key] = env[key]
    installed_media = json.loads(subprocess.check_output(['docker','image','inspect',media_image],stderr=subprocess.PIPE))[0]['Id']
    for name in ['oldap-mediahelper','oldap-imageserver']:
        service = copy.deepcopy(source_config['services'][name])
        for mount in service['volumes']:
            source = Path(mount['source'])
            if source.is_relative_to(root/'tree/data'):
                mount['source'] = str(candidate/'media-state'/source.relative_to(root/'tree/data'))
            elif mount['target'] == '/var/cache/sipi':
                cache=candidate/'sipi-cache';cache.mkdir(mode=0o777);cache.chmod(0o777)
                mount['source']=str(cache)
            else:
                raise ValueError('Unexpected source media mount')
        if name == 'oldap-mediahelper':
            service['image'] = installed_media
        approved[name] = service
    result = {'name':project, 'services':approved, 'networks':source_config['networks']}
    with (root/'candidate-compose.json').open('x') as stream:
        json.dump(result,stream,indent=2)
    (root/'candidate-prepared.json').write_text(json.dumps({'status':'prepared_not_started', 'source_snapshot':accepted['snapshot_id'], 'images':{n:s['image'] for n,s in approved.items()}},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--project',required=True)
    parser.add_argument('--media-image',required=True)
    args=parser.parse_args()
    if args.root.parent != Path('/srv/storage') or not args.root.name.startswith('oldap-restore-rehearsal-') or args.root.resolve()!=args.root:
        raise ValueError('Invalid rehearsal root')
    if not re.fullmatch('oldap-restore-[a-z0-9-]+',args.project) or not re.fullmatch(r'[^\s]+@sha256:[a-f0-9]{64}',args.media_image):
        raise ValueError('Invalid isolated project or unpinned media image')
    os.umask(0o077)
    prepare(args.root,args.project,args.media_image)
