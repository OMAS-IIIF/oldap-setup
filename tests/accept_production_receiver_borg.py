"""Run on the office Mac after installing receiver scripts, using Homebrew Python.

Creates a disposable encrypted repository and five synthetic pairs. Uses actual
Borg create/extract/prune/compact; maps source operations to temporary directories.
No production SSH, mail, schedules or real backup repository are modified.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('r', '/Users/rosenth/OLDAP_BACKUP/jena/tools/run-production-backup-receiver.py')
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
original_output=subprocess.check_output
with tempfile.TemporaryDirectory(prefix='oldap-borg-receiver-') as temporary:
    base=Path(temporary); root=base/'receiver'; root.mkdir(); (root/'receipts').mkdir()
    repo=root/'borg'; credentials=base/'credentials.json'
    env={k:v for k,v in os.environ.items() if not k.startswith('BORG_')}
    env.update(BORG_PASSPHRASE=secrets.token_urlsafe(32), BORG_CACHE_DIR=str(base/'cache'), BORG_SECURITY_DIR=str(base/'security'))
    subprocess.run([r.BORG,'init','--encryption=repokey-blake2',str(repo)],env=env,check=True)
    rid=json.loads(original_output([r.BORG,'info','--json',str(repo)],env=env))['repository']['id']
    credentials.write_text(json.dumps({'repository':str(repo),'repository_id':rid,'passphrase':env['BORG_PASSPHRASE']}));credentials.chmod(0o600)
    source={role:base/role for role in ('api','media')}
    for path in source.values():path.mkdir()
    manifests=[]; receipts={}
    now=datetime.now(timezone.utc)
    for index in range(5):
        when=now-timedelta(days=4-index)
        sid=when.strftime('%Y%m%dT%H%M%SZ')+'-1234abcd'
        manifest={'snapshot_id':sid,'status':'offline-compared','completed_at':now.isoformat()}
        target=root/'snapshots'/sid;target.mkdir(parents=True)
        for role,prefix in [('api','/srv/storage'),('media','/data')]:
            contents=(role+str(index)).encode()
            manifest[role]={'path':f'{prefix}/oldap-jena-snapshot-{sid}/{role}.tar','bytes':len(contents),'sha256':hashlib.sha256(contents).hexdigest()}
            (target/(role+'.tar')).write_bytes(contents)
            remote=source[role]/sid;remote.mkdir();(remote/(role+'.tar')).write_bytes(contents)
        manifest['media']['host']='dhlab-iii.dhlab.unibas.ch'
        (source['api']/sid/'ready.json').write_text(json.dumps(manifest))
        (target/'manifest.json').write_text(json.dumps(manifest));manifests.append(manifest)
        if index<4:
            subprocess.run([r.BORG,'create','--timestamp',when.strftime('%Y-%m-%dT%H:%M:%S'),str(repo)+'::production-'+sid,'api.tar','media.tar','manifest.json'],cwd=target,env=env,check=True)
    def directory(role,sid):return source[role]/sid
    def remote(role,action,receipt=None):
        if action=='inventory':
            return {p.name: r.transport.read_json(p/'received.json') for p in source[role].iterdir() if (p/'received.json').exists()}
        return r.transport.operate(role,{'action':action,'receipt':receipt})
    def output(command,**kwargs):
        if command[0]=='ssh':return json.dumps(manifests[-1]).encode()
        return original_output(command,**kwargs)
    with patch.object(r,'ROOT',root),patch.object(r,'CREDENTIALS',credentials),patch.object(r.transport,'REPOSITORY_ID',rid),patch.object(r.transport,'snapshot_directory',side_effect=directory),patch.dict(os.environ,{'BORG_CACHE_DIR':str(base/'cache'),'BORG_SECURITY_DIR':str(base/'security')}):
        instance=r.Receiver();instance.env.update(BORG_CACHE_DIR=str(base/'cache'),BORG_SECURITY_DIR=str(base/'security'))
        for manifest in manifests[:-1]:
            sid=manifest['snapshot_id']; name='production-'+sid
            aid=instance.verify_borg(name,manifest)
            receipt={'repository_id':rid,'archive':name,'archive_id':aid,'manifest':manifest,'verified_at':now.isoformat()}
            r.transport.atomic_json(root/'receipts'/(sid+'.json'),receipt)
            remote('media','acknowledge',receipt);remote('api','acknowledge',receipt)
        with patch.object(instance,'remote',side_effect=remote),patch.object(r.subprocess,'check_output',side_effect=output):
            sid=instance.backup()
            assert sid==manifests[-1]['snapshot_id']
            assert instance.backup()==sid
        assert sum((p/'api.tar').exists() for p in source['api'].iterdir())==3
        assert sum((p/'media.tar').exists() for p in source['media'].iterdir())==3
        assert sum((p/'api.tar').exists() for p in (root/'snapshots').iterdir())==2
        assert len(list((root/'receipts').glob('*.json')))==5
        remaining=json.loads(instance.borg('list','--json',str(repo)))['archives']
        assert len(remaining)==5
        # A new archive whose contents contradict its manifest must fail on restored SHA.
        bad=root/'bad';bad.mkdir()
        manifest=manifests[-1]
        (bad/'manifest.json').write_text(json.dumps(manifest))
        (bad/'api.tar').write_bytes(b'xxxx');(bad/'media.tar').write_bytes(b'yyyyyy')
        instance.borg('create',str(repo)+'::corrupt-fixture','api.tar','media.tar','manifest.json',cwd=bad)
        try:instance.verify_borg('corrupt-fixture',manifest)
        except ValueError:pass
        else:raise AssertionError('Corrupt source digest accepted')
        instance.borg('check','--verify-data',str(repo))
    print(json.dumps({'status':'passed','scope':'disposable encrypted Borg with five synthetic matched pairs; create, streamed restore hashes, acknowledgements, retention and retry','server_pairs':3,'office_pairs':2,'borg_archives_before_corruption_fixture':5,'corrupt_digest_refused':True,'production_data_untouched':True},indent=2))
