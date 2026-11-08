"""Backup reporting must not mistake process exit or email submission for recovery."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('job',Path(__file__).parents[1]/'scripts/run-jena-backup.py')
job=importlib.util.module_from_spec(spec);spec.loader.exec_module(job)


def manifest(snapshot_id):
    result={'snapshot_id':snapshot_id,'status':'offline-compared'}
    for role,prefix in [('api','/srv/storage'),('media','/data')]:
        result[role]={'path':f'{prefix}/oldap-jena-snapshot-{snapshot_id}/{role}.tar',
                      'bytes':123,'sha256':hashlib.sha256(role.encode()).hexdigest()}
    result['media']['host']='dhlab-iii.dhlab.unibas.ch'
    return result


class BackupJobTests(unittest.TestCase):
    def test_success_requires_publication_and_successful_mail(self):
        for failure in ('','process','exception','missing-marker','bad-marker','mail'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); mails=[]
                def run(command, **kwargs):
                    if command[0]=='mail':
                        mails.append((command,kwargs['input']))
                        return subprocess.CompletedProcess(command,1 if failure=='mail' else 0)
                    if failure=='exception':raise OSError('sensitive error detail')
                    kwargs['stdout'].write('PRIVATE TOKEN MUST STAY IN LOG\n')
                    snapshot_id=next(x.split('=',1)[1] for x in command if x.startswith('snapshot_id='))
                    if failure!='missing-marker':
                        path=root/f'oldap-jena-snapshot-{snapshot_id}'
                        path.mkdir(); data=manifest(snapshot_id)
                        if failure=='bad-marker':data['media']['path']='/wrong'
                        (path/'ready.json').write_text(json.dumps(data))
                    return subprocess.CompletedProcess(command,1 if failure=='process' else 0)
                with patch.object(job,'LOG_ROOT',root/'logs'),patch.object(job,'SNAPSHOT_ROOT',root),patch.object(job.subprocess,'run',side_effect=run),patch.dict(job.os.environ,{'HARVEST_MAIL_TO':'test@example.org','HARVEST_MAIL_FROM':'test@example.org'}):
                    status=job.run_backup()
                self.assertEqual(status,0 if not failure else 1)
                self.assertEqual(len(mails),1)
                command,body=mails[0]
                self.assertNotIn('PRIVATE TOKEN',body);self.assertNotIn('sensitive error',body)
                self.assertIn('SUCCESS' if failure in ('','mail') else 'FAILURE',command[command.index('-s')+1])

    def test_marker_identity_type_and_host_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ready.json'
            for change in ('id','status','bytes','hash','host'):
                data=manifest('test')
                if change=='id':data['snapshot_id']='other'
                if change=='status':data['status']='pending'
                if change=='bytes':data['api']['bytes']=True
                if change=='hash':data['api']['sha256']='invalid'
                if change=='host':data['media']['host']='media.home.org'
                path.write_text(json.dumps(data))
                with self.subTest(change=change),self.assertRaises(ValueError):job.check_ready(path,'test')

    def test_mail_test_never_runs_a_snapshot(self):
        with patch.object(job,'notify',return_value=True) as notify,patch.object(job,'run_backup') as backup,patch.object(job.os,'geteuid',return_value=0),patch.object(job.socket,'gethostname',return_value='dhlab-oldap'),patch('sys.argv',['run-jena-backup.py','--notification-test','failure']):
            self.assertEqual(job.main(),0)
            backup.assert_not_called();notify.assert_called_once_with(False,'notification-test','No backup log',test=True)
