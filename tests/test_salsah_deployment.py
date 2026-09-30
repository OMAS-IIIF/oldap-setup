"""Validate additive configuration and the isolated SALSAH update boundary."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]

class SalsahDeploymentTests(unittest.TestCase):
    def test_compose_overlay_preserves_existing_services(self):
        base = (ROOT / 'docker-compose.yml').read_text()
        overlay = (ROOT / 'salsah-compose.yml').read_text()
        variables = {name: '/tmp/salsah-fixture' for name in re.findall(r'\$\{([A-Z_]+)', base + overlay)}
        variables.update(SALSAH_TAG='v0.0.1', SALSAH_ORIGIN='https://salsah.org', SALSAH_API_URL='https://api.salsah.org', SALSAH_MEDIA_URL='https://media.oldap.org')
        with tempfile.TemporaryDirectory() as folder:
            empty = Path(folder) / '.env'; empty.write_text('')
            result = subprocess.run(['docker', 'compose', '--profile', '*', '--env-file', str(empty), '-f', str(ROOT / 'docker-compose.yml'), '-f', str(ROOT / 'salsah-compose.yml'), 'config', '--format', 'json'], env={**os.environ, **variables}, capture_output=True, text=True, check=True)
        services = json.loads(result.stdout)['services']
        self.assertEqual(set(services), set(yaml.safe_load(base)['services']) | {'salsah-2'})
        self.assertNotIn('ports', services['salsah-2'])
        self.assertEqual(services['salsah-2']['environment']['PUBLIC_API_URL'], 'https://api.salsah.org')
        self.assertEqual(services['oldap-api']['environment']['OLDAP_FRONTENDS_FILE'], '/run/oldap-frontends.json')

    def test_caddy_is_opt_in_and_preserves_existing_domains(self):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / 'templates'))
        template = env.get_template('Caddyfile.j2')
        for enabled in (False, True):
            output = template.render(caddy_mode='prod', caddy_email='operator@example.org', salsah_enabled=enabled)
            for name in ['api.oldap.org', 'app.oldap.org', 'fasnacht.digital']:
                self.assertIn(name, output)
            self.assertEqual('reverse_proxy salsah-2:3200' in output, enabled)

    def test_routine_update_starts_only_salsah(self):
        tasks = yaml.safe_load((ROOT / 'tasks/update-salsah.yml').read_text())
        start = next(t['community.docker.docker_compose_v2'] for t in tasks if 'community.docker.docker_compose_v2' in t)
        self.assertEqual(start['services'], ['salsah-2'])
        self.assertFalse(start['dependencies'])
        self.assertFalse(start['remove_orphans'])
        for task in tasks:
            self.assertNotIn('ansible.builtin.template', task)
        selector = (ROOT / 'templates/oldap.env.j2').read_text().split('COMPOSE_FILE=', 1)[1].split('\n', 1)[0]
        for writer in (False, True):
            for salsah in (False, True):
                rendered = jinja2.Template(selector).render(oldap_writer_enabled=writer, salsah_enabled=salsah)
                self.assertEqual(rendered, 'docker-compose.yml' + (':writer-compose.yml' if writer else '') + (':salsah-compose.yml' if salsah else ''))
