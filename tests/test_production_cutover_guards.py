"""Offline failure-path tests for production checkpoint and write-boundary guards."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


containers = module('check-cutover-containers')
boundary = module('cutover-write-boundary')


def fixture(names, running):
    return {name: {'id':name, 'image':'sha256:fixture',
                   'state': {'Running':name in running, 'ExitCode':0, 'OOMKilled':False}}
            for name in names}


class LifecycleTests(unittest.TestCase):
    def test_exact_online_source(self):
        for role, names in [('api', containers.API), ('media', containers.MEDIA)]:
            self.assertEqual(containers.validate(role, 'online', fixture(names, names))['status'], 'passed')

    def test_running_batch_blocks_snapshot(self):
        state = fixture(containers.API | {'oldap-batch-europeana'}, containers.API | {'oldap-batch-europeana'})
        with self.assertRaises(ValueError):
            containers.validate('api', 'online', state)

    def test_frontend_or_image_server_must_not_write_during_snapshot(self):
        for role, names, writer in [('api', containers.API, 'oldap-app'), ('media', containers.MEDIA, 'oldap-imageserver')]:
            with self.assertRaises(ValueError):
                containers.validate(role, 'frozen', fixture(names, {writer}))

    def test_unclean_exit_blocks_snapshot(self):
        for key, value in [('ExitCode', 137), ('ExitCode', 1), ('OOMKilled', True)]:
            state = fixture(containers.API, set())
            state['graphdb']['state'][key] = value
            with self.assertRaises(ValueError):
                containers.validate('api', 'frozen', state)

    def test_private_target_has_no_source_writer_or_ingress(self):
        names = containers.API | containers.TARGET
        running = containers.TARGET | {'oldap-api', 'redis'}
        self.assertEqual(containers.validate('api', 'target-private', fixture(names, running))['status'], 'passed')
        for extra in ['graphdb', 'compose-archive-writer-1', 'caddy']:
            with self.assertRaises(ValueError):
                containers.validate('api', 'target-private', fixture(names, running | {extra}))


class BoundaryTests(unittest.TestCase):
    def test_opening_intent_permanently_fences_automatic_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            boundary.boundary(root, 'check-rollback')
            boundary.boundary(root, 'mark-opening', 'a'*64)
            self.assertEqual(json.loads((root/'target-opened.json').read_text())['state'], 'target-writes-possible')
            for action in ['check-rollback', 'mark-opening']:
                with self.assertRaises(FileExistsError):
                    boundary.boundary(root, action, 'a'*64)

    def test_even_partial_or_symlinked_marker_blocks_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root/'target-opened.json'
            marker.write_text('')
            with self.assertRaises(FileExistsError):
                boundary.boundary(root, 'check-rollback')
            marker.unlink()
            marker.symlink_to(root/'absent')
            with self.assertRaises(FileExistsError):
                boundary.boundary(root, 'check-rollback')

    def test_invalid_acceptance_does_not_publish_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                boundary.boundary(Path(folder), 'mark-opening', 'not-a-hash')
            self.assertFalse((Path(folder)/'target-opened.json').exists())

    def test_public_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.chmod(0o755)
            with self.assertRaises(ValueError):
                boundary.boundary(root, 'check-rollback')


class LockTests(unittest.TestCase):
    def test_ready_requires_exclusive_lock_and_shutdown_releases_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            command = [sys.executable, str(ROOT/'scripts/hold-production-cutover-lock.py'), str(root/'lock')]
            first = subprocess.Popen(command+[str(root/'ready')], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic()+5
                while not (root/'ready').exists() and time.monotonic()<deadline:
                    time.sleep(0.02)
                self.assertTrue((root/'ready').exists())
                other = subprocess.run(command+[str(root/'other')], capture_output=True, timeout=5)
                self.assertNotEqual(other.returncode, 0)
                self.assertFalse((root/'other').exists())
            finally:
                first.terminate()
                first.communicate(timeout=5)
            self.assertFalse((root/'ready').exists())
            self.assertTrue((root/'lock').exists())  # Never replace the shared inode.


if __name__ == '__main__':
    unittest.main()
