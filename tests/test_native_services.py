"""Startup fail-closed checks for the native persistent writer store."""

import importlib.util
from pathlib import Path
import tempfile
import subprocess
import shutil
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "native_services", Path(__file__).parents[1] / "scripts/native-services.py"
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeStartupTest(unittest.TestCase):
    def test_missing_aof_cannot_bootstrap_empty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "redis.conf"
            path.write_text(
                f'dir "{directory}"\nappendonly yes\nappendfsync always\naof-load-truncated no\nmaxmemory-policy noeviction\ndaemonize no\n'
            )
            with patch.object(native.os, "execv") as execute:
                with self.assertRaisesRegex(ValueError, "AOF is missing"):
                    native.start_redis(Path("/unused/redis-server"), path)
                execute.assert_not_called()

    @unittest.skipUnless(shutil.which("redis-server"), "Redis binary required")
    def test_corrupt_manifest_cannot_start_writer_store(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "appendonlydir").mkdir()
            (root / "appendonlydir/appendonly.aof.manifest").write_text(
                "corrupt manifest\n"
            )
            config = root / "redis.conf"
            config.write_text(
                f'dir "{directory}"\nport 0\nunixsocket "{root / "redis.sock"}"\nappendonly yes\nappendfsync always\naof-load-truncated no\nmaxmemory-policy noeviction\ndaemonize no\n'
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(native.__file__)),
                    "redis",
                    "--binary",
                    shutil.which("redis-server"),
                    "--configuration",
                    str(config),
                ],
                capture_output=True,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(
                (root / "appendonlydir/appendonly.aof.manifest").read_text(),
                "corrupt manifest\n",
            )

    def test_truncated_aof_tolerance_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "redis.conf"
            path.write_text(
                f'dir "{directory}"\nappendonly yes\nappendfsync always\naof-load-truncated yes\nmaxmemory-policy noeviction\ndaemonize no\n'
            )
            with patch.object(native.os, "execv") as execute:
                with self.assertRaisesRegex(ValueError, "durable foreground"):
                    native.start_redis(Path("/unused/redis-server"), path)
                execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
