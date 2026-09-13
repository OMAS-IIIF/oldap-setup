"""Protect the routine update boundary against full-stack deployment regressions."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class RoutineUpdateTests(unittest.TestCase):
    def test_make_dispatches_update_without_local_secrets(self):
        """Exercise Make expansion with a harmless replacement Ansible executable."""
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'ansible-playbook'
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            executable.chmod(0o755)
            result = subprocess.run(
                ['make', '--no-print-directory', 'deploy-vm',
                 'API_VERSION=v0.2.24', 'APP_VERSION=v0.2.4',
                 'TOOLS_VERSION=v0.3.12', 'HARVESTERS_VERSION=0.1.3',
                 'FASNACHTS_VERSION=v0.1.37', 'AUTH_SECRETS_FILE=/nonexistent'],
                cwd=ROOT, env={**os.environ, 'PATH': directory + ':' + os.environ['PATH']},
                check=True, capture_output=True, text=True,
            )
            self.assertIn('oldap-update.yml', result.stdout)
            self.assertIn('oldap_api_tag=v0.2.24', result.stdout)
            self.assertNotIn('oldap-deploy.yml', result.stdout)
            self.assertNotIn('/nonexistent', result.stdout)

    def test_update_cannot_start_infrastructure_or_reset_configuration(self):
        play = yaml.safe_load((ROOT / 'oldap-update.yml').read_text())[0]
        tasks = play['tasks']
        compose = [t['community.docker.docker_compose_v2'] for t in tasks
                   if 'community.docker.docker_compose_v2' in t]
        self.assertEqual(len(compose), 1)
        self.assertEqual(compose[0]['services'], ['oldap-api', 'oldap-app', 'fasnachts-page'])
        self.assertIs(compose[0]['dependencies'], False)
        self.assertIs(compose[0]['remove_orphans'], False)
        for task in tasks:
            self.assertNotIn('ansible.builtin.template', task)
            self.assertNotIn('ansible.builtin.systemd', task)
            self.assertNotIn('ansible.builtin.apt', task)
        preflight = next(i for i, t in enumerate(tasks) if 'Verify writer compatibility' in t['name'])
        persist = next(i for i, t in enumerate(tasks) if 'ansible.builtin.lineinfile' in t)
        self.assertLess(preflight, persist)
        self.assertEqual(tasks[preflight]['environment'], '{{ release_tags }}')
        self.assertEqual(tasks[persist]['loop'], '{{ release_tags | dict2items }}')
        self.assertIn('--no-deps', tasks[preflight]['ansible.builtin.command']['argv'])
