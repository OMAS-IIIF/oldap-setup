"""Run the actual rollback commands with a fake Docker CLI on localhost only.

No Docker daemon, SSH host or deployment files are accessed. The fake process
records commands so failure tests prove source restart remains unreachable.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ActivationTests(unittest.TestCase):
    def run_rollback(self, failure='', containers='oldap-api\ncompose-oldap-jena-1\nredis'):
        """Execute production rescue admission/stop/remove, then a restart sentinel."""
        tasks = yaml.safe_load((ROOT / 'oldap-jena-activate.yml').read_text())[0]['tasks']
        rescue = next(task['rescue'] for task in tasks if 'rescue' in task)
        boundary = next(i for i, task in enumerate(rescue)
                        if task['name'] == 'Restore original application and proxy configuration')
        with tempfile.TemporaryDirectory(prefix='jena-rollback-test-') as temporary:
            directory = Path(temporary)
            log = directory / 'commands.jsonl'
            docker = directory / 'docker'
            docker.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
with open(os.environ['FAKE_DOCKER_LOG'], 'a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1] == os.environ.get('FAKE_DOCKER_FAILURE'):
    sys.exit(1)
if sys.argv[1] == 'ps':
    print(os.environ['FAKE_DOCKER_CONTAINERS'])
''')
            docker.chmod(0o755)
            play = [{'hosts': 'localhost', 'gather_facts': False,
                     'vars': {'ansible_python_interpreter': sys.executable},
                     'environment': {'PATH': str(directory) + ':' + os.environ['PATH'],
                                     'FAKE_DOCKER_LOG': str(log),
                                     'FAKE_DOCKER_FAILURE': failure,
                                     'FAKE_DOCKER_CONTAINERS': containers},
                     'tasks': rescue[:boundary] + [
                         {'name': 'Source restart sentinel',
                          'ansible.builtin.command': {'argv': ['docker', 'source-restart']}}]}]
            playbook = directory / 'test.yml'
            playbook.write_text(yaml.safe_dump(play, sort_keys=False))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local',
                                     str(playbook)], cwd=directory, capture_output=True, text=True,
                                    timeout=60)
            commands = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, commands

    def test_inventory_stop_or_remove_failure_prevents_source_restart(self):
        for failure in ('ps', 'stop', 'rm'):
            with self.subTest(failure=failure):
                result, commands = self.run_rollback(failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(any(command[0] == failure for command in commands), result.stdout)
                self.assertNotIn(['source-restart'], commands)

    def test_missing_containers_are_harmless_and_stop_order_is_preserved(self):
        result, commands = self.run_rollback()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([c[-1] for c in commands if c[0] == 'stop'],
                         ['oldap-api', 'compose-oldap-jena-1', 'redis'])
        self.assertEqual(commands[-1], ['source-restart'])
        result, commands = self.run_rollback(containers='')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any(c[0] in ('stop', 'rm') for c in commands))
        self.assertEqual(commands[-1], ['source-restart'])

    def test_first_cutover_guards_precede_mutations(self):
        activation = yaml.safe_load((ROOT / 'oldap-jena-activate.yml').read_text())[0]['tasks']
        guard = next(i for i, t in enumerate(activation)
                     if t['name'] == 'Refuse first activation after target writes may have started')
        self.assertEqual(activation[guard]['ansible.builtin.assert']['that'], 'not target_opened.stat.exists')
        self.assertLess(guard, next(i for i, t in enumerate(activation) if 'block' in t))
        freeze = yaml.safe_load((ROOT / 'oldap-jena-freeze.yml').read_text())[0]['tasks']
        source = next(i for i, t in enumerate(freeze)
                      if t['name'] == 'Require the GraphDB source before stopping any services')
        self.assertIn('== "graphdb"', freeze[source]['ansible.builtin.command']['argv'][-1])
        self.assertLess(source, next(i for i, t in enumerate(freeze) if 'block' in t))
