"""Guard frontend-only updates against backend restart or unpinned publication."""
from pathlib import Path
import re
import json
import shlex
import subprocess
import tempfile
import unittest
import yaml
ROOT = Path(__file__).resolve().parents[1]

class JenaWebDeploymentTests(unittest.TestCase):
    def test_web_activation_and_rollback_do_not_start_dependencies(self):
        play = yaml.safe_load((ROOT/'oldap-jena-web-update.yml').read_text())[0]
        block = next(t for t in play['tasks'] if 'block' in t)
        for tasks in (block['block'], block['rescue']):
            commands = [t['ansible.builtin.command']['cmd'] for t in tasks
                        if isinstance(t.get('ansible.builtin.command'), dict) and 'cmd' in t['ansible.builtin.command']]
            up = next(c for c in commands if ' up ' in c)
            self.assertEqual(up, 'docker compose up -d --no-deps --wait oldap-app fasnachts-page')

    def test_salsah_accepts_legacy_release_or_pinned_candidate_only(self):
        tasks = yaml.safe_load((ROOT/'tasks/update-salsah.yml').read_text())
        rule = tasks[0]['ansible.builtin.assert']['that']
        pattern = rule.split("match('")[1].split("')")[0]
        tag = 'jena-0.0.2-rc1-abcdef123456-amd64'
        self.assertRegex('v0.0.2', pattern)
        self.assertRegex(tag+'@sha256:'+'a'*64, pattern)
        for invalid in ('latest', tag, tag+'@sha256:abc', 'v0.0.2;echo bad'):
            self.assertIsNone(re.fullmatch(pattern, invalid))

    def test_media_update_preserves_unrelated_image_lines(self):
        play=yaml.safe_load((ROOT.parent/'oldap-mediaserver/ansible/update-jena-home.yml').read_text())[0]
        patch=next(t['ansible.builtin.replace'] for t in play['tasks'] if 'ansible.builtin.replace' in t)
        source='    image: lrosenth/oldap-mediahelper:v0.2.17\n    image: lrosenth/sipi-2:0.1.0\n    image: caddy:2.8\n'
        result=re.sub(patch['regexp'], r'\g<1>candidate', source, flags=re.M)
        self.assertIn('image: candidate',result)
        self.assertIn('image: lrosenth/sipi-2:0.1.0',result)
        self.assertIn('image: caddy:2.8',result)

    def test_media_preflight_includes_profiled_workers(self):
        """Use real Compose resolution: workers are absent unless profiles are enabled."""
        play = yaml.safe_load((ROOT.parent / 'oldap-mediaserver/ansible/update-jena-home.yml').read_text())[0]
        task = next(t for t in play['tasks'] if t['name'].startswith('Verify all four'))
        command = shlex.split(task['ansible.builtin.shell']['cmd'].split('|', 1)[0])
        services = {'mediaserver': {'image': 'example/helper:test'}}
        for worker in ('ingest-worker', 'export-worker', 'mobile-media-worker'):
            services[worker] = {'image': 'example/helper:test', 'profiles': ['workers']}
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'docker-compose.jena-candidate.yml').write_text(
                yaml.safe_dump({'name': 'profile-check', 'services': services}))
            resolved = json.loads(subprocess.check_output(command, cwd=directory, text=True))
        self.assertEqual(set(resolved['services']), set(services))
