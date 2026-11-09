"""Opt-in Docker test of the real shared lock, without any network/API access.

Run with SWISSCOVERY_LOCK_TEST_IMAGE set to a local image containing util-linux
and Python. Two unrelated container names must still serialize against one Linux filesystem (a Docker volume on macOS).
"""
import os
from pathlib import Path
import subprocess
import time
import unittest
import uuid

import yaml

ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get('SWISSCOVERY_LOCK_TEST_IMAGE')


@unittest.skipUnless(IMAGE, 'Set SWISSCOVERY_LOCK_TEST_IMAGE for the Docker lock test')
class SwisscoveryLockTests(unittest.TestCase):
    def test_overlap_is_rejected_and_process_exit_releases_lock(self):
        service = yaml.safe_load((ROOT / 'swisscovery-compose.yml').read_text())['services']['oldap-harvesters']
        entry = service['entrypoint'][:-1]  # Replace only the actual harvester.
        for kill in (False, True):
            with self.subTest(kill=kill):
                name = 'swisscovery-lock-test-' + uuid.uuid4().hex
                volume = name + '-volume'
                subprocess.run(['docker', 'volume', 'create', volume], capture_output=True, check=True)
                base = ['docker', 'run', '--rm', '--network', 'none', '-v', f'{volume}:/var/lib/swisscovery/locks', '--entrypoint', entry[0]]
                holder = subprocess.Popen(base + ['--name', name, IMAGE, *entry[1:], 'python', '-c',
                    "from pathlib import Path; import time; Path('/var/lib/swisscovery/locks/ready').touch(); time.sleep(60)"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                try:
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        probe = subprocess.run(['docker', 'exec', name, 'test', '-f', '/var/lib/swisscovery/locks/ready'], capture_output=True)
                        if probe.returncode == 0 or holder.poll() is not None:
                            break
                        time.sleep(0.1)
                    self.assertEqual(probe.returncode, 0, 'First container did not acquire lock')
                    contender = base + [IMAGE, *entry[1:], 'python', '-c', 'print("acquired")']
                    rejected = subprocess.run(contender, capture_output=True, text=True, timeout=20)
                    self.assertEqual(rejected.returncode, 75, rejected.stderr)
                    self.assertNotIn('acquired', rejected.stdout)
                    action = ['kill', '--signal', 'KILL'] if kill else ['stop', '--time', '3']
                    subprocess.run(['docker', *action, name], capture_output=True, check=True, timeout=15)
                    holder.communicate(timeout=15)
                    retry = subprocess.run(contender, capture_output=True, text=True, timeout=20)
                    self.assertEqual(retry.returncode, 0, retry.stderr)
                    self.assertIn('acquired', retry.stdout)
                finally:
                    subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
                    holder.communicate(timeout=15)
                    subprocess.run(['docker', 'volume', 'rm', volume], capture_output=True, check=True)
