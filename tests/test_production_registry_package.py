"""Different Docker stores must select identical reviewed registry content."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('registry',Path(__file__).parents[1]/'scripts/prepare-production-registry-package.py')
registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)


class RegistryPackageTests(unittest.TestCase):
    def test_only_selector_changes_and_source_is_preserved(self):
        digest='sha256:'+'a'*64
        config={'services':{'api':{'image':digest,'environment':{'KEY':'unchanged'},'volumes':['same']}}}
        result=registry.repin(config,{digest:'owner/api@'+digest})
        self.assertEqual(config['services']['api']['image'],digest)
        self.assertEqual(result['services']['api']['image'],'owner/api@'+digest)
        result['services']['api']['image']=digest
        self.assertEqual(result,config)

    def test_mutable_or_different_manifest_is_rejected(self):
        digest='sha256:'+'a'*64
        for reference in ['owner/api:latest','owner/api@sha256:'+'b'*64,digest]:
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                registry.repin({'services':{'api':{'image':digest}}},{digest:reference})

    def test_unreviewed_files_links_and_nested_output_are_rejected(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source';source.mkdir()
            (source/'manifest.json').write_text(json.dumps({'files':{}}))
            with self.assertRaises(ValueError):
                registry.build(source,root/'unused-plan',source/'output')
            (source/'extra').write_text('unreviewed')
            with self.assertRaises(ValueError):
                registry.build(source,root/'unused-plan',root/'output')
            (source/'extra').unlink();(source/'link').symlink_to(root)
            with self.assertRaises(ValueError):
                registry.build(source,root/'unused-plan',root/'output')
            self.assertFalse((root/'output').exists())
