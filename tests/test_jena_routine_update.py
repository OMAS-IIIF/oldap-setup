"""Image-only update contracts; fake Docker exercises failure and rollback paths."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('routine', ROOT / 'scripts/update-jena-applications.py')
routine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routine)
IMAGE = 'lrosenth/oldap-api@sha256:' + 'a' * 64
BATCH = 'lrosenth/oldap-harvesters@sha256:' + 'b' * 64


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = 'SECRET="unchanged=$value"\nCOMPOSE_FILE=docker-compose.yml\nOLDAP_EUROPEANA_COMPOSE_FILE=docker-compose.yml:batch-europeana.yml\n'
        (self.root / '.env').write_text(self.env)
        self.original = {'oldap-api': {'image': 'old-api', 'environment': {'OLDAP_BACKEND': 'jena'}},
                         'oldap-jena-identity': {'image': 'old-api'}, 'oldap-jena': {'image': 'java'},
                         'redis': {'image': 'redis'}, 'fasnachts-page': {'image': 'frontend'}}
        self.write('docker-compose.yml', self.original)
        self.write('batch-europeana.yml', {'oldap-harvesters': {'image': 'old-batch', 'environment': {'OLDAP_BACKEND': 'jena'}}})
        self.locks = [self.root / name for name in ('maintenance.lock', 'recovery.lock')]
        for p in self.locks:
            p.touch()
        self.starts, self.calls = [], []
        self.fail_activation = False
        self.fail_pull = False
        self.images = {s: d['image'] for s, d in self.original.items()}

    def write(self, name, services):
        (self.root / name).write_text(json.dumps({'services': services}))

    def compose(self, root, files, *args):
        self.calls.append(args)
        if args == ('config', '--format', 'json'):
            merged = {}
            for p in files:
                for name, value in json.loads(p.read_text())['services'].items():
                    merged.setdefault(name, {}).update(value)
            return json.dumps({'services': merged})
        self.fail('Unexpected compose command: ' + repr(args))

    def command(self, args, **kwargs):
        self.calls.append(args)
        if args[:2] == ['docker', 'pull'] and self.fail_pull:
            raise RuntimeError('Registry unavailable')
        if args[:3] == ['docker', 'image', 'inspect']:
            return json.dumps([{'Id': args[-1]}])
        return ''

    def container(self, root, files, name):
        return {'Id': 'container-' + name, 'Image': self.images[name]}

    def activate(self, root, files, services):
        self.starts.append(set(services))
        if self.fail_activation and len(self.starts) == 1:
            raise RuntimeError('Unhealthy new API')
        current = json.loads(self.compose(root, files, 'config', '--format', 'json'))['services']
        for service in services:
            self.images[service] = current[service]['image']

    def apply(self, images):
        with patch.object(routine, 'LOCK_PATHS', self.locks), patch.object(routine, 'compose', self.compose), \
             patch.object(routine, 'command', self.command), patch.object(routine, 'container', self.container), \
             patch.object(routine, 'activate', self.activate):
            return routine.apply(self.root, images)

    def test_update_preserves_secrets_and_couples_api_then_replay_is_noop(self):
        result = self.apply({'api': IMAGE, 'harvesters': BATCH})
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(self.starts, [{'oldap-api', 'oldap-jena-identity'}])
        self.assertIn('SECRET="unchanged=$value"\n', (self.root / '.env').read_text())
        self.assertEqual(json.loads((self.root/'docker-compose.yml').read_text())['services'], self.original)
        chosen = routine.selections(self.root, routine.environment((self.root/'.env').read_text()))
        batch = json.loads(self.compose(self.root, chosen['harvesters'], 'config', '--format', 'json'))['services']
        self.assertEqual(batch['oldap-api']['image'], IMAGE)
        self.assertEqual(batch['oldap-harvesters']['image'], BATCH)
        self.assertEqual(self.apply({'api': IMAGE, 'harvesters': BATCH})['status'], 'unchanged')
        self.assertEqual(len(self.starts), 1)

    def test_failed_pull_changes_nothing(self):
        self.fail_pull = True
        with self.assertRaisesRegex(RuntimeError, 'Registry'):
            self.apply({'api': IMAGE})
        self.assertEqual((self.root/'.env').read_text(), self.env)
        self.assertFalse(list(self.root.glob('routine-*')))
        self.assertEqual(self.starts, [])

    def test_failed_activation_restores_config_and_restarts_previous_pair(self):
        self.fail_activation = True
        with self.assertRaisesRegex(RuntimeError, 'preceding selection restored'):
            self.apply({'api': IMAGE})
        self.assertEqual((self.root/'.env').read_text(), self.env)
        self.assertFalse((self.root/'routine-images.yml').exists())
        self.assertEqual(self.images['oldap-api'], 'old-api')
        self.assertEqual(len(self.starts), 2)
        self.assertTrue(list(self.root.glob('routine-update-*/manifest.json')))

    def test_busy_lock_refuses_update(self):
        with self.locks[0].open('r+') as owner:
            routine.fcntl.flock(owner, routine.fcntl.LOCK_EX | routine.fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.apply({'api': IMAGE})
        self.assertEqual(self.calls, [])

    def test_partial_later_release_preserves_earlier_pins(self):
        self.apply({'api': IMAGE})
        self.apply({'fasnacht': 'lrosenth/fasnachts-page@sha256:' + 'c'*64})
        data = json.loads((self.root/'routine-images.yml').read_text())['services']
        self.assertEqual(data['oldap-api']['image'], IMAGE)
        self.assertEqual(set(data), {'oldap-api', 'oldap-jena-identity', 'fasnachts-page'})

    def test_batch_only_release_never_starts_jobs(self):
        self.apply({'harvesters': BATCH})
        self.assertEqual(self.starts, [set()])
        self.assertEqual(routine.environment((self.root/'.env').read_text())['COMPOSE_FILE'], 'docker-compose.yml')

    def test_home_overlay_selection_and_explicit_production_selection(self):
        for name in ('jena-compose.yml', 'jena-harvesters-compose.yml', 'swisscovery-compose.yml', 'jena-swisscovery-compose.yml'):
            self.write(name, {})
        chosen = routine.selections(self.root, {'COMPOSE_FILE': 'docker-compose.yml:jena-compose.yml'})
        self.assertEqual(chosen['harvesters_ocr'][-1].name, 'jena-swisscovery-compose.yml')
        chosen = routine.selections(self.root, routine.environment(self.env))
        self.assertEqual(chosen['harvesters'][-1].name, 'batch-europeana.yml')

    def test_invalid_images_graphdb_and_missing_identity_fail_closed(self):
        for value in ({}, {'unknown': IMAGE}, {'api': 'lrosenth/oldap-api:latest'}, {'tools': IMAGE}):
            with self.assertRaises(ValueError):
                routine.release_images(value)
        current = {'core': self.original}
        self.original['oldap-api']['environment']['OLDAP_BACKEND'] = 'graphdb'
        with self.assertRaises(ValueError): routine.plan({'api': IMAGE}, current)
        self.original['oldap-api']['environment']['OLDAP_BACKEND'] = 'jena'
        del self.original['oldap-jena-identity']
        with self.assertRaises(ValueError): routine.plan({'api': IMAGE}, current)

    def test_absent_optional_tool_is_reported_without_adding_service(self):
        result = self.apply({'tools': 'lrosenth/oldap-tools@sha256:' + 'd'*64})
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(result['plan'][0]['status'], 'not-installed')
        self.assertEqual(self.starts, [])

    def test_selector_cannot_escape_root_or_use_symlinks(self):
        (self.root/'link.yml').symlink_to(self.root/'docker-compose.yml')
        for selection in ('', 'link.yml', '../outside.yml'):
            with self.assertRaises(ValueError): routine.paths(self.root, selection)
        with self.assertRaises(ValueError): routine.environment('COMPOSE_FILE=a\nCOMPOSE_FILE=b\n')

    def test_activation_orders_identity_before_api_without_dependencies(self):
        calls = []
        with patch.object(routine, 'compose', side_effect=lambda root, files, *args: calls.append(args)), \
             patch.object(routine, 'container', return_value={'Id': 'api-id'}), \
             patch.object(routine, 'command', return_value=''):
            routine.activate(self.root, [], {'oldap-api', 'oldap-jena-identity', 'fasnachts-page'})
        self.assertEqual([c[-1] for c in calls], ['oldap-jena-identity', 'oldap-api', 'fasnachts-page'])
        self.assertTrue(all('--no-deps' in c and '--wait' in c for c in calls))

    def test_managed_override_cannot_contain_infrastructure(self):
        self.write('routine-images.yml', {'redis': {'image': IMAGE}})
        (self.root/'.env').write_text(self.env.replace('COMPOSE_FILE=docker-compose.yml\n',
                                                     'COMPOSE_FILE=docker-compose.yml:routine-images.yml\n'))
        with self.assertRaisesRegex(ValueError, 'application image'):
            self.apply({'api': IMAGE})
        self.assertEqual(self.starts, [])

    def test_real_compose_preserves_every_non_image_field(self):
        # Local parser only: config never pulls or starts a container.
        import shutil
        if not shutil.which('docker'):
            self.skipTest('Docker Compose unavailable')
        before = json.loads(routine.compose(self.root, [self.root/'docker-compose.yml'], 'config', '--format', 'json'))
        self.write('candidate.yml', {'oldap-api': {'image': IMAGE}, 'oldap-jena-identity': {'image': IMAGE}})
        after = json.loads(routine.compose(self.root, [self.root/'docker-compose.yml', self.root/'candidate.yml'], 'config', '--format', 'json'))
        for name in ('oldap-api','oldap-jena-identity'):
            before['services'][name]['image'] = IMAGE
        self.assertEqual(after, before)

    def test_preview_reports_images_without_mutation(self):
        selected = routine.selections(self.root, routine.environment(self.env))
        with patch.object(routine, 'compose', self.compose):
            current = routine.configs(self.root, selected)
            result = routine.plan({'api': IMAGE}, current)
        self.assertEqual(result[0]['services'], ['oldap-api', 'oldap-jena-identity'])
        self.assertEqual((self.root/'.env').read_text(), self.env)
        self.assertFalse(list(self.root.glob('routine-*')))

    def test_apply_with_real_compose_parser_changes_only_images(self):
        import shutil
        if not shutil.which('docker'):
            self.skipTest('Docker Compose unavailable')
        real_command = routine.command
        def commands(args, **kwargs):
            if args[:2] == ['docker', 'compose']:
                return real_command(args, **kwargs)
            return self.command(args, **kwargs)
        with patch.object(routine, 'LOCK_PATHS', self.locks), \
             patch.object(routine, 'command', commands), patch.object(routine, 'container', self.container), \
             patch.object(routine, 'activate', self.activate):
            result = routine.apply(self.root, {'api': IMAGE, 'harvesters': BATCH})
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(self.starts, [{'oldap-api','oldap-jena-identity'}])


    def test_real_preview_cli_emits_no_environment_secrets(self):
        import shutil, subprocess, sys
        if not shutil.which('docker'):
            self.skipTest('Docker Compose unavailable')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/update-jena-applications.py'),
                                 '--root', str(self.root), '--images', json.dumps({'api': IMAGE})],
                                capture_output=True,text=True,check=True)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'preview')
        self.assertTrue(report['plan'][0]['configuration_change'])
        self.assertNotIn('SECRET', result.stdout)
        self.assertEqual((self.root/'.env').read_text(), self.env)
        self.assertFalse(list(self.root.glob('routine-*')))


class MakeTargetsTests(unittest.TestCase):
    def test_all_four_targets_select_correct_host_and_mode_without_vault(self):
        import os, subprocess
        with tempfile.TemporaryDirectory(prefix='release selection ') as folder:
            fake = Path(folder)/'ansible-playbook'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            fake.chmod(0o755)
            manifest = Path(folder)/'release.json'
            manifest.write_text(json.dumps({'api': IMAGE}))
            for target in ('plan-home','plan-vm','deploy-home','deploy-vm'):
                result = subprocess.run(['make','--no-print-directory',target,'RELEASE_FILE='+str(manifest)],
                                        cwd=ROOT, env={**os.environ,'PATH':folder+':'+os.environ['PATH']},
                                        capture_output=True,text=True,check=True)
                self.assertIn('oldap-jena-update.yml',result.stdout)
                self.assertIn('oldap_home' if target.endswith('home') else 'oldap_prod',result.stdout)
                self.assertIn('oldap_update_apply='+('true' if target.startswith('deploy') else 'false'),result.stdout)
                self.assertNotIn('--ask-vault-pass',result.stdout)
                self.assertIn(str(manifest),result.stdout)
            rejected = subprocess.run(['make','deploy-vm','API_VERSION=v99.0.0'],cwd=ROOT,
                                      capture_output=True,text=True)
            self.assertNotEqual(rejected.returncode,0)
            self.assertIn('Use RELEASE_FILE',rejected.stderr)
