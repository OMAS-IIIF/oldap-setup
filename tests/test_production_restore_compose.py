"""Verify bounded configuration selection before any production extraction."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('restore_config', Path(__file__).resolve().parents[1]/'scripts/restore-production-compose.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class RestoreTests(unittest.TestCase):
    def fixture(self, root, extra=None):
        names = ['opt/oldap/compose/.env', 'opt/oldap/compose/docker-compose.yml',
                 'opt/oldap/compose/redis-data/dump.rdb', 'srv/storage/graphdb/data']
        with tarfile.open(root/'api.tar', 'w') as archive:
            for name in names + ([extra] if extra else []):
                member = tarfile.TarInfo(name)
                member.size = 3
                archive.addfile(member, io.BytesIO(b'old'))
        (root/'source-compose.json').write_text('{}')
        artifacts = [{} for _ in range(5)]
        for index, name in [(0, 'api.tar'), (3, 'source-compose.json')]:
            content = (root/name).read_bytes()
            artifacts[index] = {'size':len(content), 'checksum':hashlib.sha256(content).hexdigest()}
        (root/'manifest.json').write_text(json.dumps({'status':'source-frozen','artifacts':artifacts}))

    def test_only_configuration_selected_without_directory_recursion(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(restore.subprocess, 'run') as command:
            root = Path(directory)
            self.fixture(root)
            restore.restore('api', root)
            names = (root/'rollback-config-members.list').read_bytes().split(b'\0')[:-1]
            self.assertEqual(names, [b'opt/oldap/compose/.env', b'opt/oldap/compose/docker-compose.yml'])
            self.assertIn('--no-recursion', command.call_args.args[0])

    def test_bad_hash_or_traversal_never_extracts(self):
        for failure in ['checksum', 'traversal']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory, patch.object(restore.subprocess, 'run') as command:
                root = Path(directory)
                self.fixture(root, 'opt/oldap/compose/../escape' if failure=='traversal' else None)
                if failure=='checksum':
                    (root/'source-compose.json').write_text('[]')
                with self.assertRaises(ValueError):
                    restore.restore('api', root)
                command.assert_not_called()
