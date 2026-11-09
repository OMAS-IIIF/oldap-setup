"""Provider overlays and external readonly inputs must not escape rollback retention."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('retention', Path(__file__).parents[1]/'scripts/retain-production-configuration.py')
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


class ProviderRetentionTests(unittest.TestCase):
    def test_swisscovery_ocr_and_external_inputs_are_retained(self):
        calls = []
        def output(args, **kw):
            selected = kw['env'].get('COMPOSE_FILE', '')
            calls.append(selected)
            ocr = 'swisscovery-compose.yml' in selected
            return json.dumps({'services': {'oldap-harvesters': {
                'image': 'harvester:ocr' if ocr else 'harvester:normal',
                'volumes': [
                    {'type':'bind', 'source':'/private/model' if ocr else '/private/config', 'read_only':True},
                    {'type':'bind', 'source':'/live/reports', 'read_only':False},
                ]}}})
        with patch.object(retention, 'output', side_effect=output):
            images, paths = retention.configuration_inputs('api', '/opt/oldap/compose')
        self.assertEqual(images, ['harvester:normal', 'harvester:ocr'])
        self.assertEqual(paths, {'/private/model', '/private/config'})
        self.assertEqual(len(calls), 3)
        self.assertIn('/opt/oldap/compose/swisscovery-compose.yml', calls[-1])
