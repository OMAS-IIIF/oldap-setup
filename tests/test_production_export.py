"""Exercise source export ACL separation and occupied-controller rejection."""
import importlib.util
import os
from pathlib import Path
import types
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location('export_source', Path(__file__).resolve().parents[1]/'scripts/export-production-source.py')
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class ExportTests(unittest.TestCase):
    def exercise(self, occupied):
        reads = []
        class Redis:
            def __init__(self, **kwargs):
                self.role = 'ordinary'
            @classmethod
            def from_url(cls, url, **kwargs):
                client = cls()
                client.role = url
                return client
            def ping(self):
                return True
            def get(self, key):
                if key.endswith(':controller') and self.role != 'recovery':
                    raise PermissionError('Controller requires the separate recovery ACL')
                reads.append((self.role, key))
                return 'occupied' if occupied and key.endswith(':controller') else None
            def dbsize(self):
                return 0
        requests = MagicMock()
        requests.get.return_value.__enter__.return_value.headers = {'Content-Type':'application/x-trigstar'}
        environment = {'OLDAP_STAGING_LOCK_REDIS_URL':'writer', 'OLDAP_WRITER_RECOVERY_REDIS_URL':'recovery',
                       'OLDAP_TS_SERVER':'http://graphdb:7200', 'OLDAP_TS_REPO':'oldap', 'OLDAP_CUTOVER_CHECK_ONLY':'1'}
        with patch.dict('sys.modules', {'redis':types.SimpleNamespace(Redis=Redis), 'requests':requests}), patch.dict(os.environ, environment):
            if occupied:
                with self.assertRaisesRegex(AssertionError, 'controller is occupied'):
                    exec(export.CLIENT, {})
                requests.get.assert_not_called()
            else:
                with self.assertRaises(SystemExit) as result:
                    exec(export.CLIENT, {})
                self.assertEqual(result.exception.code, 0)
                self.assertIn(('recovery','oldap-api:staging:recovery:controller'), reads)
                requests.get.assert_called_once()

    def test_recovery_key_uses_recovery_acl(self):
        self.exercise(False)

    def test_occupied_controller_blocks_export(self):
        self.exercise(True)
