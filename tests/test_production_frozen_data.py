"""Guard new offline preparation and private Redis cache cleanup boundaries."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1]/'scripts'/name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


prepare = load('prepare-production-frozen-data.py')
cache = load('clear-migrated-model-cache.py')


class FrozenDataTests(unittest.TestCase):
    def test_release_archive_rejects_unsafe_members_and_wrong_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'release.tar'
            for name, mode, kind, valid in [('safe/file',0o600,'file',True),('../escape',0o600,'file',False),
                ('/escape',0o600,'file',False),('link',0o600,'link',False),('writable',0o666,'file',False)]:
                with tarfile.open(path,'w') as archive:
                    item=tarfile.TarInfo(name);item.mode=mode
                    if kind=='link': item.type=tarfile.SYMTYPE;item.linkname='/outside';archive.addfile(item)
                    else:item.size=1;archive.addfile(item,io.BytesIO(b'x'))
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if valid:prepare.validate_archive(path,digest)
                else:
                    with self.assertRaises(ValueError):prepare.validate_archive(path,digest)
                with self.assertRaises(ValueError):prepare.validate_archive(path,'0'*64)

    def test_cache_guard_refuses_source_mount_or_running_clients(self):
        root='/srv/storage/oldap-jena-production-test'
        rows=[{'Name':'/redis','Mounts':[{'Destination':'/data','Type':'bind','Source':root+'/data/redis'}]},
              {'Name':'/oldap-api','State':{'Running':False},'Image':'sha256:example','Config':{'Env':['OLDAP_BACKEND=jena','OLDAP_REDIS_URL=redis://redis:6379']}},
              {'Name':'/compose-oldap-jena-identity-1','State':{'Running':False}}]
        for failure in ('none','source','client','other-running'):
            sample=json.loads(json.dumps(rows))
            if failure=='source':sample[0]['Mounts'][0]['Source']='/opt/oldap/compose/redis-data'
            if failure=='client':sample[1]['State']['Running']=True
            calls=[]
            def output(command,**kwargs):
                calls.append(command)
                if command[1]=='ps':return 'redis\ncompose-oldap-jena-1\n'+('oldap-api\n' if failure=='other-running' else '')
                if command[1]=='inspect':return json.dumps(sample).encode()
                return json.dumps({'derived_objects':{'DataModel':2},'retained_entries':3}).encode()
            with patch('socket.gethostname',return_value='dhlab-oldap'),patch.object(cache.os,'geteuid',return_value=0),patch('subprocess.check_output',side_effect=output):
                if failure=='none':
                    self.assertEqual(cache.clear_private_production(root)['status'],'passed')
                    self.assertEqual(len([c for c in calls if c[1]=='run']),2)
                else:
                    with self.assertRaises(ValueError):cache.clear_private_production(root)
                    self.assertFalse(any(c[1]=='run' for c in calls))

class OffhostGateTests(unittest.TestCase):
    def test_every_frozen_artifact_and_manifest_must_match(self):
        gate=load('check-production-offhost-checkpoint.py');sid='test'
        artifacts=[];files={}
        for root,name,local in [('/srv/storage','api.tar','api.tar'),('/data','media.tar','media.tar'),('/srv/storage','source.trig','source.trig'),('/srv/storage','source-compose.json','api-source-compose.json'),('/data','source-compose.json','media-source-compose.json')]:
            artifacts.append({'path':f'{root}/oldap-cutover-{sid}/{name}','size':123,'checksum':'a'*64})
            files[local]={'bytes':123,'sha256':'a'*64}
        blob=json.dumps({'snapshot_id':sid,'status':'source-frozen','artifacts':artifacts}).encode()
        files['manifest.json']={'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}
        good={'status':'passed','snapshot_id':sid,'repository_id':gate.REPOSITORY_ID,'archive':'cutover-test','files':files}
        self.assertEqual(gate.validate(blob,good)['status'],'passed')
        for error in ('id','repo','missing-media','changed-api','changed-manifest'):
            bad=json.loads(json.dumps(good))
            if error=='id':bad['snapshot_id']='old'
            elif error=='repo':bad['repository_id']='wrong'
            elif error=='missing-media':del bad['files']['media.tar']
            elif error=='changed-api':bad['files']['api.tar']['sha256']='b'*64
            else:bad['files']['manifest.json']['bytes']+=1
            with self.subTest(error=error),self.assertRaises(ValueError):gate.validate(blob,bad)


if __name__=='__main__':unittest.main()
