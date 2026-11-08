#!/usr/bin/env python3
"""Prepare a private batch supplement for a pinned consolidated Jena release.

Inputs are resolved source provider configurations and the accepted target core
Compose document. Preserve provider commands, OCR limits and production input
mounts; replace backend wiring, image and policy with reviewed Jena values. This
builder never starts jobs or changes an installed release. Output must be new.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

CLIENT_ENV = (
    'OLDAP_ACCESS_JWT_SECRET', 'OLDAP_JWT_ISSUER', 'OLDAP_JWT_AUDIENCE',
    'OLDAP_REDIS_URL', 'OLDAP_STAGING_LOCK_REDIS_URL', 'OLDAP_ARCHIVE_POLICY_FILE',
    'OLDAP_BACKEND', 'OLDAP_TS_SERVER', 'OLDAP_TS_REPO', 'OLDAP_JENA_URL',
    'OLDAP_JENA_SERVICE_KEY', 'OLDAP_JENA_BOOTSTRAP_KEY',
    'OLDAP_JENA_FULLTEXT_KEY', 'OLDAP_JENA_IDENTITY_KEY',
)


def prepare_service(source, core, image):
    """Return a profiled Jena batch preserving reviewed provider behavior.

    Reject unknown environment/mount boundaries rather than silently dropping a
    future provider setting. No credentials are printed or copied from home.
    """
    if not re.fullmatch(r'(?:[a-z0-9/_-]+@)?sha256:[a-f0-9]{64}', image):
        raise ValueError('Require an accepted immutable image reference')
    api = core['services']['oldap-api']
    env = api['environment']
    if env.get('OLDAP_BACKEND') != 'jena':
        raise ValueError('Target core is not Jena')
    original = source['services']['oldap-harvesters']
    extra = set(original.get('environment', {})) - set(CLIENT_ENV) - {
        'OLDAP_TS_PASSWORD', 'OLDAP_TS_USER', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'}
    if extra:
        raise ValueError('Unreviewed provider environment keys')
    service = copy.deepcopy(original)
    for key in ('networks', 'depends_on', 'labels', 'entrypoint', 'container_name'):
        service.pop(key, None)
    service.update(image=image, pull_policy='never', profiles=['harvesters'],
                   network_mode='service:oldap-jena', restart='no')
    command = service.get('command')
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError('Provider requires a nonempty argument list')
    service['environment'] = {key: env[key] for key in CLIENT_ENV}
    for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        if key in original.get('environment', {}):
            service['environment'][key] = original['environment'][key]
    mounts = []
    for mount in service.get('volumes', []):
        if mount['target'] == '/run/oldap-writer-client':
            continue  # Legacy coordinator credentials must not enter the target.
        path = Path(mount.get('source', ''))
        if mount.get('type') != 'bind' or '..' in path.parts or not path.is_relative_to('/srv/storage/oldap-data/oldap-harvesters'):
            raise ValueError('Unreviewed provider input mount')
        mount.setdefault('bind', {})['create_host_path'] = False
        mounts.append(mount)
    policy = [m for m in api['volumes'] if m['target'] == '/run/oldap-policy/archive-policy.json']
    if len(policy) != 1 or not policy[0].get('read_only'):
        raise ValueError('Require exactly one read-only target archive policy')
    service['volumes'] = mounts + copy.deepcopy(policy)
    return service


def build(core_path, europeana, swisscovery, standard_image, ocr_image, output):
    """Write private overlays and launcher supplement, with checksummed inputs.

    selectors.env must be merged into the existing .env at installation, never
    substituted for it. The existing core bundle remains immutable.
    """
    os.umask(0o077)
    core = json.loads(core_path.read_text())
    services = {name: prepare_service(json.loads(path.read_text()), core, image)
                for name, path, image in [('europeana', europeana, standard_image),
                                          ('swisscovery', swisscovery, ocr_image)]}
    output.mkdir(mode=0o700)
    for name, service in services.items():
        (output/f'batch-{name}.yml').write_text(json.dumps({'services': {'oldap-harvesters': service}}, indent=2)+'\n')
    (output/'selectors.env').write_text(''.join(
        f'OLDAP_{name.upper()}_COMPOSE_FILE=docker-compose.yml:batch-{name}.yml\n' for name in services))
    repo = Path(__file__).resolve().parents[1]
    for name in ['run-harvester.sh', 'run-swisscovery.sh', 'run-locked.py', 'run-weekly-harvest.py']:
        shutil.copyfile(repo/'scripts'/name, output/name)
        (output/name).chmod(0o700)
    shutil.copyfile(repo/'harvest-schedule-compose.yml', output/'harvest-schedule-compose.yml')
    report = {'status': 'prepared_not_installed_no_jobs_started',
              'input_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [core_path, europeana, swisscovery]},
              'images': {name: svc['image'] for name, svc in services.items()},
              'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}}
    (output/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['core', 'europeana', 'swisscovery', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--standard-image', required=True)
    parser.add_argument('--ocr-image', required=True)
    args = parser.parse_args()
    print(build(args.core, args.europeana, args.swisscovery, args.standard_image, args.ocr_image, args.output)['status'])
