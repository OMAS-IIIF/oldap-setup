"""Exercise backup alarms, including stale, incomplete and corrupted snapshots."""

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "health", Path(__file__).parents[1] / "scripts/check-snapshot-health.py"
)
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class SnapshotHealthTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "snapshot-test"
        self.directory.mkdir()
        self.now = datetime(2026, 11, 7, tzinfo=timezone.utc)
        self.data = {
            "snapshot_id": self.directory.name,
            "status": "offline-compared",
            "completed_at": self.now.isoformat(),
        }
        for role in ("api", "media"):
            content = role.encode()
            (self.directory / f"{role}.tar").write_bytes(content)
            self.data[role] = {
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }

    def check(self, **kwargs):
        (self.directory / "manifest.json").write_text(json.dumps(self.data))
        return health.check_snapshot(
            self.directory, max_age_hours=30, min_free_percent=0, now=self.now, **kwargs
        )

    def test_valid_full_verification(self):
        self.assertEqual(self.check(verify=True)["status"], "passed")

    def test_missing_old_and_future_timestamps_fail(self):
        for value in (
            None,
            (self.now - timedelta(hours=31)).isoformat(),
            (self.now + timedelta(hours=1)).isoformat(),
            "2026-11-07T00:00:00",
        ):
            with self.subTest(value=value):
                self.data["completed_at"] = value
                self.assertEqual(self.check()["status"], "attention")

    def test_incomplete_wrong_identity_and_invalid_metadata_fail(self):
        self.data["status"] = "copying"
        self.assertEqual(self.check()["status"], "attention")
        self.data["status"] = "offline-compared"
        self.data["snapshot_id"] = "other"
        self.assertEqual(self.check()["status"], "attention")
        self.data["snapshot_id"] = self.directory.name
        self.data["api"]["bytes"] = True
        self.assertEqual(self.check()["status"], "attention")

    def test_missing_archive_and_symlink_fail(self):
        archive = self.directory / "api.tar"
        archive.unlink()
        self.assertEqual(self.check()["status"], "attention")
        archive.symlink_to(self.directory / "media.tar")
        self.assertEqual(self.check()["status"], "attention")

    def test_same_size_corruption_requires_explicit_hash_check(self):
        (self.directory / "api.tar").write_bytes(b"BAD")
        self.assertEqual(self.check()["status"], "passed")
        self.assertEqual(self.check(verify=True)["status"], "attention")

    def test_legacy_snapshot_still_checks_integrity(self):
        self.data.pop("completed_at")
        report = self.check(verify=True)
        self.assertEqual(report["status"], "attention")
        self.assertEqual(
            report["archives"], {"api": "sha256-verified", "media": "sha256-verified"}
        )
        (self.directory / "api.tar").write_bytes(b"BAD")
        report = self.check(verify=True)
        self.assertEqual(report["archives"]["api"], "checksum-mismatch")

    def test_capacity_alarm(self):
        self.check()
        usage = health.shutil._ntuple_diskusage(total=100, used=90, free=10)
        with patch.object(health.shutil, "disk_usage", return_value=usage):
            report = health.check_snapshot(
                self.directory, max_age_hours=30, min_free_percent=20, now=self.now
            )
        self.assertIn(
            "Receiver filesystem below minimum free capacity", report["issues"]
        )


if __name__ == "__main__":
    unittest.main()
