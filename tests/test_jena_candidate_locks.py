"""Offline candidate locks: run with the Python environment containing Poetry.

Synthetic wheels/locks are temporary; sockets are disabled throughout solving.
No repository working tree or registry is modified by these tests.
"""
import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location('candidate_locks', Path(__file__).parents[1] / 'scripts/lock-jena-candidate.py')
try:
    import poetry.factory
except ImportError:
    locks = None
else:
    locks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locks)


@unittest.skipIf(locks is None, "Run with the Poetry Python environment")
class CandidateLockTests(unittest.TestCase):
    def fixture(self, root, wheel_name='oldaplib'):
        wheel = root / f'{wheel_name}-1.0.0rc1-py3-none-any.whl'
        with ZipFile(wheel, 'w') as archive:
            archive.writestr(f'{wheel_name}-1.0.0rc1.dist-info/METADATA',
                             f'Metadata-Version: 2.1\nName: {wheel_name}\nVersion: 1.0.0rc1\nRequires-Python: >=3.13\nRequires-Dist: fixture-dependency (==1.0.0)\n')
        projects = []
        for name in ('oldaplib', 'oldap-api', 'oldap-tools'):
            path = root / name
            path.mkdir()
            dependency = 'fixture-dependency ==1.0.0' if name == 'oldaplib' else 'oldaplib >=1.0.0rc1,<2.0.0'
            (path / 'pyproject.toml').write_text(f'[project]\nname="{name}"\nversion="1.0.0rc1"\nrequires-python=">=3.13"\ndependencies=["{dependency}"]\n')
            (path / 'poetry.lock').write_text('''[[package]]
name = "fixture-dependency"
version = "1.0.0"
description = ""
optional = false
python-versions = ">=3.13"
groups = ["main"]
files = []
[metadata]
lock-version = "2.1"
python-versions = ">=3.13"
content-hash = "fixture"
''')
            projects.append(path)
        return wheel, projects

    def test_offline_portable_hashed_lock_and_idempotent_replay(self):
        with tempfile.TemporaryDirectory() as temporary, patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
            wheel, projects = self.fixture(Path(temporary))
            locks.lock_candidates(wheel, projects)
            before = [(p / 'poetry.lock').read_bytes() for p in projects]
            for path in projects[1:]:
                data = tomllib.loads((path / 'poetry.lock').read_text())
                candidate = next(p for p in data['package'] if p['name'] == 'oldaplib')
                self.assertEqual(candidate['version'], '1.0.0rc1')
                self.assertNotIn('source', candidate)
                self.assertEqual(candidate['files'][0]['file'], wheel.name)
                self.assertTrue(candidate['files'][0]['hash'].startswith('sha256:'))
            locks.lock_candidates(wheel, projects)
            self.assertEqual(before, [(p / 'poetry.lock').read_bytes() for p in projects])

    def test_harvester_keeps_independent_version_with_exact_library_lock(self):
        with tempfile.TemporaryDirectory() as temporary, patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
            wheel, projects = self.fixture(Path(temporary))
            source = projects[-1] / 'pyproject.toml'
            source.write_text(source.read_text().replace('oldap-tools', 'oldap-harvesters').replace('version="1.0.0rc1"', 'version="0.1.14rc1"'))
            locks.lock_candidates(wheel, projects)
            data = tomllib.loads((projects[-1] / 'poetry.lock').read_text())
            self.assertEqual(next(p['version'] for p in data['package'] if p['name'] == 'oldaplib'), '1.0.0rc1')

    def test_wrong_wheel_or_inconsistent_project_versions_leave_locks_unchanged(self):
        for invalid in ('wheel', 'version'):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as temporary:
                wheel, projects = self.fixture(Path(temporary), 'other' if invalid == 'wheel' else 'oldaplib')
                if invalid == 'version':
                    path = projects[-1] / 'pyproject.toml'
                    path.write_text(path.read_text().replace('version="1.0.0rc1"', 'version="1.0.0rc2"'))
                before = [(p / 'poetry.lock').read_bytes() for p in projects]
                with self.assertRaises(ValueError):
                    locks.lock_candidates(wheel, projects)
                self.assertEqual(before, [(p / 'poetry.lock').read_bytes() for p in projects])
