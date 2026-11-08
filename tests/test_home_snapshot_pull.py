"""Failure-path acceptance for the actual receiver, without network access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('pull', Path(__file__).parents[1] / 'scripts/pull-home-snapshot.py')
pull = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pull)


class SnapshotPullTests(unittest.TestCase):
    def manifest(self):
        data = {'snapshot_id': 'test', 'status': 'offline-compared'}
        for role, prefix in [('api', '/srv/storage'), ('media', '/data')]:
            content = role.encode()
            data[role] = {'path': f'{prefix}/oldap-jena-snapshot-test/{role}.tar',
                          'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        data['media']['host'] = 'media.home.org'
        return data

    def test_interrupted_pull_is_not_complete_and_can_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def transfer(command, **kwargs):
                role = Path(command[-1]).stem
                if role == 'media':
                    raise subprocess.CalledProcessError(23, command)
                Path(command[-1]).write_bytes(role.encode())
            with patch.object(pull.subprocess, 'check_output', return_value=json.dumps(self.manifest()).encode()), patch.object(pull.subprocess, 'run', side_effect=transfer):
                with self.assertRaises(subprocess.CalledProcessError):
                    pull.pull('test', root, Path('/config'))
            self.assertFalse((root/'snapshots/test').exists())
            transferred = []
            def good(command, **kwargs):
                transferred.append(Path(command[-1]).stem)
                Path(command[-1]).write_bytes(Path(command[-1]).stem.encode())
            with patch.object(pull.subprocess, 'check_output', return_value=json.dumps(self.manifest()).encode()), patch.object(pull.subprocess, 'run', side_effect=good):
                target = pull.pull('test', root, Path('/config'))
                self.assertTrue((target/'manifest.json').exists())
                self.assertEqual(transferred, ['media'])
                with self.assertRaises(FileExistsError):
                    pull.pull('test', root, Path('/config'))

    def test_corrupt_download_never_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(pull.subprocess, 'check_output', return_value=json.dumps(self.manifest()).encode()), patch.object(pull.subprocess, 'run', side_effect=lambda cmd, **kw: Path(cmd[-1]).write_bytes(b'bad')):
                with self.assertRaises(ValueError):
                    pull.pull('test', root, Path('/config'))
            self.assertFalse((root/'snapshots/test').exists())

    def test_remote_path_and_identity_are_not_trusted(self):
        for field, value in [('path', '/etc/shadow'), ('bytes', -1), ('sha256', 'invalid')]:
            data = self.manifest(); data['api'][field] = value
            with self.assertRaises(ValueError):
                pull.validate_manifest(data, 'test')
        with self.assertRaises(ValueError):
            pull.validate_manifest(self.manifest(), 'other')

    def test_changed_ready_marker_prevents_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.manifest(); second = self.manifest(); second['api']['sha256'] = 'a'*64
            with patch.object(pull.subprocess, 'check_output', side_effect=[json.dumps(first).encode(), json.dumps(second).encode()]), patch.object(pull.subprocess, 'run', side_effect=lambda cmd, **kw: Path(cmd[-1]).write_bytes(Path(cmd[-1]).stem.encode())):
                with self.assertRaises(ValueError):
                    pull.pull('test', Path(directory), Path('/config'))
            self.assertFalse((Path(directory)/'snapshots/test').exists())

    def test_same_size_corrupt_partial_is_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root/'incoming/test'; stage.mkdir(parents=True)
            (stage/'api.tar').write_bytes(b'bad')
            calls = []
            def transfer(command, **kwargs):
                calls.append(Path(command[-1]).stem)
                Path(command[-1]).write_bytes(Path(command[-1]).stem.encode())
            with patch.object(pull.subprocess, 'check_output', return_value=json.dumps(self.manifest()).encode()), patch.object(pull.subprocess, 'run', side_effect=transfer):
                target = pull.pull('test', root, Path('/config'))
            self.assertEqual(calls, ['api', 'media'])
            self.assertEqual((target/'api.tar').read_bytes(), b'api')

    def test_production_endpoints_are_explicit_and_cannot_mix_with_home(self):
        data=self.manifest()
        with self.assertRaises(ValueError):
            pull.validate_manifest(data,'test','production')
        data['media']['host']='dhlab-iii.dhlab.unibas.ch'
        with self.assertRaises(ValueError):
            pull.validate_manifest(data,'test','home')
        calls=[]
        def transfer(command, **kwargs):
            calls.append(command)
            Path(command[-1]).write_bytes(Path(command[-1]).stem.encode())
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(pull.subprocess,'check_output',return_value=json.dumps(data).encode()) as fetch, patch.object(pull.subprocess,'run',side_effect=transfer):
                target=pull.pull('test',Path(directory),Path('/production-config'),'production')
                self.assertTrue((target/'manifest.json').exists())
                self.assertEqual(fetch.call_args.args[0][-3],'dhlab-oldap.dhlab.unibas.ch')
            self.assertTrue(calls[0][-2].startswith('dhlab-oldap.dhlab.unibas.ch:'))
            self.assertTrue(calls[1][-2].startswith('dhlab-iii.dhlab.unibas.ch:'))
