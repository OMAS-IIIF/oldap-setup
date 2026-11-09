"""Rehearsal preparation must never retain live paths or external network access."""
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('rehearsal', Path(__file__).resolve().parents[1]/'scripts/prepare-production-rehearsal.py')
rehearsal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearsal)


class RehearsalTests(unittest.TestCase):
    def test_unrelated_backup_paths_not_extracted(self):
        runtime = tarfile.TarInfo('srv/storage/graphdb/data.db')
        backup = tarfile.TarInfo('srv/storage/oldap-data/backups/latest.trig.gz')
        backup.type = tarfile.SYMTYPE
        self.assertEqual(rehearsal.safe_members([runtime, backup], 'api'), [runtime])

    def test_runtime_links_and_traversal_rejected(self):
        for name, kind in [('srv/storage/graphdb/link', tarfile.SYMTYPE),
                           ('../outside', tarfile.REGTYPE),
                           ('/absolute', tarfile.REGTYPE),
                           ('srv/storage/graphdb/device', tarfile.CHRTYPE)]:
            member = tarfile.TarInfo(name)
            member.type = kind
            with self.subTest(name=name), self.assertRaises(ValueError):
                rehearsal.safe_members([member], 'api')

    def test_source_configuration_is_isolated_and_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'tree/source').mkdir(parents=True)
            (root/'incoming').mkdir()
            (root/'extracted.json').write_text('{}')
            def service():
                return {'image':'sha256:'+'a'*64, 'environment':{},
                        'container_name':'LIVE', 'ports':['443:443'], 'privileged':True,
                        'volumes':[{'type':'bind', 'source':'/source', 'target':'/data'}]}
            api = {'services':{name:service() for name in ['graphdb','redis','archive-writer','oldap-api']}}
            media = {'services':{name:service() for name in ['mediaserver','imageserver']}}
            (root/'incoming/api-source-compose.json').write_text(json.dumps(api))
            (root/'incoming/media-source-compose.json').write_text(json.dumps(media))
            with patch.object(rehearsal.image_archive, 'resolve_source_image', return_value='sha256:'+'b'*64):
                rehearsal.configuration(root, 'oldap-restore-test')
            result = json.loads((root/'source-compose.json').read_text())
            self.assertTrue(result['networks']['default']['internal'])
            self.assertEqual(result['networks']['default']['driver_opts']['com.docker.network.bridge.gateway_mode_ipv4'], 'isolated')
            self.assertEqual(len(result['services']), 6)
            for service in result['services'].values():
                self.assertNotIn('container_name', service)
                self.assertNotIn('ports', service)
                self.assertNotIn('privileged', service)
                self.assertEqual(service['pull_policy'], 'never')
                self.assertEqual(service['restart'], 'no')
                for mount in service['volumes']:
                    self.assertTrue(Path(mount['source']).is_relative_to(root))
            self.assertEqual(result['services']['oldap-api']['environment']['OLDAP_IMPORT_EMAIL_BACKEND'], 'console')
            self.assertEqual(json.loads((root/'incoming/api-source-compose.json').read_text()), api)

    def test_incomplete_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'incoming').mkdir()
            (root/'incoming/manifest.json').write_text(json.dumps({'status':'source-frozen', 'artifacts':[]}))
            with self.assertRaisesRegex(ValueError, 'recovered source'):
                rehearsal.verify_inputs(root)
