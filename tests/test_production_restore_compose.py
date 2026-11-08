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
        names = ['opt/oldap/compose/.env', 'opt/oldap/compose/docker-compose.yml', 'opt/oldap/compose/Caddyfile',
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
        with tempfile.TemporaryDirectory() as directory, patch.object(restore.subprocess, 'run') as command, patch.object(restore, 'unexpected_inputs', return_value=[]):
            root = Path(directory)
            self.fixture(root)
            restore.restore('api', root)
            names = (root/'rollback-config-members.list').read_bytes().split(b'\0')[:-1]
            self.assertEqual(names, [b'opt/oldap/compose/.env', b'opt/oldap/compose/docker-compose.yml', b'opt/oldap/compose/Caddyfile'])
            self.assertIn('--no-recursion', command.call_args.args[0])

    def test_bad_hash_or_traversal_never_extracts(self):
        for failure in ['checksum', 'traversal']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory, patch.object(restore.subprocess, 'run') as command, patch.object(restore, 'unexpected_inputs', return_value=[]):
                root = Path(directory)
                self.fixture(root, 'opt/oldap/compose/../escape' if failure=='traversal' else None)
                if failure=='checksum':
                    (root/'source-compose.json').write_text('[]')
                with self.assertRaises(ValueError):
                    restore.restore('api', root)
                command.assert_not_called()

    def test_preflight_does_not_extract_or_create_selection(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(restore.subprocess, 'run') as command, patch.object(restore, 'unexpected_inputs', return_value=[]):
            root = Path(directory)
            self.fixture(root)
            before = set(root.iterdir())
            restore.restore('api', root, check_only=True)
            self.assertEqual(before, set(root.iterdir()))
            command.assert_not_called()

    def test_duplicate_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(restore.subprocess, 'run') as command, patch.object(restore, 'unexpected_inputs', return_value=[]):
            root = Path(directory)
            self.fixture(root, 'opt/oldap/compose/.env')
            with self.assertRaises(ValueError):
                restore.restore('api', root)
            command.assert_not_called()

    def test_media_uses_service_env_files_without_global_dotenv(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(restore.subprocess, 'run') as command, patch.object(restore, 'unexpected_inputs', return_value=[]):
            root=Path(directory)
            with tarfile.open(root/'media.tar','w') as archive:
                for name in sorted(restore.REQUIRED_FILES['media']):
                    member=tarfile.TarInfo('opt/oldap-mediaserver/compose/'+name)
                    member.size=3;archive.addfile(member,io.BytesIO(b'old'))
            (root/'source-compose.json').write_text('{}')
            artifacts=[{} for _ in range(5)]
            for index,name in [(1,'media.tar'),(4,'source-compose.json')]:
                data=(root/name).read_bytes()
                artifacts[index]={'size':len(data),'checksum':hashlib.sha256(data).hexdigest()}
            (root/'manifest.json').write_text(json.dumps({'status':'source-frozen','artifacts':artifacts}))
            restore.restore('media',root,check_only=True)
            command.assert_not_called()

    def test_target_selectors_are_quarantined_and_redis_is_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=root/'compose';directory.mkdir()
            checkpoint=root/'checkpoint';checkpoint.mkdir()
            for name in ['docker-compose.yml','mediaserver.env','.env','compose.yaml']:
                (directory/name).write_text(name)
            (directory/'redis-data').mkdir();(directory/'redis-data/dump.rdb').write_text('persistent')
            expected={Path('.'),Path('docker-compose.yml'),Path('mediaserver.env')}
            extras=restore.unexpected_inputs(directory,expected,Path('redis-data'))
            self.assertEqual({p.name for p in extras},{'.env','compose.yaml'})
            restore.quarantine_inputs(directory,extras,checkpoint)
            self.assertFalse((directory/'.env').exists())
            self.assertFalse((directory/'compose.yaml').exists())
            self.assertEqual((directory/'redis-data/dump.rdb').read_text(),'persistent')
            evidence=json.loads((checkpoint/'rollback-config-quarantine.json').read_text())
            self.assertEqual((Path(evidence['path'])/'.env').read_text(),'.env')
            self.assertEqual((directory/'docker-compose.yml').read_text(),'docker-compose.yml')
