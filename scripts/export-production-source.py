#!/usr/bin/env python3
"""Check idle source coordination and export asserted RDF with writers stopped.

Run on the API host as root. Use the stopped original API image/environment and
read-only bind mounts for the TLS coordinator credential. Never start its normal
entrypoint. All raw environment/output stays private; no keys are removed. Export
HTTP failure, occupied coordination or any Docker failure aborts the checkpoint.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

CLIENT = r'''
import os,requests
from redis import Redis
from urllib.parse import quote
writer=Redis.from_url(os.environ['OLDAP_STAGING_LOCK_REDIS_URL'],socket_timeout=10)
assert writer.ping()
for key in ['oldap-api:staging:mutation','oldap-api:staging:recovery:barrier','oldap-api:staging:recovery:controller']:
    assert writer.get(key) is None, 'Source coordinator is occupied'
assert Redis(host='redis',port=6379,db=1,socket_timeout=10).dbsize()==0, 'Ordinary coordination is occupied'
url=os.environ['OLDAP_TS_SERVER'].rstrip('/')+'/repositories/'+quote(os.environ['OLDAP_TS_REPO'],safe='')+'/statements'
user=os.environ.get('OLDAP_TS_USER','');password=os.environ.get('OLDAP_TS_PASSWORD','')
with requests.get(url,params={'infer':'false'},headers={'Accept':'application/x-trigstar'},auth=(user,password) if user else None,stream=True,timeout=(10,120)) as response:
    response.raise_for_status()
    assert response.headers.get('Content-Type','').split(';')[0] in ['application/x-trigstar','application/trig','application/x-trig']
    with open('/snapshot/source.trig','xb') as output:
        for block in response.iter_content(1024*1024):output.write(block)
        output.flush();os.fsync(output.fileno())
'''


def export(root):
    """Use a disposable read-only client, retaining private export inputs for recovery."""
    os.umask(0o077)
    row = json.loads(subprocess.check_output(['docker','inspect','oldap-api']))[0]
    if row['State']['Running']:
        raise RuntimeError('API must be stopped before source export')
    environment = row['Config']['Env']
    if any('\n' in line or '\r' in line for line in environment):
        raise ValueError('Environment cannot be represented safely as an env-file')
    env_file = root/'source-api.env'
    with env_file.open('x') as stream:
        stream.write('\n'.join(environment)+'\n')
    subprocess.run(['docker','run','--rm','--pull','never','--name','oldap-cutover-source-reader',
                    '--network','compose_default','--read-only','--user','0:0',
                    '--cap-drop','ALL','--security-opt','no-new-privileges',
                    '--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
                    '--volumes-from','oldap-api:ro','--env-file',str(env_file),
                    '--mount','type=bind,src='+str(root)+',dst=/snapshot',
                    '--entrypoint','python',row['Image'],'-c',CLIENT],
                   check=True,capture_output=True)
    if (root/'source.trig').stat().st_size == 0:
        raise RuntimeError('Empty repository export')


if __name__ == '__main__':
    export(Path(sys.argv[1]))
