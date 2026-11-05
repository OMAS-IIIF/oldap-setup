"""Validate the real Compose merge, writer dependencies and proxy boundary."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from tests.test_writer_deployment import fixture, render

ROOT = Path(__file__).resolve().parents[1]


class JenaDeploymentTests(unittest.TestCase):
    def model(self, writer=False, rehearsal=False, archive=False, harvester=None):
        """Resolve candidate configuration with synthetic, non-secret inputs."""
        text = ''.join((ROOT / name).read_text() for name in ('docker-compose.yml', 'jena-compose.yml', 'archive-policy-compose.yml', 'swisscovery-compose.yml', 'jena-harvesters-compose.yml', 'jena-swisscovery-compose.yml'))
        env = {**os.environ, **{name: '/tmp/jena-fixture' for name in re.findall(r'\$\{([A-Z_]+)', text)}}
        env.update(OLDAP_JENA_RUNTIME_IMAGE='eclipse-temurin:25-jre', OLDAP_JENA_HEAP_MB='512',
                   OLDAP_JENA_DIRECT_MB='512', OLDAP_JENA_MEMORY_MB='10240',
                   OLDAP_JENA_API_IMAGE='lrosenth/oldap-api@sha256:' + 'a' * 64,
                   OLDAP_JENA_TOOLS_IMAGE='lrosenth/oldap-tools@sha256:' + 'b' * 64,
                   OLDAP_JENA_HARVESTERS_IMAGE='lrosenth/oldap-harvesters@sha256:' + 'c' * 64,
                   OLDAP_JENA_HARVESTERS_OCR_IMAGE='lrosenth/oldap-harvesters@sha256:' + 'd' * 64)
        with tempfile.TemporaryDirectory() as folder:
            command = ['docker', 'compose', '--env-file', '/dev/null', '--profile', '*',
                       '-f', str(ROOT / 'docker-compose.yml')]
            if writer:
                path = Path(folder) / 'writer.yml'
                path.write_text(render('writer-compose.yml.j2', {**fixture(), 'inventory_hostname': 'owner'}))
                command += ['-f', str(path)]
            command += ['-f', str(ROOT / 'jena-compose.yml')]
            if rehearsal:
                command += ['-f', str(ROOT / 'jena-rehearsal-compose.yml')]
            if archive:
                command += ['-f', str(ROOT / 'archive-policy-compose.yml')]
            if harvester == 'swisscovery':
                command += ['-f', str(ROOT / 'swisscovery-compose.yml'), '-f', str(ROOT / 'jena-swisscovery-compose.yml')]
            elif harvester:
                command += ['-f', str(ROOT / 'jena-harvesters-compose.yml')]
            command += ['config', '--format', 'json']
            return json.loads(subprocess.check_output(command, env=env, text=True))['services']

    def test_total_memory_and_direct_buffers_are_bounded(self):
        """Resolve actual Compose budgets, including the no-swap relationship."""
        service = self.model()['oldap-jena']
        self.assertEqual(int(service['mem_limit']), 10240 * 1024**2)
        self.assertEqual(service['memswap_limit'], service['mem_limit'])
        self.assertEqual(service['environment']['JAVA_TOOL_OPTIONS'],
                         '-XX:MaxDirectMemorySize=512m')

    def test_archive_policy_is_shared_read_only_with_explicit_publication(self):
        services = self.model(archive=True)
        for name in ('oldap-api', 'oldap-tools', 'oldap-harvesters'):
            client = services[name]
            path = client['environment']['OLDAP_ARCHIVE_POLICY_FILE']
            mount = next(v for v in client['volumes'] if v['target'] == path)
            self.assertTrue(mount['read_only'])
            self.assertEqual(client['network_mode'], 'service:oldap-jena')
        policy = json.loads((ROOT / 'files/jena-home-archive-policy.json').read_text())
        self.assertEqual(set(policy['projects']), {'fasnacht'})
        self.assertTrue(policy['projects']['fasnacht']['enabled'])
        publication = policy['projects']['fasnacht']['publication']
        self.assertEqual(publication['publisherRoleIris'],
                         ['http://fasnacht.digital/ns/ArchiveMediaEditor'])
        self.assertEqual(publication['publicRoleIri'], 'http://oldap.org/base#Unknown')
        self.assertEqual(set(publication['rootClassIris']),
                         {'http://fasnacht.digital/ns/ArchiveObject',
                          'http://fasnacht.digital/ns/CarnivalEvent'})
        self.assertEqual(publication['maxResources'], 100)

    def test_harvesters_select_exact_images_and_retain_jena_policy_and_ocr_limits(self):
        for source, digest in [('europeana', 'c'), ('swisscovery', 'd')]:
            with self.subTest(source=source):
                service = self.model(archive=True, harvester=source)['oldap-harvesters']
                self.assertEqual(service['image'], 'lrosenth/oldap-harvesters@sha256:' + digest * 64)
                self.assertEqual(service['network_mode'], 'service:oldap-jena')
                self.assertEqual(service['environment']['OLDAP_BACKEND'], 'jena')
                self.assertIn('OLDAP_ARCHIVE_POLICY_FILE', service['environment'])
                if source == 'swisscovery':
                    self.assertEqual(service['entrypoint'][0], 'flock')
                    self.assertEqual(service['mem_limit'], str(5 * 1024**3))

    def test_rehearsal_uses_private_listener_and_separate_storage(self):
        services = self.model(rehearsal=True)
        self.assertEqual(services['oldap-api']['container_name'], 'oldap-jena-review-api')
        self.assertEqual(services['redis']['container_name'], 'oldap-jena-review-redis')
        self.assertEqual(services['oldap-jena']['ports'][0]['host_ip'], '127.0.0.1')
        self.assertEqual(str(services['oldap-jena']['ports'][0]['published']), '18000')
        for name, suffix in [('oldap-api', '/api'), ('redis', '/redis')]:
            self.assertEqual(len(services[name]['volumes']), 1)
            self.assertEqual(services[name]['volumes'][0]['source'], '/tmp/jena-fixture' + suffix)

    def test_all_clients_share_loopback_without_graphdb_dependency(self):
        services = self.model()
        for name in ('oldap-api', 'oldap-tools', 'oldap-harvesters'):
            client = services[name]
            self.assertEqual(client['network_mode'], 'service:oldap-jena')
            self.assertNotIn('networks', client)
            self.assertNotIn('graphdb', client['depends_on'])
            self.assertEqual(client['environment']['OLDAP_BACKEND'], 'jena')
        self.assertNotIn('ports', services['oldap-jena'])
        self.assertNotIn('expose', services['oldap-api'])
        self.assertIn('oldap-api', services['oldap-jena']['networks']['default']['aliases'])
        self.assertEqual(services['graphdb']['profiles'], ['graphdb-legacy'])
        self.assertEqual(services['graphdb-init']['profiles'], ['graphdb-legacy'])
        self.assertEqual(services['redis']['command'], [
            'redis-server', '--appendonly', 'yes', '--appendfsync', 'always',
            '--maxmemory-policy', 'noeviction'])

    def test_identity_callbacks_have_independent_private_capacity(self):
        services = self.model()
        identity = services['oldap-jena-identity']
        self.assertEqual(identity['network_mode'], 'service:oldap-jena')
        self.assertEqual(identity['image'], services['oldap-api']['image'])
        self.assertNotIn('ports', identity)
        self.assertNotIn('oldap-api', identity['depends_on'])
        self.assertIn('--bind=127.0.0.1:8001', identity['environment']['GUNICORN_CMD_ARGS'])
        self.assertEqual(services['oldap-api']['depends_on']['oldap-jena-identity']['condition'],
                         'service_healthy')
        self.assertNotIn('OLDAP_AUTH_ADMIN_PASSWORD', identity['environment'])
        self.assertNotIn('OLDAP_JENA_SERVICE_KEY', identity['environment'])

    def test_writer_health_and_credentials_survive_overlay(self):
        services = self.model(writer=True)
        for name in ('oldap-api', 'oldap-tools', 'oldap-harvesters'):
            client = services[name]
            self.assertEqual(client['depends_on']['archive-writer']['condition'], 'service_healthy')
            self.assertIn('OLDAP_STAGING_LOCK_REDIS_URL', client['environment'])
            self.assertEqual(client['environment']['OLDAP_TS_SERVER'], 'http://127.0.0.1:3031')
        self.assertNotIn('OLDAP_JENA_IDENTITY_KEY', services['oldap-tools']['environment'])

    def test_home_and_production_proxy_block_private_callbacks(self):
        for mode in ('dev', 'prod'):
            config = render('Caddyfile.j2', {'caddy_mode': mode, 'caddy_email': 'test@example.org'})
            self.assertIn('@private path /internal/jena /internal/jena/*', config)
            self.assertNotIn('@private path /internal/*', config)
            self.assertIn('respond @private 404', config)
            # Caddy parses and sorts the actual candidate, without binding ports.
            subprocess.run(['docker', 'run', '--rm', '-i', '--entrypoint', 'caddy', 'caddy:2.8',
                            'adapt', '--config', '/dev/stdin', '--adapter', 'caddyfile'],
                           input=config, text=True, check=True, capture_output=True)

    def test_service_and_client_templates_share_exact_credentials_and_paths(self):
        values = {f'oldap_jena_{name}_key': name + '-test-' + 'a' * 48
                  for name in ('identity', 'service', 'bootstrap', 'fulltext')}
        values.update(oldap_jena_root='/srv/storage/oldap-jena-test',
                      oldap_jena_runtime_image='eclipse-temurin@sha256:' + 'a' * 64,
                      oldap_jena_heap_mb=6144, oldap_jena_direct_mb=512, oldap_jena_memory_mb=10240, oldap_jena_api_image='lrosenth/oldap-api@sha256:' + 'a' * 64,
                      oldap_jena_tools_image='lrosenth/oldap-tools@sha256:' + 'b' * 64)
        properties = dict(line.split('=', 1) for line in render('jena-service.properties.j2', values).splitlines()
                          if line and not line.startswith('#'))
        environment = dict(line.split('=', 1) for line in render('jena.env.j2', values).splitlines()
                           if line and not line.startswith('#'))
        for name in ('identity', 'service', 'bootstrap', 'fulltext'):
            self.assertEqual(properties[name + 'Secret'], environment['OLDAP_JENA_' + name.upper() + '_KEY'])
        self.assertEqual(properties['identityUrl'], 'http://127.0.0.1:8001/internal/jena/identity')
        self.assertEqual(properties['dataset'], '/var/lib/oldap-jena/dataset')
        self.assertEqual(environment['OLDAP_JENA_DATA'], values['oldap_jena_root'] + '/data')


if __name__ == '__main__':
    unittest.main()
