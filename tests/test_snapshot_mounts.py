"""Snapshot coverage must include state beyond database/media files."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('mounts',Path(__file__).parents[1]/'scripts/check-snapshot-mounts.py')
mounts=importlib.util.module_from_spec(spec);spec.loader.exec_module(mounts)


class MountTests(unittest.TestCase):
    def test_nested_bind_and_disposable_cache(self):
        data=[{'Mounts':[{'Type':'bind','Source':'/opt/media/caddy-data','Destination':'/data'},
                         {'Type':'volume','Destination':'/var/cache/sipi'}]}]
        self.assertEqual(mounts.validate(data,['opt/media']),1)
        with self.assertRaises(ValueError):mounts.validate(data,['opt/media/compose'])

    def test_named_user_state_and_sibling_paths_fail(self):
        for mount in [{'Type':'volume','Destination':'/data'},
                      {'Type':'bind','Source':'/data/medias','Destination':'/data'}]:
            with self.assertRaises(ValueError):mounts.validate([{'Mounts':[mount]}],['data/media'])
        for root in ['/', '../data', '.', '/data']:
            with self.assertRaises(ValueError):mounts.validate([], [root])
