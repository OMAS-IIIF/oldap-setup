#!/usr/bin/env python3
"""Check target media credentials and signed IIIF without opening production writers.

Use the precreated target images/environment. The upload probe has no host data
mounts or network. The SIPI probe has no published ports, read-only media and an
empty temporary cache. Short-lived API tokens come from a protected input file;
never print them. Both real production media services and workers remain stopped.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess

AUTH_CODE = '''import json
from pathlib import Path
from app import app
inputs=json.loads(Path('/probe/input.json').read_text())
client=app.test_client()
assert client.post('/upload').status_code==401
assert client.post('/upload',headers={'Authorization':'Bearer invalid-probe-token'}).status_code==401
r=client.post('/upload',headers={'Authorization':'Bearer '+inputs['access_token']})
assert r.status_code==400 and r.json['message']=='Missing projectId field'
print(json.dumps({'status':'passed','upload_auth':'fresh API token accepted; missing/invalid tokens rejected; no upload submitted'}))
'''
IMAGE_CODE = '''import hashlib,json,time
from pathlib import Path
from urllib.parse import urlencode
import requests
inputs=json.loads(Path('/probe/input.json').read_text())
s=requests.Session();s.trust_env=False
base='http://127.0.0.1:8182/iiif/3/'+inputs['asset']
query='?'+urlencode({'token':inputs['media_token']})
for attempt in range(40):
    try:
        r=s.get(base+'/info.json'+query,timeout=5)
        if r.status_code==200:break
    except requests.RequestException:pass
    time.sleep(.5)
else:raise RuntimeError('Private signed IIIF metadata unavailable')
metadata=r.json()
r=s.get(base+'/full/!160,160/0/default.jpg'+query,timeout=30)
assert r.status_code==200 and r.content.startswith(b'\\xff\\xd8\\xff')
result={'status':'passed','iiif_dimensions':{k:metadata[k] for k in ('width','height')},'image_bytes':len(r.content),'image_sha256':hashlib.sha256(r.content).hexdigest()}
for key in ('iiif_dimensions','image_bytes','image_sha256'):assert result[key]==inputs['expected'][key], key+' differs from accepted source baseline'
print(json.dumps(result))
'''


def run(input_path):
    """Run disposable probes; guarantee removal without touching source storage."""
    if input_path.is_symlink() or input_path.stat().st_mode & 0o077:
        raise ValueError('Probe tokens require a private ordinary file')
    if subprocess.check_output(['docker', 'ps', '-q'], text=True).strip():
        raise ValueError('Keep all production media services stopped')
    rows = json.loads(subprocess.check_output(['docker', 'inspect', 'oldap-mediahelper', 'oldap-imageserver']))
    helper, sipi = rows
    environments = [{k:v for k,v in (item.split('=',1) for item in row['Config']['Env'])} for row in rows]
    for row in rows:
        if row['State']['Running']:
            raise ValueError('Production media must remain private and stopped')
    token_mount = ['--mount', f'type=bind,src={input_path.resolve()},dst=/probe/input.json,readonly']
    helper_env = dict(os.environ)
    helper_env.update(environments[0])
    helper_env['OLDAP_IMPORT_CALLBACK_RECONCILE_SECONDS'] = '0'
    helper_flags = [value for key in environments[0] for value in ('-e', key)]
    if 'OLDAP_IMPORT_CALLBACK_RECONCILE_SECONDS' not in environments[0]:
        helper_flags += ['-e', 'OLDAP_IMPORT_CALLBACK_RECONCILE_SECONDS']
    auth = json.loads(subprocess.check_output(
        ['docker','run','--rm','-i','--user','0:0','--network','none',*token_mount,*helper_flags,helper['Image'],'python','-'],
        input=AUTH_CODE.encode(), env=helper_env, stderr=subprocess.PIPE))
    name = 'oldap-private-sipi-acceptance'
    if subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
        raise ValueError('Private probe already exists; inspect before retrying')
    command=['docker','run','--detach','--name',name,'--network','none','--tmpfs','/var/cache/sipi:rw,size=256m']
    for mount in sipi['Mounts']:
        if mount['Destination']=='/var/cache/sipi':continue
        if mount['Type']!='bind' or mount['Source']!='/data/media' or mount['Destination']!='/data/images':
            raise ValueError('Unexpected SIPI source mount')
        command += ['--mount','type=bind,src=/data/media,dst=/data/images,readonly']
    for key in environments[1]:command += ['-e',key]
    entrypoint=sipi['Config']['Entrypoint']
    command += ['--entrypoint',entrypoint[0],sipi['Image'],*entrypoint[1:],*(sipi['Config'].get('Cmd') or [])]
    try:
        subprocess.run(command,env=dict(os.environ,**environments[1]),check=True,stdout=subprocess.DEVNULL)
        image=json.loads(subprocess.check_output(
            ['docker','run','--rm','-i','--user','0:0','--network','container:'+name,*token_mount,helper['Image'],'python','-'],
            input=IMAGE_CODE.encode(), stderr=subprocess.PIPE))
    finally:
        subprocess.run(['docker','rm','-f',name],check=True,stdout=subprocess.DEVNULL)
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():
        raise ValueError('Unexpected media process after probes')
    return {'status':'passed','scope':'disposable target images, upload-token validation and read-only signed source media; public ingress stayed closed',
            'authentication':auth,'image':image}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    args=parser.parse_args()
    if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='dhlab-iii':
        parser.error('Run as root on the frozen production media VM')
    print(json.dumps(run(args.input),indent=2))
