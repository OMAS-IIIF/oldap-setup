"""Opt-in real Compose argument/lock test using a network-isolated CLI fixture."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('OLDAP_TEST_DOCKER_IMAGE'), 'Set an existing Python/flock image for real Compose tests')
class LauncherRuntimeTests(unittest.TestCase):
    def test_defaults_and_explicit_overrides_for_both_backends_and_sources(self):
        image = os.environ['OLDAP_TEST_DOCKER_IMAGE']
        subprocess.run(['docker', 'image', 'inspect', image], capture_output=True, check=True)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder/'run-harvester.sh').write_text((ROOT/'scripts/run-harvester.sh').read_text())
            fixture = folder/'cli'
            fixture.write_text('#!/usr/bin/env python\nimport json,sys; print(json.dumps(sys.argv[1:]))\n')
            fixture.chmod(0o755)
            locks = folder/'locks'
            locks.mkdir()
            base = {'services': {'oldap-harvesters': {
                'image': image, 'profiles': ['harvesters'], 'platform': 'linux/amd64', 'network_mode': 'none',
                'command': ['--config', '/fixture/europeana with spaces.toml', '--write-oldap'],
                'volumes': [f'{fixture}:/usr/local/bin/oldap-harvest-europeana:ro',
                            f'{fixture}:/usr/local/bin/oldap-harvest-swisscovery:ro',
                            f'{ROOT}/scripts/run-locked.py:/run/oldap-batch/run-locked.py:ro',
                            f'{locks}:/run/oldap-batch/locks', f'{locks}:/var/lib/swisscovery/locks']}}}
            (folder/'docker-compose.yml').write_text(json.dumps(base))
            swiss = ['--config', '/fixture/swisscovery.toml', '--write-oldap', '--text-model', 'a model.mlmodel']
            (folder/'swisscovery-compose.yml').write_text(json.dumps({'services': {'oldap-harvesters': {'command': swiss}}}))
            for name in ['writer-compose.yml', 'jena-compose.yml', 'archive-policy-compose.yml',
                         'jena-harvesters-compose.yml', 'jena-swisscovery-compose.yml', 'harvest-schedule-compose.yml']:
                (folder/name).write_text('services: {}\n')
            for backend in ['graphdb', 'jena', 'consolidated']:
                selection = 'docker-compose.yml:writer-compose.yml' if backend == 'graphdb' else 'docker-compose.yml:jena-compose.yml:archive-policy-compose.yml'
                if backend == 'consolidated':
                    selection = 'docker-compose.yml'
                    for provider in ['europeana','swisscovery']:
                        override = {'services': {}} if provider == 'europeana' else {'services': {'oldap-harvesters': {'command': swiss}}}
                        (folder/f'batch-{provider}.yml').write_text(json.dumps(override))
                extra = ''.join(f'OLDAP_{provider.upper()}_COMPOSE_FILE=docker-compose.yml:batch-{provider}.yml\n' for provider in ['europeana','swisscovery']) if backend == 'consolidated' else ''
                (folder/'.env').write_text('COMPOSE_FILE='+selection+'\n'+extra)
                for source in ['europeana', 'swisscovery']:
                    defaults = base['services']['oldap-harvesters']['command'] if source == 'europeana' else swiss
                    for arguments in [[], ['--help'], ['--config', 'explicit spaced.toml', '--dry-run-output', 'out.json']]:
                        with self.subTest(backend=backend, source=source, arguments=arguments):
                            result = subprocess.run(['sh', str(folder/'run-harvester.sh'), source, *arguments],
                                                    cwd='/', capture_output=True, text=True, check=True)
                            self.assertEqual(json.loads(result.stdout.splitlines()[-1]), arguments or defaults)
