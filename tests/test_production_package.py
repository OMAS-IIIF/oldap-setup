"""Production package boundaries: do not import home identities or unsafe paths."""
import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('package',Path(__file__).resolve().parents[1]/'scripts/prepare-production-package.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def test_source_identity_and_mail_with_new_backend_wiring(self):
        home={'OLDAP_BACKEND':'jena','OLDAP_ACCESS_JWT_SECRET':'home',
              'OLDAP_JENA_SERVICE_KEY':'new-placeholder','OLDAP_MAIL_HOST':'home.invalid',
              'OLDAP_STAGING_LOCK_REDIS_URL':'redis://redis/1'}
        source={'OLDAP_BACKEND':'graphdb','OLDAP_ACCESS_JWT_SECRET':'production',
                'OLDAP_MAIL_HOST':'prod.example','OLDAP_STAGING_LOCK_REDIS_URL':'redis://old-writer/1',
                'OLDAP_TS_PASSWORD':'legacy-password'}
        result=package.production_environment(home,source)
        self.assertEqual(result['OLDAP_ACCESS_JWT_SECRET'],'production')
        self.assertEqual(result['OLDAP_MAIL_HOST'],'prod.example')
        self.assertEqual(result['OLDAP_BACKEND'],'jena')
        self.assertEqual(result['OLDAP_STAGING_LOCK_REDIS_URL'],'redis://redis/1')
        self.assertNotIn('OLDAP_TS_PASSWORD',result)
        self.assertEqual(home['OLDAP_ACCESS_JWT_SECRET'],'home')

    def test_missing_source_credential_never_falls_back_to_home(self):
        with self.assertRaises(ValueError):
            package.production_environment({'OLDAP_ACCESS_JWT_SECRET':'home'}, {})

    def test_archives_are_reproducible_and_reject_links(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tree=root/'tree';tree.mkdir()
            (tree/'file').write_text('content')
            package.archive(tree,root/'one.tar');package.archive(tree,root/'two.tar')
            self.assertEqual((root/'one.tar').read_bytes(),(root/'two.tar').read_bytes())
            (tree/'link').symlink_to(tree/'file')
            with self.assertRaises(ValueError):package.archive(tree,root/'bad.tar')

    def test_duplicate_source_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            archive=Path(d)/'source.tar'
            with tarfile.open(archive,'w') as t:
                t.addfile(tarfile.TarInfo('config'));t.addfile(tarfile.TarInfo('config'))
            with self.assertRaises(ValueError):package.read_member(archive,'config')
