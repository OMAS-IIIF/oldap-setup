"""Reject unsafe private-target inputs before starting production consumers."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = load('check-cutover-bundle')
compose = load('check-production-target-compose')


class TargetInputTests(unittest.TestCase):
    def archive(self, root, extra=None):
        path = root/'candidate.tar'
        with tarfile.open(path, 'w') as archive:
            for name in ['.env', 'docker-compose.yml']:
                member = tarfile.TarInfo(name)
                member.mode = 0o600
                member.size = 1
                archive.addfile(member, io.BytesIO(b'x'))
            if extra:
                archive.addfile(extra)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_checksum_binds_reviewed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path, checksum = self.archive(Path(directory))
            bundle.validate(path, checksum)
            with self.assertRaises(ValueError):
                bundle.validate(path, '0'*64)

    def test_unsafe_archive_members_rejected(self):
        for name, kind, mode in [('../escape', tarfile.REGTYPE, 0o600),
                                 ('/absolute', tarfile.REGTYPE, 0o600),
                                 ('link', tarfile.SYMTYPE, 0o600),
                                 ('redis-data/source', tarfile.REGTYPE, 0o600),
                                 ('.env', tarfile.REGTYPE, 0o600),
                                 ('.env.extra', tarfile.REGTYPE, 0o644),
                                 ('directory', tarfile.DIRTYPE, 0o600),
                                 ('setuid', tarfile.REGTYPE, 0o4600)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                member = tarfile.TarInfo(name)
                member.type, member.mode = kind, mode
                path, checksum = self.archive(Path(directory), member)
                with self.assertRaises(ValueError):
                    bundle.validate(path, checksum)

    def test_existing_destination_link_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, checksum = self.archive(root)
            destination = root/'installed'
            destination.mkdir()
            (destination/'.env').symlink_to(root/'outside')
            with self.assertRaises(ValueError):
                bundle.validate(path, checksum, destination)

    def config(self, root):
        services = {name: {'image': 'repo@sha256:'+'a'*64} for name in
                    ['oldap-jena', 'oldap-jena-identity', 'oldap-api', 'redis',
                     'caddy', 'oldap-app', 'fasnachts-page', 'salsah-2']}
        services['oldap-api']['environment'] = {'OLDAP_BACKEND': 'jena'}
        for name in ['oldap-api', 'oldap-jena-identity']:
            services[name]['network_mode'] = 'service:oldap-jena'
        for name in ['oldap-api', 'redis', 'oldap-jena']:
            services[name]['volumes'] = [{'type': 'bind', 'source': str(root/'data'/name)}]
        return {'services': services}

    def test_pinned_isolated_target_accepted(self):
        root = Path('/tmp/new-target')
        compose.validate('api', self.config(root), root)

    def test_mutable_image_missing_storage_and_wrong_namespace_rejected(self):
        root = Path('/tmp/new-target')
        for service, key, value in [('caddy','image','repo:latest'),
                                    ('redis','volumes',[]),
                                    ('oldap-api','network_mode','bridge'),
                                    ('oldap-jena','ports',[3031])]:
            config = self.config(root)
            config['services'][service][key] = value
            with self.subTest(service=service, key=key), self.assertRaises(ValueError):
                compose.validate('api', config, root)

    def test_source_mount_named_volume_and_traversal_rejected(self):
        root = Path('/tmp/new-target')
        for mount in [{'type':'bind','source':'/srv/storage/oldap-data'},
                      {'type':'bind','source':str(root/'data/../../source')},
                      {'type':'volume','source':'redis-data'}]:
            config = self.config(root)
            config['services']['redis']['volumes'] = [mount]
            with self.subTest(mount=mount), self.assertRaises(ValueError):
                compose.validate('api', config, root)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'data').mkdir()
            (root/'data/redis').symlink_to('/tmp')
            with self.assertRaises(ValueError):
                compose.validate('api', self.config(root), root)


if __name__ == '__main__':
    unittest.main()
