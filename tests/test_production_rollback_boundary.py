"""Private rollback must refuse public writers and unsafe source shutdowns."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('boundary', Path(__file__).resolve().parents[1]/'scripts/check-production-rollback-boundary.py')
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


def container(name, running=False, exit_code=0, oom=False):
    return {'Name': '/'+name, 'State': {'Running': running, 'ExitCode': exit_code, 'OOMKilled': oom}}


class BoundaryTests(unittest.TestCase):
    def test_partial_private_start_allowed(self):
        boundary.validate('api', [container('graphdb'), container('oldap-api', True)])
        boundary.validate('media', [container('mediaserver')])

    def test_ingress_workers_and_unknown_containers_refused(self):
        for name in ['caddy', 'archive-writer', 'unknown']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                boundary.validate('api', [container('graphdb'), container(name, True)])
        with self.assertRaises(ValueError):
            boundary.validate('media', [container('ingest-worker', True)])

    def test_missing_running_or_unclean_graphdb_refused(self):
        for rows in [[], [container('graphdb', True)], [container('graphdb', exit_code=137)], [container('graphdb', oom=True)]]:
            with self.assertRaises(ValueError):
                boundary.validate('api', rows)
