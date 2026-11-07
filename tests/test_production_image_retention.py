"""Image retention must not certify changed or unknown source containers."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('retention', Path(__file__).parents[1]/'scripts/retain-production-images.py')
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


class RetentionTests(unittest.TestCase):
    def test_unexpected_inventory_never_saves_or_certifies(self):
        with tempfile.TemporaryDirectory() as base:
            target = Path(base)/'package'
            with patch.object(retention, 'ssh', return_value=SimpleNamespace(stdout='{}')) as ssh:
                with self.assertRaises(RuntimeError):
                    retention.retain(target)
                self.assertEqual(ssh.call_count, 1)
            self.assertFalse((target/'images-complete.json').exists())
            self.assertFalse((target/'api-images.tar').exists())

    def test_restart_during_copy_rejects_completion(self):
        identity = 'sha256:'+'a'*64
        inventory = {n: {'image_id': identity, 'container_id': n, 'started_at': 'before'}
                     for n in retention.EXPECTED['api']}
        changed = {n: dict(v, started_at='after') for n, v in inventory.items()}
        calls = iter([SimpleNamespace(stdout=json.dumps(inventory)),
                      SimpleNamespace(), SimpleNamespace(stdout=json.dumps(changed))])
        with tempfile.TemporaryDirectory() as base:
            target = Path(base)/'package'
            with patch.object(retention, 'ssh', side_effect=lambda *a, **k: next(calls)), \
                 patch.object(retention.subprocess, 'run'), \
                 patch.object(retention.subprocess, 'check_output', return_value=identity):
                with self.assertRaisesRegex(RuntimeError, 'Source changed'):
                    retention.retain(target)
            self.assertFalse((target/'images-complete.json').exists())
            self.assertFalse((target/'api-verified.json').exists())


if __name__ == '__main__':
    unittest.main()
