"""Verify installation checks reject an active writer or outstanding lock."""

import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "operator_check", ROOT / "scripts/check-production-operator.py"
)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class OperatorInstallationTests(unittest.TestCase):
    def run_check(self, *, locked=False, running=False, digest="reviewed"):
        config = {
            "domain": "oldap-production",
            "operatorRedisUrl": "rediss://recovery-operator:fixture@archive-writer.internal:6379/1",
            "nodes": [{"writerServices": ["oldap-api"]}],
            "databaseService": "graphdb",
        }

        class Client:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def ping(self):
                return True

            def info(self, section):
                return {"aof_last_write_status": "ok"}

            def get(self, key):
                return b"owned" if locked else None

        class Domain:
            database_node = {}

            def containers(self, node, service):
                return [service]

            def run(self, node, *args):
                return "true" if args[-1] == "graphdb" or running else "false"

        with patch("redis.Redis.from_url", return_value=Client()), patch(
            "oldaplib.src.mutation_gate._validate_store"
        ), patch(
            "oldaplib.src.writer_recovery_operator.protected_json", return_value=config
        ), patch(
            "oldaplib.src.writer_recovery_operator.inventory_digest",
            return_value=digest,
        ), patch(
            "oldaplib.src.writer_recovery_operator.DockerDomain", return_value=Domain()
        ), patch(
            "sys.argv", ["check", "reviewed"]
        ), contextlib.redirect_stdout(
            io.StringIO()
        ) as output:
            check.main()
            return output.getvalue()

    def test_idle_installation(self):
        self.assertIn('"recoveryExecuted": false', self.run_check())

    def test_lock_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_check(locked=True)

    def test_active_writer_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_check(running=True)

    def test_inventory_drift_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_check(digest="other")
