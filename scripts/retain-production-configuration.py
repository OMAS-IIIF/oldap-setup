#!/usr/bin/env python3
"""Retain online production configuration and configured images on each host.

Run as root through oldap-production-retain.yml. The new output directory is
private and readable by the established rosenth backup account. No service is
stopped or reconfigured. Redis, GraphDB and media contents are deliberately not
claimed as a coordinated snapshot. Errors leave incomplete artifacts for review;
only a final manifest certifies configuration comparison and container stability.
"""
import argparse
import glob
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess


def output(args, **kwargs):
    """Capture command output privately; callers must not log secret-bearing data."""
    return subprocess.check_output(args, stderr=subprocess.PIPE, **kwargs)


def stable_inventory(containers):
    """Keep only identities needed to detect deployment or restart during capture."""
    return {c['Name']: {'id': c['Id'], 'image_id': c['Image'],
                        'started': c['State']['StartedAt']} for c in containers}


def configuration_inputs(role, compose):
    """Resolve base and provider overlays privately, including read-only job inputs."""
    selections = [None]
    if role == 'api':
        # Profiles alone do not select the provider-specific Swisscovery overlay.
        selections += [
            ['docker-compose.yml', 'writer-compose.yml', 'harvest-schedule-compose.yml'],
            ['docker-compose.yml', 'writer-compose.yml', 'swisscovery-compose.yml', 'harvest-schedule-compose.yml'],
        ]
    refs = set()
    provider_inputs = set()
    for selection in selections:
        environment = dict(os.environ)
        if selection:
            environment['COMPOSE_FILE'] = ':'.join(str(Path(compose)/name) for name in selection)
        configuration = json.loads(output(['docker', 'compose', '--profile', '*', 'config', '--format', 'json'],
                                          cwd=compose, env=environment))
        for service in configuration['services'].values():
            if service.get('image'):
                refs.add(service['image'])
        if selection:
            for mount in configuration['services']['oldap-harvesters'].get('volumes', []):
                if mount.get('type') == 'bind' and mount.get('read_only'):
                    provider_inputs.add(mount['source'])
    return sorted(refs), provider_inputs


def retain(role, root):
    """Save a new role-specific preparation package, not live application data.

    Args:
        role: Either api or media; selects the inventoried deployment directory.
        root: New private direct child of /var/tmp with an oldap-rollback- prefix.

    Raises:
        ValueError: The role or output path is not allowed.
        RuntimeError: Source containers changed during capture.
        subprocess.CalledProcessError: Capture, image resolution or comparison failed.
    """
    if role not in {'api', 'media'} or root.parent != Path('/var/tmp') or not root.name.startswith('oldap-rollback-'):
        raise ValueError('Invalid source role or retention path')
    os.umask(0o077)
    root.mkdir(mode=0o700, exist_ok=False)
    account = pwd.getpwnam('rosenth')
    os.chown(root, account.pw_uid, account.pw_gid)
    names = output(['docker', 'ps', '-q'], text=True).split()
    containers = json.loads(output(['docker', 'inspect', *names]))
    before = stable_inventory(containers)
    compose = '/opt/oldap/compose' if role == 'api' else '/opt/oldap-mediaserver/compose'
    refs, provider_inputs = configuration_inputs(role, compose)
    images = json.loads(output(['docker', 'image', 'inspect', *refs]))
    running_ids = {c['Image'] for c in containers}
    ids = sorted({i['Id'] for i in images} | running_ids)
    # API running images are streamed separately. Media Docker requires sudo,
    # so retain all media image bytes here before the unprivileged SSH transfer.
    extra = sorted(set(ids) - running_ids) if role == 'api' else ids
    paths = ['/opt/oldap', '/srv/storage/caddy'] if role == 'api' else ['/opt/oldap-mediaserver']
    for pattern in ['/etc/systemd/system/oldap*', '/etc/oldap*', '/usr/local/bin/oldap*']:
        paths.extend(glob.glob(pattern))
    paths.extend(provider_inputs)
    # A parent already retained covers nested configuration files and directories.
    unique_paths = set(paths)
    paths = sorted(path for path in unique_paths if not any(
        str(parent) in unique_paths for parent in Path(path).parents))
    archive = root / 'configuration.tar'
    output(['tar', '--acls', '--xattrs', '--exclude=opt/oldap/compose/redis-data',
            '-cpf', str(archive), '-C', '/', *[p.lstrip('/') for p in paths]])
    output(['tar', '--compare', '--acls', '--xattrs', '-f', str(archive), '-C', '/'])
    report = {
        'role': role,
        'scope': 'online configuration and exact image retention; not coordinated data backup',
        'paths': paths, 'containers': before,
        'configured_images': [{'reference': ref, 'id': item['Id']} for ref, item in zip(refs, images)],
        'extra_image_ids': extra, 'archives': {},
    }
    if extra:
        with (root / 'extra-images.tar').open('xb') as stream:
            subprocess.run(['docker', 'image', 'save', *extra], stdout=stream,
                           stderr=subprocess.PIPE, check=True)
    current_names = output(['docker', 'ps', '-q'], text=True).split()
    after = stable_inventory(json.loads(output(['docker', 'inspect', *current_names])))
    if after != before:
        raise RuntimeError('Source containers changed during retention')
    for path in root.glob('*.tar'):
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        report['archives'][path.name] = {'sha256': digest, 'bytes': path.stat().st_size}
        os.chown(path, account.pw_uid, account.pw_gid)
    manifest = root / 'manifest.json'
    manifest.write_text(json.dumps(report, indent=2) + '\n')
    os.chown(manifest, account.pw_uid, account.pw_gid)
    print(json.dumps({'role': role, 'path': str(root), 'images': len(ids), 'extra_images': len(extra)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['api', 'media'])
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    retain(args.role, args.destination)
