"""Source capture must retain actual images and reject unprotected storage."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('capture', Path(__file__).resolve().parents[1]/'scripts/capture-production-compose.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CaptureTests(unittest.TestCase):
    def fixture(self, source):
        configuration = {'services': {'api': {'image': 'mutable:tag', 'volumes': [{'type':'bind', 'source':str(source), 'target':'/data'}]}}}
        rows = [{'Name':'/original', 'Image':'sha256:actual', 'Config':{'Labels':{'com.docker.compose.service':'api'}}}]
        return configuration, rows

    def test_actual_image_is_pinned(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(capture.NAMES, {'api':['original']}), patch.dict(capture.ROOTS, {'api':[directory]}):
            config, rows = self.fixture(Path(directory))
            result = capture.pin_source('api', config, rows)
            self.assertEqual(result['services']['api']['image'], 'sha256:actual')
            self.assertEqual(result['services']['api']['pull_policy'], 'never')

    def test_unprotected_bind_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(capture.NAMES, {'api':['original']}), patch.dict(capture.ROOTS, {'api':['/not/in/snapshot']}):
            config, rows = self.fixture(Path(directory))
            with self.assertRaisesRegex(ValueError, 'not covered'):
                capture.pin_source('api', config, rows)

    def test_wrong_topology_rejected(self):
        config, rows = self.fixture(Path('/tmp'))
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            capture.pin_source('api', config, rows)
