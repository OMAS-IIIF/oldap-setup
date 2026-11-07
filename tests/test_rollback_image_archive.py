"""Reject corrupt archive metadata before invoking Docker or publishing output."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('archive', Path(__file__).parents[1]/'scripts/verify-rollback-image-archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveTests(unittest.TestCase):
    def test_corrupt_config_never_loads(self):
        with tempfile.TemporaryDirectory() as base:
            source, target = Path(base)/'source.tar', Path(base)/'target.tar'
            config = 'blobs/sha256/'+'0'*64
            with tarfile.open(source, 'w') as output:
                for name, data in [('manifest.json', json.dumps([{'Config':config}]).encode()),
                                   (config, b'{}')]:
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    output.addfile(entry, io.BytesIO(data))
            with patch.object(archive.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    archive.verify(source, target, 'api')
                run.assert_not_called()
            self.assertFalse(target.exists())

    def test_existing_compatibility_copy_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as base:
            target = Path(base)/'retained.tar'
            target.write_bytes(b'keep')
            with self.assertRaises(ValueError):
                archive.verify(Path(base)/'absent.tar', target, 'api')
            self.assertEqual(target.read_bytes(), b'keep')
