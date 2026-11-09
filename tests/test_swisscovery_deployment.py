"""Exercise the actual Compose merge and optional batch release boundary."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import yaml
from tests.test_writer_deployment import fixture, render

ROOT = Path(__file__).resolve().parents[1]


class SwisscoveryDeploymentTests(unittest.TestCase):
    def test_batch_inherits_writer_contract_and_keeps_lock_and_limits(self):
        base = (ROOT / 'docker-compose.yml').read_text()
        overlay = (ROOT / 'swisscovery-compose.yml').read_text()
        variables = {name: '/tmp/swisscovery-fixture' for name in re.findall(r'\$\{([A-Z_]+)', base + overlay)}
        variables['OLDAP_HARVESTERS_TAG'] = '0.9.9'
        writer = render('writer-compose.yml.j2', {**fixture(), 'inventory_hostname': 'owner'})
        with tempfile.TemporaryDirectory() as folder:
            empty = Path(folder) / '.env'
            empty.write_text('')
            writer_file = Path(folder) / 'writer.yml'
            writer_file.write_text(writer)
            result = subprocess.run([
                'docker', 'compose', '--profile', '*', '--env-file', str(empty),
                '-f', str(ROOT / 'docker-compose.yml'), '-f', str(writer_file),
                '-f', str(ROOT / 'swisscovery-compose.yml'),
                '-f', str(ROOT / 'harvest-schedule-compose.yml'), 'config', '--format', 'json',
            ], env={**os.environ, **variables}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        services = json.loads(result.stdout)['services']
        batch = services['oldap-harvesters']
        parent = yaml.safe_load(writer)['services']['oldap-harvesters']
        for name, value in parent['environment'].items():
            self.assertEqual(batch['environment'][name], value)
        self.assertFalse(any('RECOVERY' in name for name in batch['environment']))
        self.assertEqual(batch['image'], 'lrosenth/oldap-harvesters:0.9.9-ocr')
        self.assertTrue(batch['profiles'])
        self.assertEqual(float(batch['cpus']), 2)
        self.assertEqual(batch['mem_limit'], str(5 * 1024**3))
        self.assertEqual(batch['entrypoint'][:5], ['flock', '--nonblock', '--conflict-exit-code', '75', '--no-fork'])
        mounts = {volume['target']: volume for volume in batch['volumes']}
        self.assertEqual(mounts['/run/oldap-writer-client']['source'], '/fixture/client')
        self.assertEqual(mounts['/run/oldap-batch/locks']['source'], '/srv/storage/oldap-data/job-locks')
        self.assertTrue(mounts['/run/oldap-batch/run-locked.py']['read_only'])
        self.assertFalse(mounts['/var/lib/swisscovery/locks']['bind']['create_host_path'])
        self.assertEqual(batch['depends_on']['archive-writer']['condition'], 'service_healthy')

    def test_release_checks_precede_version_selection_and_never_harvest(self):
        tasks = yaml.safe_load((ROOT / 'oldap-update.yml').read_text())[0]['tasks']
        check = next(i for i, t in enumerate(tasks) if t.get('ansible.builtin.include_tasks', {}).get('file') == 'tasks/check-swisscovery.yml')
        persist = next(i for i, t in enumerate(tasks) if 'ansible.builtin.lineinfile' in t)
        self.assertLess(check, persist)
        self.assertIn('when', tasks[check])
        checks = yaml.safe_load((ROOT / 'tasks/check-swisscovery.yml').read_text())
        for task in checks:
            command = task.get('ansible.builtin.command', {})
            self.assertNotIn('--write-oldap', command.get('argv', []))
        installer = yaml.safe_load((ROOT / 'oldap-swisscovery-install.yml').read_text())[0]['tasks']
        self.assertFalse(any('community.docker.docker_compose_v2' in t for t in installer))
        self.assertFalse(any('ansible.builtin.template' in t for t in installer))
