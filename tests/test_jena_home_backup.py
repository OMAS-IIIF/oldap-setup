"""Exercise snapshot recovery ordering without Docker, SSH or real storage."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class HomeBackupRecoveryTests(unittest.TestCase):
    def recovery(self, failure='', console=False, native=False):
        """Run actual recovery tasks with fake Docker and injected command failure."""
        play = yaml.safe_load((ROOT / 'oldap-jena-home-backup.yml').read_text())[0]
        tasks = yaml.safe_load((ROOT / 'tasks/jena-home-start.yml').read_text())
        for task in tasks:
            task.pop('delegate_to', None)
            task.pop('args', None)  # Production Compose directory is not used locally.
            if 'retries' in task:
                task.update(retries=1, delay=0)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            log = directory / 'commands.jsonl'
            docker = directory / 'docker'
            docker.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
args = sys.argv[1:]
with open(os.environ['COMMAND_LOG'], 'a') as stream:
    stream.write(json.dumps(args) + '\\n')
failure = os.environ['COMMAND_FAILURE']
if (failure == 'native' and any('8040' in a for a in args) or
    failure == 'storage' and args[:2] == ['start', 'redis'] or
    failure == 'backend' and args[0] == 'exec' or
    failure == 'identity' and args[0] == 'compose' and args[-1] == 'oldap-jena-identity' or
    failure == 'api' and args[0] == 'compose' and args[-1] == 'oldap-api' or
    failure == 'console' and args[0] == 'compose' and args[-1] == 'jena-console'):
    sys.exit(1)
''')
            docker.chmod(0o755)
            fixture = [{'hosts': 'localhost', 'gather_facts': False,
                        'vars': {'ansible_python_interpreter': sys.executable,
                                 'media_writers': play['vars']['media_writers'],
                                 'api_running': {'stdout_lines': ['compose-jena-console-1'] if console else []},
                                 **({'jena_admin_ready_key': 'test-only'} if native else {})},
                        'environment': {'PATH': str(directory) + ':' + os.environ['PATH'],
                                        'COMMAND_LOG': str(log), 'COMMAND_FAILURE': failure},
                        'tasks': tasks}]
            path = directory / 'play.yml'
            path.write_text(yaml.safe_dump(fixture))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(path)],
                                    capture_output=True, text=True)
            return result, [json.loads(line) for line in log.read_text().splitlines()]

    def test_recovery_reconnects_both_consumers_before_ingress(self):
        result, commands = self.recovery()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(commands[0], ['start', 'redis', 'compose-oldap-jena-1'])
        self.assertEqual([c[-1] for c in commands if c[0] == 'compose'],
                         ['oldap-jena-identity', 'oldap-api'])
        self.assertTrue(all('--force-recreate' in c for c in commands if c[0] == 'compose'))
        self.assertEqual(commands[4], ['start', 'caddy'])
        self.assertEqual(commands[-1], ['start', 'oldap-media-caddy'])

    def test_failed_recovery_never_reopens_ingress(self):
        for failure in ('storage', 'backend', 'identity', 'api'):
            with self.subTest(failure=failure):
                result, commands = self.recovery(failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(['start', 'caddy'], commands)
                self.assertNotIn(['start', 'oldap-media-caddy'], commands)

    def test_console_reconnects_before_ingress_and_failure_keeps_ingress_closed(self):
        result, commands = self.recovery(console=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        names = [c[-1] for c in commands if c[0] == 'compose']
        self.assertEqual(names, ['oldap-jena-identity', 'oldap-api', 'jena-console'])
        reconnect = next(i for i,c in enumerate(commands) if c[-1] == 'jena-console')
        self.assertLess(reconnect, commands.index(['start', 'caddy']))
        result, commands = self.recovery(failure='console', console=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(['start', 'caddy'], commands)

    def test_failed_native_administration_readiness_keeps_ingress_closed(self):
        result, commands = self.recovery(failure='native', native=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(['start', 'caddy'], commands)
        self.assertNotIn(['start', 'oldap-media-caddy'], commands)
