"""Exercise recovery decisions, partial failures and maintenance without Docker."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('jena_recovery', Path(__file__).resolve().parents[1] / 'scripts/jena-recovery.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def container(service, namespace, started='one'):
    return dict(service=service, namespace=namespace, id=service, started=started, running=namespace is not None)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.containers = {M.OWNER: container('oldap-jena', 'new')}
        self.containers.update({name: container(service, 'old') for service, name in M.CLIENTS})
        self.calls = []
        self.failure = None
        self.readiness = True
        self.owner_patch = patch.object(M, 'inspect', side_effect=lambda name: dict(self.containers[name]))
        self.command_patch = patch.object(M, 'command', side_effect=self.command)
        self.ready_patch = patch.object(M, 'ready', side_effect=lambda: self.readiness)
        for mock in (self.owner_patch, self.command_patch, self.ready_patch):
            mock.start()
            self.addCleanup(mock.stop)

    def command(self, args, **kwargs):
        self.calls.append(args)
        if args[:2] == ['docker', 'compose']:
            service = args[-1]
            name = dict(M.CLIENTS)[service]
            if service == self.failure:
                self.containers[name]['running'] = False
                self.containers[name]['namespace'] = None
                raise RuntimeError('injected recreation failure')
            self.containers[name] = container(service, 'new')
        return ''

    def run_check(self):
        return M.reconcile(self.directory, self.directory)

    def test_repair_orders_identity_before_api_and_is_idempotent(self):
        self.assertEqual(self.run_check(), 'recovered')
        self.assertEqual([c[-1] for c in self.calls if c[1] == 'compose'], ['oldap-jena-identity', 'oldap-api'])
        self.assertEqual(self.calls[-1][1], 'exec')  # Anonymous end-to-end check.
        self.calls.clear()
        self.assertEqual(self.run_check(), 'healthy')
        self.assertEqual(self.calls, [])

    def test_same_container_id_with_new_namespace_still_repairs(self):
        self.assertEqual(self.containers[M.OWNER]['id'], 'oldap-jena')
        self.assertEqual(self.run_check(), 'recovered')

    def test_backend_not_ready_does_not_touch_clients(self):
        self.readiness = False
        self.assertEqual(self.run_check(), 'backend-not-ready')
        self.assertFalse(self.calls)

    def test_maintenance_does_not_even_inspect_docker(self):
        (self.directory / 'maintenance').touch()
        with patch.object(M, 'inspect', side_effect=AssertionError('must not inspect')):
            self.assertEqual(self.run_check(), 'maintenance')

    def test_intentional_stop_is_respected_even_after_successful_repair(self):
        self.run_check()
        self.calls.clear()
        self.containers[M.CLIENTS[0][1]] = container('oldap-jena-identity', None)
        self.assertIn('intentionally-stopped', self.run_check())
        self.assertFalse(self.calls)

    def test_failure_stops_before_api_then_retries_owned_stopped_client(self):
        self.failure = 'oldap-jena-identity'
        with self.assertRaises(RuntimeError):
            self.run_check()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.run_check(), 'retry-backoff')
        self.failure = None
        with patch.object(M.time, 'time', return_value=10**12):
            self.assertEqual(self.run_check(), 'recovered')

    def test_three_failures_are_bounded(self):
        self.failure = 'oldap-jena-identity'
        for timestamp in (100, 140, 180):
            with patch.object(M.time, 'time', return_value=timestamp), self.assertRaises(RuntimeError):
                self.run_check()
        count = len(self.calls)
        with patch.object(M.time, 'time', return_value=300), self.assertRaisesRegex(RuntimeError, 'exhausted'):
            self.run_check()
        self.assertEqual(len(self.calls), count)

    def test_new_generation_retains_interrupted_repair_ownership(self):
        self.failure = 'oldap-jena-identity'
        with self.assertRaises(RuntimeError):
            self.run_check()
        self.containers[M.OWNER]['started'] = 'two'
        self.failure = None
        self.assertEqual(self.run_check(), 'recovered')

    def test_healthy_clients_are_not_recreated(self):
        for service, name in M.CLIENTS:
            self.containers[name] = container(service, 'new')
        self.assertEqual(self.run_check(), 'healthy')
        self.assertFalse(self.calls)

    def test_wrong_service_label_fails_closed(self):
        self.containers[M.CLIENTS[0][1]]['service'] = 'other'
        with self.assertRaisesRegex(RuntimeError, 'label'):
            self.run_check()
        self.assertFalse(self.calls)

    def test_owner_changes_before_mutation_no_recreation(self):
        real = lambda name: dict(self.containers[name])
        count = 0
        def inspect(name):
            nonlocal count
            if name == M.OWNER:
                count += 1
                if count == 2:
                    self.containers[name]['started'] = 'two'
            return real(name)
        with patch.object(M, 'inspect', side_effect=inspect):
            self.assertEqual(self.run_check(), 'backend-changed')
        self.assertFalse(self.calls)

    def test_failure_does_not_persist_credentials_or_command_output(self):
        self.failure = 'oldap-api'
        with self.assertRaises(RuntimeError):
            self.run_check()
        state = json.loads((self.directory / 'state.json').read_text())
        self.assertEqual(set(state), {'generation', 'repairs'})
        self.assertFalse(state['repairs']['oldap-api']['complete'])
        self.assertTrue(state['repairs']['oldap-jena-identity']['complete'])

    def test_interrupted_removal_is_distinguished_from_daemon_failure(self):
        self.owner_patch.stop()
        try:
            with patch.object(M, 'command', side_effect=[RuntimeError('missing'), '']):
                result = M.inspect('oldap-api')
            self.assertFalse(result['running'])
            self.assertEqual(result['service'], 'oldap-api')
            with patch.object(M, 'command', side_effect=[RuntimeError('daemon'), RuntimeError('daemon')]):
                with self.assertRaises(RuntimeError):
                    M.inspect('oldap-api')
        finally:
            self.owner_patch.start()
