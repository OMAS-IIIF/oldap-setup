"""Verify that image provenance never exposes Docker configuration secrets."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'snapshot_images', Path(__file__).parents[1] / 'scripts/snapshot-images.py')
images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(images)


class ImageProvenanceTests(unittest.TestCase):
    def test_records_actual_image_and_platform_without_secrets(self):
        container = {'Name': '/worker', 'Image': 'sha256:actual',
                     'Config': {'Image': 'example:latest', 'Env': ['PASSWORD=secret']}}
        image = {'Id': 'sha256:actual', 'RepoDigests': ['example@sha256:registry'],
                 'Os': 'linux', 'Architecture': 'arm64', 'Variant': 'v8',
                 'Config': {'Env': ['TOKEN=secret']}}
        with patch.object(images, 'inspect', side_effect=[[container], [image]]) as read:
            result = images.inventory(['worker'])
        self.assertEqual(read.call_args_list[1].args, ('image', ['sha256:actual']))
        self.assertEqual(result['worker']['image_id'], 'sha256:actual')
        self.assertEqual(result['worker']['repo_digests'], ['example@sha256:registry'])
        self.assertEqual(result['worker']['architecture'], 'arm64')
        self.assertNotIn('secret', json.dumps(result))

    def test_local_only_image_is_explicitly_without_registry_digest(self):
        with patch.object(images, 'inspect', side_effect=[
            [{'Name': '/api', 'Image': 'sha256:local', 'Config': {'Image': 'local:build'}}],
            [{'Id': 'sha256:local', 'Os': 'linux', 'Architecture': 'amd64'}],
        ]):
            self.assertEqual(images.inventory(['api'])['api']['repo_digests'], [])

    def test_requires_explicit_names(self):
        for names in ([], ['--all']):
            with self.assertRaises(ValueError):
                images.inventory(names)
