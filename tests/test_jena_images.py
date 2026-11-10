"""Publishing refuses stable/existing tags and rejects untested or altered bundles."""
import importlib.util
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('jena_images', ROOT / 'scripts/jena-images.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_only_content_qualified_jena_tags_are_allowed(self):
        for value in ('latest', 'v0.2.37', 'jena-latest', 'jena-0.2.37-rc1', 'jena-0.2.37-rc0-abcdef123456'):
            self.assertFalse(release.valid_reference('lrosenth/oldap-api:' + value))
        self.assertTrue(release.valid_reference('lrosenth/oldap-api:jena-0.2.37-rc1-abcdef123456'))
        self.assertFalse(release.valid_reference('someone/oldap-api:jena-0.2.37-rc1-abcdef123456'))

    def test_package_rc_versions_keep_isolated_tags_and_cannot_mislabel_rc(self):
        fingerprint = 'a' * 64
        for version in ('1.0.0', '1.0.0rc1'):
            tag = release.candidate_tag(version, 1, fingerprint)
            self.assertEqual(tag, 'jena-1.0.0-rc1-' + 'a' * 12)
            self.assertTrue(release.valid_reference('lrosenth/oldap-api:' + tag))
        for version in ('1.0.0rc2', '1.0.0.dev1', 'latest'):
            with self.assertRaises(ValueError):
                release.candidate_tag(version, 1, fingerprint)

    def test_api_make_requires_explicit_bundle_without_running_docker(self):
        for target in ('docker-prepare', 'docker-build', 'docker-image', 'docker-push'):
            result = subprocess.run(['make', target], cwd=ROOT.parent / 'oldap-api',
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Set IMAGE_BUNDLE', result.stderr)

    def test_api_make_routes_bundle_with_spaces_to_shared_workflow(self):
        for target, action in (('docker-build', 'build'), ('docker-image', 'build'),
                               ('docker-push', 'publish'), ('docker-accept', 'accept')):
            result = subprocess.run(['make', target, 'IMAGE_BUNDLE=/tmp/release with spaces',
                                     'IMAGE_PYTHON=/bin/echo'], cwd=ROOT.parent / 'oldap-api',
                                    capture_output=True, text=True, check=True)
            self.assertIn('jena-images.py ' + action, result.stdout)
            self.assertIn('/tmp/release with spaces', result.stdout)

    def test_independent_versions_still_require_compatible_library(self):
        metadata = {'tool': {'poetry': {'dependencies': {'oldaplib': '>=1.0.1,<2.0.0'}}}}
        release.check_library_requirement(metadata, '1.0.2')
        for version in ('1.0.0', '2.0.0'):
            with self.assertRaisesRegex(ValueError, 'declared version'):
                release.check_library_requirement(metadata, version)

    def test_tools_only_acceptance_does_not_require_api_or_java_service(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            built = {'oldap-tools': {arch: {'id': 'sha256:fixture'} for arch in release.ARCHES}}
            release.save(root / 'built.json', built)
            with patch.object(release, 'verify'), patch.object(release.subprocess, 'run') as run:
                release.accept(root, None)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(json.loads((root / 'accepted.json').read_text()), built)

    def fixture(self, root):
        context = root / 'oldap-api'
        context.mkdir()
        (context / 'Dockerfile').write_text('test fixture')
        ref = 'lrosenth/oldap-api:jena-0.2.37-rc1-abcdef123456'
        manifest = {'sources': {'oldap-api': {'version': '0.2.37'}}, 'components': {'oldap-api': {
            'reference': ref, 'context_sha256': {'Dockerfile': release.digest(context / 'Dockerfile')}}}}
        built = {'oldap-api': {arch: {'reference': ref + '-' + arch, 'id': 'sha256:fixture'} for arch in release.ARCHES}}
        release.save(root / 'release.json', manifest)
        release.save(root / 'built.json', built)
        release.save(root / 'accepted.json', built)
        return manifest

    def test_stable_references_require_explicit_final_mode(self):
        self.assertFalse(release.valid_reference('lrosenth/oldap-api:v1.0.0'))
        self.assertTrue(release.valid_reference('lrosenth/oldap-api:v1.0.0', final=True))
        self.assertTrue(release.valid_reference('lrosenth/oldap-tools:v1.0.0-amd64', final=True))
        for tag in ('latest', 'v1.0.0rc1', 'v1.0.0+local'):
            self.assertFalse(release.valid_reference('lrosenth/oldap-api:' + tag, final=True))

    def test_final_manifest_rejects_relabelled_rc_or_wrong_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root)
            manifest['final'] = True
            manifest['versions'] = {'oldap-api': '1.0.0', 'oldaplib': '1.0.0'}
            manifest['sources'] = {name: {'version': '1.0.0'} for name in release.PACKAGES}
            manifest['components']['oldap-api']['reference'] = 'lrosenth/oldap-api:v1.0.0'
            release.save(root / 'release.json', manifest)
            release.verify(root)
            manifest['versions']['oldaplib'] = '1.0.1'
            manifest['sources']['oldaplib']['version'] = '1.0.1'
            release.save(root / 'release.json', manifest)
            release.verify(root)
            manifest['versions']['oldaplib'] = '1.0.0rc1'
            release.save(root / 'release.json', manifest)
            with self.assertRaises(ValueError):
                release.verify(root)
            manifest['versions']['oldaplib'] = '1.0.0'
            manifest['components']['oldap-api']['reference'] = 'lrosenth/oldap-api:v1.0.1'
            release.save(root / 'release.json', manifest)
            with self.assertRaises(ValueError):
                release.verify(root)

    def test_changed_context_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            (root / 'oldap-api/Dockerfile').write_text('changed')
            with self.assertRaises(ValueError):
                release.verify(root)

    def test_existing_tag_never_pushed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            with patch.object(release, 'registry', return_value='sha256:exists'), patch.object(release.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    release.publish(root)
                run.assert_not_called()

    def test_registry_failure_never_pushed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            with patch.object(release, 'registry', side_effect=TimeoutError), patch.object(release.subprocess, 'run') as run:
                with self.assertRaises(TimeoutError):
                    release.publish(root)
                run.assert_not_called()

    def test_changed_acceptance_refused_before_registry_access(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            release.save(root / 'accepted.json', {})
            with patch.object(release, 'registry') as registry:
                with self.assertRaises(ValueError):
                    release.publish(root)
                registry.assert_not_called()


if __name__ == '__main__':
    unittest.main()
