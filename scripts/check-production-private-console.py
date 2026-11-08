"""Check the production native console inside its private network namespace."""
import hashlib,json,uuid,zipfile
from pathlib import Path
import requests
config={}
for line in Path('/probe/service.properties').read_text().splitlines():
    if line.strip() and not line.lstrip().startswith('#'):
        k,v=line.split('=',1);config[k.strip()]=v.strip()
base='http://127.0.0.1:'+config.get('adminPort','8040')
s=requests.Session();s.trust_env=False
headers={'X-Oldap-Admin-Key':config['adminSecret'],'Origin':config['adminOrigin']}
checks=[]
assert s.get(base+'/$/ping',timeout=15).status_code==401;checks.append('Unauthenticated administration refused')
r=s.get(base+'/',headers=headers,timeout=15);r.raise_for_status()
expected=zipfile.ZipFile('/probe/fuseki-server.jar').read('webapp/index.html')
assert r.content==expected;checks.append('Official Apache UI exactly matches pinned distribution')
r=s.get(base+'/$/server',headers=headers,timeout=15);r.raise_for_status();info=r.json()
assert info['version']=='6.2.0' and any(d['ds.name']=='/oldap' for d in info['datasets']);checks.append('Native dataset registered')
graph='urn:oldap:production-private-check:'+uuid.uuid4().hex
query='ASK { GRAPH <'+graph+'> { <urn:item> <urn:value> 1 } }'
def ask():
    r=s.post(base+'/oldap/query',headers={**headers,'Accept':'application/sparql-results+json'},data={'query':query},timeout=20);r.raise_for_status();return r.json()['boolean']
def update(text):
    r=s.post(base+'/oldap/update',headers={**headers,'Content-Type':'application/sparql-update'},data=text.encode(),timeout=20);r.raise_for_status()
assert not ask()
try:
    update('INSERT DATA { GRAPH <'+graph+'> { <urn:item> <urn:value> 1 } }')
    assert ask();checks.append('Private native update/query verified')
finally:
    update('DROP SILENT GRAPH <'+graph+'>')
assert not ask();checks.append('Disposable test graph removed')
print(json.dumps({'status':'passed','scope':'private native UI/protocols; public DNS/TLS/proxy still separate','checks':checks,'ui_sha256':hashlib.sha256(expected).hexdigest()},indent=2))
