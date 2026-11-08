#!/usr/bin/env python3
"""Activate a reviewed YAML-derived field plan inside an isolated Jena API.

Reads credentials from that container's environment, never prints tokens/passwords.
Only an absent index or exactly matching configuration is admitted. This helper
is for the isolated rehearsal, not arbitrary updates to an existing live index.
"""
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote
import requests


def activate(plan):
    """Create the reviewed project index once and verify its exact field map."""
    if os.environ.get('OLDAP_BACKEND') != 'jena':
        raise ValueError('Jena API required')
    base = 'http://127.0.0.1:8000'
    session = requests.Session()
    session.trust_env = False
    response = session.post(base+'/admin/auth/'+quote(os.environ['OLDAP_AUTH_ADMIN_USER'],safe=''),
                            json={'password':os.environ['OLDAP_AUTH_ADMIN_PASSWORD']},timeout=60)
    response.raise_for_status()
    session.headers['Authorization'] = 'Bearer '+response.json()['accessToken']
    url = base+'/admin/fulltext/'+quote(plan['project'],safe='')
    response=session.get(url,timeout=60);response.raise_for_status();before=response.json()
    desired={'graph':plan['graph'],'fields':plan['fields']}
    if before['configuration'] not in [None,desired]:
        raise ValueError('Existing field configuration differs from reviewed plan')
    if before['configuration'] is None:
        response=session.put(url,json={'configuration':desired,'expectedRevision':before['revision']},timeout=180)
        response.raise_for_status()
    response=session.get(url,timeout=60);response.raise_for_status();after=response.json()
    if after['status']!='active' or after['configuration']!=desired:
        raise ValueError('Fulltext activation verification failed')
    return {'status':'passed','project':plan['project'],'fields':len(plan['fields']),'revision':after['revision']}


if __name__ == '__main__':
    print(json.dumps(activate(json.loads(Path(sys.argv[1]).read_text())),indent=2))
