"""Exercise actual maintenance ordering with a blocked or unsupported mobile worker."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class MobileDrainTests(unittest.TestCase):
    def test_api_stays_available_until_mobile_drain_succeeds(self):
        for failure in ('', 'capability', 'drain'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                log = directory / 'commands.jsonl'
                docker = directory / 'docker'
                docker.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
args = sys.argv[1:]
with open(os.environ['COMMAND_LOG'], 'a') as stream:
    stream.write(json.dumps(args) + '\\n')
failure = os.environ['COMMAND_FAILURE']
if failure == 'capability' and args[0] == 'exec':
    sys.exit(1)
if failure == 'drain' and args[0] == 'stop' and args[-1] == 'oldap-mobile-media-worker':
    sys.exit(1)
''')
                docker.chmod(0o755)
                tasks = yaml.safe_load((ROOT / 'tasks/jena-home-quiesce.yml').read_text())
                for task in tasks:
                    task.pop('delegate_to', None)
                play = [{'hosts': 'localhost', 'gather_facts': False,
                         'vars': {'ansible_python_interpreter': sys.executable,
                                  'mobile_stop_signal': 'SIGTERM',
                                  'media_writers': ['oldap-mediahelper', 'oldap-ingest-worker',
                                                    'oldap-export-worker', 'oldap-mobile-media-worker']},
                         'environment': {'PATH': str(directory) + ':' + os.environ['PATH'],
                                         'COMMAND_LOG': str(log), 'COMMAND_FAILURE': failure},
                         'tasks': tasks}]
                path = directory / 'play.yml'
                path.write_text(yaml.safe_dump(play))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(path)], capture_output=True, text=True)
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                api_stop = ['stop', '--timeout', '90', 'caddy']
                if failure:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(api_stop, calls)
                    if failure == 'capability':
                        self.assertFalse(any(call[0] == 'stop' for call in calls))
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    drain = ['stop', '--signal', 'SIGTERM', '--timeout', '-1', 'oldap-mobile-media-worker']
                    self.assertLess(calls.index(drain), calls.index(api_stop))
