"""Failure/retry and retention contracts for the office receiver; no live deletes."""
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('receiver', Path(__file__).parents[1] / 'scripts/run-production-backup-receiver.py')
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)
transport = receiver.transport


def receipt(number):
    sid = f'202611{number:02d}T031500Z-1234abcd'
    manifest = {'snapshot_id': sid, 'status': 'offline-compared', 'completed_at': '2026-11-09T03:45:00Z'}
    for role, prefix in [('api', '/srv/storage'), ('media', '/data')]:
        manifest[role] = {'path': f'{prefix}/oldap-jena-snapshot-{sid}/{role}.tar',
                          'bytes': len(role), 'sha256': hashlib.sha256(role.encode()).hexdigest()}
    manifest['media']['host'] = 'dhlab-iii.dhlab.unibas.ch'
    return {'manifest': manifest, 'repository_id': transport.REPOSITORY_ID,
            'archive': 'production-' + sid, 'archive_id': 'a' * 64,
            'verified_at': '2026-11-09T04:00:00Z'}


class ReceiverTests(unittest.TestCase):
    def test_freshness_and_fixed_endpoints(self):
        now = datetime(2026, 11, 9, 4, tzinfo=timezone.utc)
        for hours, valid in [(0, True), (11, True), (13, False), (-1, False)]:
            data = receipt(9)['manifest']
            data['completed_at'] = (now - timedelta(hours=hours)).isoformat()
            if valid:
                receiver.fresh_manifest(data, now)
            else:
                with self.assertRaises(ValueError): receiver.fresh_manifest(data, now)
        for field, value in [('snapshot_id', '../escape'), ('completed_at', '2026-11-09T04:00:00')]:
            data = receipt(9)['manifest']; data[field] = value
            with self.assertRaises(ValueError): receiver.fresh_manifest(data, now)
        data = receipt(9)['manifest']; data['media']['host'] = 'media.home.org'
        with self.assertRaises(ValueError): receiver.fresh_manifest(data, now)

    def test_only_matching_pairs_beyond_three_are_candidates(self):
        pairs = {receipt(i)['manifest']['snapshot_id']: receipt(i) for i in range(1, 7)}
        api, media = dict(pairs), dict(pairs)
        del media[receipt(6)['manifest']['snapshot_id']]
        self.assertEqual(receiver.retirement_candidates(api, media),
                         [receipt(2)['manifest']['snapshot_id'], receipt(1)['manifest']['snapshot_id']])
        media[receipt(3)['manifest']['snapshot_id']] = receipt(3) | {'archive_id': 'b' * 64}
        with self.assertRaises(ValueError): receiver.retirement_candidates(api, media)

    def test_transport_acknowledgement_and_idempotent_retirement(self):
        item = receipt(1); sid = item['manifest']['snapshot_id']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); directory = root / ('oldap-jena-snapshot-' + sid)
            directory.mkdir(); (directory / 'api.tar').write_bytes(b'api')
            (directory / 'ready.json').write_text(json.dumps(item['manifest']))
            # Redirect physical test directory without changing manifest policy roots.
            with patch.object(transport, 'snapshot_directory', return_value=directory):
                with self.assertRaises(ValueError):
                    transport.operate('api', {'action': 'retire', 'receipt': item})
                transport.operate('api', {'action': 'acknowledge', 'receipt': item})
                transport.operate('api', {'action': 'acknowledge', 'receipt': item})
                (directory / 'api.tar').write_bytes(b'bad')
                with self.assertRaises(ValueError):
                    transport.operate('api', {'action': 'retire', 'receipt': item})
                (directory / 'api.tar').write_bytes(b'api')
                transport.operate('api', {'action': 'retire', 'receipt': item})
                transport.operate('api', {'action': 'retire', 'receipt': item})
                self.assertTrue((directory / 'received.json').exists())
                self.assertTrue((directory / 'ready.json').exists())
                self.assertFalse((directory / 'api.tar').exists())

    def test_transport_rejects_symlink_and_changed_publication(self):
        item = receipt(1)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'outside').write_bytes(b'api')
            (directory / 'api.tar').symlink_to(directory / 'outside')
            (directory / 'ready.json').write_text(json.dumps(item['manifest']))
            with patch.object(transport, 'snapshot_directory', return_value=directory):
                with self.assertRaises(ValueError):
                    transport.operate('api', {'action': 'acknowledge', 'receipt': item})
                (directory / 'ready.json').write_text('{}')
                with self.assertRaises(ValueError):
                    transport.operate('api', {'action': 'acknowledge', 'receipt': item})
            self.assertEqual((directory / 'outside').read_bytes(), b'api')

    def test_backup_failure_never_acknowledges_or_prunes(self):
        instance = object.__new__(receiver.Receiver); instance.repository = '/unused'
        data = receipt(9)['manifest']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); target = root / 'snapshots' / data['snapshot_id']
            target.mkdir(parents=True)
            (target / 'manifest.json').write_text(json.dumps(data))
            for role in ('api', 'media'): (target / (role + '.tar')).write_bytes(role.encode())
            for failure in ('create', 'verify'):
                def borg(*args, **kwargs):
                    if args[0] == 'list': return b'{"archives": []}'
                    if failure == 'create': raise ValueError('simulated Borg failure')
                    return b''
                with self.subTest(failure=failure), patch.object(receiver, 'ROOT', root), \
                     patch.object(receiver, 'fresh_manifest', return_value=data), \
                     patch.object(receiver.subprocess, 'check_output', return_value=json.dumps(data).encode()), \
                     patch.object(instance, 'borg', side_effect=borg), \
                     patch.object(instance, 'verify_borg', side_effect=ValueError('verification failed')), \
                     patch.object(instance, 'remote') as remote, patch.object(instance, 'retain') as retain:
                    with self.assertRaises(ValueError): instance.backup()
                    remote.assert_not_called(); retain.assert_not_called()

    def test_retry_reuses_verified_receipt_without_pulling(self):
        instance = object.__new__(receiver.Receiver); instance.repository = '/unused'
        item = receipt(9); data = item['manifest']; sid = data['snapshot_id']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'receipts').mkdir()
            (root / 'receipts' / (sid + '.json')).write_text(json.dumps(item))
            with patch.object(receiver, 'ROOT', root), \
                 patch.object(receiver, 'fresh_manifest', return_value=data), \
                 patch.object(receiver.subprocess, 'check_output', return_value=json.dumps(data).encode()), \
                 patch.object(instance, 'borg', return_value=json.dumps({'archives': [{'name': item['archive']}]}).encode()), \
                 patch.object(instance, 'verify_borg', return_value=item['archive_id']), \
                 patch.object(receiver.puller, 'pull') as pull, \
                 patch.object(instance, 'remote') as remote, patch.object(instance, 'retain') as retain:
                self.assertEqual(instance.backup(), sid)
                pull.assert_not_called(); retain.assert_called_once()
                self.assertEqual([call.args for call in remote.call_args_list],
                                 [('media', 'acknowledge', item), ('api', 'acknowledge', item)])

    def test_validation_failure_on_either_server_prevents_any_retirement(self):
        instance = object.__new__(receiver.Receiver); instance.repository = '/unused'
        pairs = {receipt(i)['manifest']['snapshot_id']: receipt(i) for i in range(1, 6)}
        calls = []
        def remote(role, action, value=None):
            calls.append(action)
            if action == 'inventory': return pairs
            if role == 'media': raise ValueError('wrong remote digest')
        archives = [{'name': item['archive'], 'id': item['archive_id']} for item in pairs.values()]
        with patch.object(instance, 'remote', side_effect=remote), \
             patch.object(instance, 'borg', return_value=json.dumps({'archives': archives}).encode()) as borg:
            with self.assertRaises(ValueError): instance.retain()
            self.assertNotIn('retire', calls)
            self.assertEqual(borg.call_count, 1)


if __name__ == '__main__': unittest.main()
