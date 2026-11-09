"""Exercise the actual Jena Compose overlay in a fresh, disposable Docker project.

Requires a built Jena release, sibling migration sources and installed API image.
Creates only named test containers and temporary storage; publishes no host ports.
Finally removes its own project. Run on the intended Linux host as well as locally.
The identity route and token codec are real; full API/account migration is separate.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = 'eclipse-temurin@sha256:ecdc0adb37bde1a281c4d245a3cd535004b1fc8322d560f5b09463b248c81df0'


def run(release, api_source, lib_source, api_image, runtime, packaged=False):
    """Verify loopback, callback, isolation and coordinated container replacement."""
    project = 'oldap-jena-network-' + secrets.token_hex(5)
    with tempfile.TemporaryDirectory(prefix=project) as temporary:
        directory = Path(temporary)
        # Docker Desktop and Linux must both permit the explicit container UID.
        directory.chmod(0o755)
        data = directory / 'data'
        data.mkdir(mode=0o777)
        data.chmod(0o777)  # disposable parent only; Jena creates dataset with 0700
        config = directory / 'service.properties'
        credentials = {name: secrets.token_hex(32) for name in ('SERVICE', 'BOOTSTRAP', 'FULLTEXT', 'IDENTITY')}
        config.write_text('dataset=/var/lib/oldap-jena/dataset\nport=3031\ntransactionLifetimeMillis=30000\n'
                          'identityUrl=http://127.0.0.1:8001/internal/jena/identity\n' +
                          ''.join(f'{name.lower() if name != "SERVICE" else "service"}Secret={value}\n'
                                  for name, value in credentials.items()))
        config.chmod(0o600)
        # On Linux this runner is intended for UID 1000 (rosenth on home.org).
        # Local Docker Desktop maps bind-mount ownership to the container user.
        env = {**os.environ, 'OLDAP_JENA_RUNTIME_IMAGE': runtime,
               'OLDAP_JENA_API_IMAGE': api_image, 'OLDAP_JENA_TOOLS_IMAGE': api_image,
               'OLDAP_JENA_RELEASE': str(release), 'OLDAP_JENA_CONFIG': str(config),
               'OLDAP_JENA_DATA': str(data), 'OLDAP_JENA_HEAP_MB': '512',
               **{'OLDAP_JENA_' + key + '_KEY': value for key, value in credentials.items()}}
        # Both processes verify the same synthetic access tokens, as in deployment.
        env['OLDAP_ACCESS_JWT_SECRET'] = secrets.token_hex(32)
        env['OLDAP_JENA_IDENTITY_APP'] = str(ROOT / 'scripts/jena_identity.py')
        peer = '/check/jena_network_peer.py'
        mounts = [f'{ROOT / "tests/jena_network_peer.py"}:{peer}:ro',
                  f'{api_source}:/source/api:ro', f'{lib_source}:/source/lib:ro']
        python_env = {'PYTHONPATH': '/source/api:/source/lib', 'PYTHONDONTWRITEBYTECODE': '1',
                      'OLDAP_ACCESS_JWT_SECRET': env['OLDAP_ACCESS_JWT_SECRET']}
        if packaged:
            mounts = mounts[:1]
            python_env.pop('PYTHONPATH')
        base = {'services': {
            'oldap-api': {'image': api_image, 'entrypoint': ['python', peer, 'serve'],
                          'environment': python_env, 'volumes': mounts,
                          'expose': ['8000'],
                          'healthcheck': {'disable': True}},
            'redis': {'image': 'redis:7-alpine'},
            'oldap-tools': {'image': api_image, 'profiles': ['tools']},
            'oldap-harvesters': {'image': api_image, 'profiles': ['tools']},
            'graphdb': {'image': api_image}, 'graphdb-init': {'image': api_image},
            'outside': {'image': api_image, 'entrypoint': ['python', peer, 'outside'],
                        'volumes': mounts, 'profiles': ['check']}}}
        base_path = directory / 'base.json'
        base_path.write_text(json.dumps(base))
        command = ['docker', 'compose', '--project-name', project, '--env-file', '/dev/null',
                   '-f', str(base_path), '-f', str(ROOT / 'jena-compose.yml')]

        def compose(*args, capture=False):
            return subprocess.run([*command, *args], env=env, check=True,
                                  capture_output=capture, text=True)

        def ready():
            # No backend health success substitutes for callback/transaction checks.
            for _ in range(60):
                result = subprocess.run([*command, 'exec', '-T', 'oldap-api', 'python', '-c',
                    "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:3031/health',timeout=1).read()==b'ready\\n'; assert urlopen('http://127.0.0.1:8000/network-check',timeout=1).status==200"],
                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    return
                time.sleep(1)
            raise TimeoutError('Owned Jena/API peer did not become ready')

        try:
            # Initialize only the NEW temporary dataset, then stop cleanly.
            initial = compose('run', '-d', '--no-deps', 'oldap-jena',
                              '/run/oldap-jena/service.properties', '--init', capture=True).stdout.strip()
            for _ in range(60):
                log = subprocess.check_output(['docker', 'logs', initial], stderr=subprocess.STDOUT, text=True)
                if 'OLDAP Jena service ready' in log:
                    break
                time.sleep(1)
            else:
                raise TimeoutError('Owned initialization failed')
            subprocess.run(['docker', 'stop', '--time', '90', initial], check=True, capture_output=True)
            subprocess.run(['docker', 'rm', initial], check=True, capture_output=True)
            compose('up', '-d', 'oldap-jena', 'oldap-api')
            ready()
            compose('exec', '-T', 'oldap-api', 'python', peer, 'transaction')
            compose('run', '--rm', '--no-deps', 'outside')
            # Remove every namespace consumer BEFORE replacing its owner.
            compose('stop', 'oldap-api', 'oldap-jena-identity', 'oldap-jena')
            compose('rm', '-f', 'oldap-api', 'oldap-jena-identity', 'oldap-jena')
            compose('up', '-d', 'oldap-jena', 'oldap-api')
            ready()
            compose('exec', '-T', '-e', 'CHECK_EXISTING=1', 'oldap-api', 'python', peer, 'transaction')
            compose('run', '--rm', '--no-deps', 'outside')
            print('PASS coordinated namespace replacement; no host ports published')
        finally:
            compose('down', '--volumes', '--remove-orphans', '--timeout', '90')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--api-source', type=Path, default=ROOT.parent / 'oldap-api')
    parser.add_argument('--lib-source', type=Path, default=ROOT.parent / 'oldaplib')
    parser.add_argument('--api-image', default='lrosenth/oldap-api:v0.2.37')
    parser.add_argument('--runtime-image', default=RUNTIME)
    parser.add_argument('--packaged', action='store_true', help='Test installed wheels without source mounts')
    args = parser.parse_args()
    run(args.release.resolve(), args.api_source.resolve(), args.lib_source.resolve(), args.api_image, args.runtime_image, args.packaged)
