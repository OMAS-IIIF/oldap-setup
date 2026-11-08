"""Execute real Ansible recovery tasks with fake Docker; failure must keep ingress closed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class SourceResumeTests(unittest.TestCase):
    def exercise(self, failure='', recreated=False):
        tasks = yaml.safe_load((ROOT/'tasks/production-source-resume.yml').read_text())
        for task in tasks:
            task.pop('delegate_to', None)
            if 'retries' in task:
                task.update(retries=1, delay=0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root/'commands.jsonl'
            fake = '''import json,os,sys
args=sys.argv[1:]
with open(os.environ['TEST_COMMANDS'],'a') as f:f.write(json.dumps(args)+'\\n')
fail=os.environ['TEST_FAILURE']
if args[0]=='inspect':
 if '--format' in args: print('healthy')
 else: print(json.dumps([{'Name':'/'+n,'Id':n+('changed' if fail=='identity' else ''),'Image':('wrong' if fail=='image' else 'image')} for n in args[1:]]))
if fail=='storage' and args[:2]==['start','graphdb']:sys.exit(1)
if fail=='repository' and args[0]=='exec' and 'requests.post' in args[-1]:sys.exit(1)
'''
            for binary in ['docker', 'systemctl']:
                path = root/binary
                path.write_text('#!'+sys.executable+'\n'+fake)
                path.chmod(0o755)
            evidence = json.dumps({'containers': {'source': {'id':'source','image':'image'}}})
            play = [{'hosts':'localhost','gather_facts':False,
                     'vars': {'ansible_python_interpreter':sys.executable, 'source_recreated':recreated,
                              'source_api':{'stdout':evidence}, 'source_media':{'stdout':evidence},
                              'source_timers':{'results':[{'item':'oldap-backup.timer','stdout':'active'},
                                                          {'item':'oldap-harvest.timer','stdout':'inactive'}]}},
                     'environment': {'PATH':str(root)+':'+os.environ['PATH'],
                                     'TEST_COMMANDS':str(log),'TEST_FAILURE':failure}, 'tasks':tasks}]
            path = root/'play.yml'
            path.write_text(yaml.safe_dump(play))
            result = subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(path)],capture_output=True,text=True)
            commands = [json.loads(line) for line in log.read_text().splitlines()]
            return result, commands

    def test_readiness_before_ingress_and_restore_only_active_timers(self):
        result, commands = self.exercise()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        query = next(i for i,c in enumerate(commands) if c[0]=='exec' and 'requests.post' in c[-1])
        self.assertLess(query, commands.index(['start','caddy']))
        self.assertLess(commands.index(['start','caddy']), commands.index(['start','oldap-media-caddy']))
        self.assertIn(['start','oldap-backup.timer'], commands)
        self.assertNotIn(['start','oldap-harvest.timer'], commands)

    def test_identity_storage_or_repository_failure_never_opens_ingress(self):
        for failure in ['identity','storage','repository']:
            with self.subTest(failure=failure):
                result, commands = self.exercise(failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(['start','caddy'], commands)
                self.assertNotIn(['start','oldap-media-caddy'], commands)
                self.assertNotIn(['start','oldap-backup.timer'], commands)

    def test_recreated_containers_require_original_images(self):
        result, commands = self.exercise('identity', recreated=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn(['start','caddy'], commands)
        result, commands = self.exercise('image', recreated=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(['start','caddy'], commands)
