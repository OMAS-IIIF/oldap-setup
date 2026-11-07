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


class BackupCompletionOrderingTests(unittest.TestCase):
    def test_recovery_precedes_hash_and_failed_phases_never_publish(self):
        """Execute the play's real block/always topology with injected failures.

        Replace only task side effects with event logging. This tests Ansible's
        failure propagation, rather than assuming how always blocks behave.
        """
        play = yaml.safe_load((ROOT / 'oldap-jena-home-backup.yml').read_text())[0]
        tasks = play['tasks']
        start = next(i for i, task in enumerate(tasks)
                     if task['name'] == 'Pre-copy media and operational state while services are online')
        cases = [(True, failure) for failure in (
            '', 'Pre-copy media and operational state while services are online',
            'Finalize media staging from stopped sources',
            'Verify finalized media staging against stopped sources',
            'Compare API archive with still-stopped source files',
            'Recover the home stack in namespace order',
            'Compare media archive with frozen staging', 'Hash API snapshot')]
        cases += [(False, failure) for failure in (
            '', 'Archive media directly from stopped sources',
            'Compare media archive with stopped sources')]
        for precopy, failure in cases:
            with self.subTest(precopy=precopy, failure=failure), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                log = directory / 'events.jsonl'
                recorder = directory / 'record.py'
                recorder.write_text('import json,sys\n'
                                    'with open(sys.argv[1], "a") as f: f.write(json.dumps(sys.argv[3])+"\\n")\n'
                                    'sys.exit(1 if sys.argv[2]==sys.argv[3] else 0)\n')

                def substitute(task):
                    result = {'name': task['name']}
                    if 'when' in task:
                        result['when'] = task['when']
                    if 'block' in task:
                        result['block'] = [substitute(item) for item in task['block']]
                        if 'always' in task:
                            result['always'] = [substitute(item) for item in task['always']]
                    else:
                        result['ansible.builtin.command'] = {'argv': [
                            sys.executable, str(recorder), str(log), failure, task['name']]}
                    return result

                fixture = [{'hosts': 'localhost', 'gather_facts': False,
                            'vars': {'ansible_python_interpreter': sys.executable,
                                     'home_media_precopy': precopy, 'home_snapshot_publish': True},
                            'tasks': [substitute(task) for task in tasks[start:]]}]
                path = directory / 'play.yml'
                path.write_text(yaml.safe_dump(fixture))
                result = subprocess.run(
                    ['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(path)],
                    capture_output=True, text=True)
                events = [json.loads(line) for line in log.read_text().splitlines()]
                recovery = 'Recover the home stack in namespace order'
                ready = 'Publish ready marker last after both archives are accessible'
                if failure == 'Pre-copy media and operational state while services are online':
                    self.assertNotIn(recovery, events)
                else:
                    self.assertIn(recovery, events)
                if failure:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(ready, events)
                    if failure != 'Hash API snapshot':
                        self.assertNotIn('Hash API snapshot', events)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    if precopy:
                        self.assertNotIn('Archive media directly from stopped sources', events)
                        self.assertLess(events.index('Verify finalized media staging against stopped sources'),
                                        events.index(recovery))
                        self.assertLess(events.index(recovery),
                                        events.index('Archive frozen media staging while services are online'))
                    else:
                        self.assertNotIn('Finalize media staging from stopped sources', events)
                        self.assertNotIn('Archive frozen media staging while services are online', events)
                        self.assertLess(events.index('Compare media archive with stopped sources'),
                                        events.index(recovery))
                    self.assertLess(events.index(recovery), events.index('Hash API snapshot'))
                    completed = 'Read completion time after successful recovery and archive hashing'
                    self.assertLess(events.index('Hash media snapshot'), events.index(completed))
                    self.assertLess(events.index(completed), events.index('Record completed snapshot manifest'))
                    self.assertLess(events.index('Record completed snapshot manifest'), events.index(ready))
