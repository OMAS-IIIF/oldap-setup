#!/usr/bin/env python3
"""Plan/apply image-only updates to installed Jena applications.

Compose remains authoritative for secrets, mounts, commands and infrastructure.
Small image overrides are selected through the existing .env and batch selectors.
No images are built, no imports started, and no namespace owner is recreated.
Run as the deployment user (root on the supported VMs). Output contains only
image references, component names and recovery paths; expanded Compose is private.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

LOCK_PATHS = ('/srv/storage/oldap-data/job-locks/maintenance.lock', '/var/lib/oldap-jena-recovery/lock')
SCHEDULE_UNITS = tuple(Path('/etc/systemd/system') / name for name in
                       ('oldap-harvest.service', 'oldap-backup.service', 'oldap-jena-backup.service'))

COMPONENTS = {
    'api': ('oldap-api', 'oldap-jena-identity'),
    'app': ('oldap-app',), 'fasnacht': ('fasnachts-page',),
    'tools': ('oldap-tools',), 'salsah': ('salsah-2',),
    'harvesters': ('oldap-harvesters',), 'harvesters_ocr': ('oldap-harvesters',),
}
REPOSITORIES = {'api': 'oldap-api', 'app': 'oldap-app', 'fasnacht': 'fasnachts-page',
                'tools': 'oldap-tools', 'salsah': 'salsah-2',
                'harvesters': 'oldap-harvesters', 'harvesters_ocr': 'oldap-harvesters'}
BATCH_KEYS = {'harvesters': 'OLDAP_EUROPEANA_COMPOSE_FILE',
              'harvesters_ocr': 'OLDAP_SWISSCOVERY_COMPOSE_FILE'}
MANAGED = {'core': 'routine-images.yml', 'harvesters': 'routine-europeana-images.yml',
           'harvesters_ocr': 'routine-swisscovery-images.yml'}


def release_images(value):
    """Validate a partial release selection; only immutable known images allowed."""
    if not isinstance(value, dict) or not value or set(value) - set(COMPONENTS):
        raise ValueError('Release must map known component names to image digests.')
    for name, image in value.items():
        if not isinstance(image, str) or not re.fullmatch(
                r'lrosenth/' + REPOSITORIES[name] + r'@sha256:[0-9a-f]{64}', image):
            raise ValueError('Expected immutable image digest for ' + name)
    return value


def environment(text):
    """Read literal Compose selector values without executing shell or secrets."""
    result = {}
    for line in text.splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key in {'COMPOSE_FILE', *BATCH_KEYS.values()}:
                if key in result:
                    raise ValueError('Duplicate Compose selector: ' + key)
                result[key] = value.strip().strip('"\'')
    return result


def select_environment(text, selectors):
    """Replace only explicit selector lines; retain all other bytes/text lines."""
    lines = text.splitlines(keepends=True)
    for key, value in selectors.items():
        matches = [i for i, line in enumerate(lines) if line.startswith(key + '=')]
        if len(matches) > 1:
            raise ValueError('Duplicate Compose selector: ' + key)
        if matches:
            lines[matches[0]] = key + '=' + value + '\n'
        else:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append(key + '=' + value + '\n')
    return ''.join(lines)


def paths(root, selection):
    """Require ordinary installed Compose files within the deployment directory."""
    result = []
    for name in selection.split(':'):
        p = Path(name) if name.startswith('/') else root / name
        if not name or p.is_symlink() or not p.is_file() or p.resolve().parent != root.resolve():
            raise ValueError('Missing or unsupported installed Compose selection.')
        result.append(p)
    return result


def selections(root, env):
    """Match existing launcher rules for both overlay and consolidated installs."""
    core = paths(root, env.get('COMPOSE_FILE', 'docker-compose.yml'))
    result = {'core': core}
    for component, key in BATCH_KEYS.items():
        if env.get(key):
            result[component] = paths(root, env[key])
        elif any(p.name == 'jena-compose.yml' for p in core):
            extra = (['swisscovery-compose.yml', 'jena-swisscovery-compose.yml']
                     if component == 'harvesters_ocr' else ['jena-harvesters-compose.yml'])
            if all((root / name).is_file() for name in extra):
                result[component] = core + [root / name for name in extra]
    return result


def command(args, *, cwd=None, timeout=300):
    """Capture potentially secret-bearing output; errors never echo it to Ansible."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('COMPOSE_')}
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(args[:3]) + ' (exit ' + str(result.returncode) + ')')
    return result.stdout


def compose(root, files, *args):
    """Use explicit files and all profiles for inspection of on-demand services."""
    base = ['docker', 'compose', '--project-directory', str(root), '--env-file', str(root / '.env'), '--profile', '*']
    for p in files:
        base += ['-f', str(p)]
    return command(base + list(args), cwd=root)


def configs(root, selected):
    """Keep expanded configuration in memory; never print or save its secrets."""
    return {key: json.loads(compose(root, files, 'config', '--format', 'json'))['services']
            for key, files in selected.items()}


def plan(images, current):
    """Resolve requested components, enforcing the coupled API/identity boundary."""
    core = current['core']
    if core.get('oldap-api', {}).get('environment', {}).get('OLDAP_BACKEND') != 'jena':
        raise ValueError('The installed API must explicitly select Jena.')
    if not {'oldap-jena', 'oldap-jena-identity'} <= set(core):
        raise ValueError('Installed namespace owner and identity service are required.')
    rows = []
    for component, image in images.items():
        group = component if component in BATCH_KEYS else 'core'
        services = current.get(group, {})
        names = COMPONENTS[component]
        present = [name for name in names if name in services]
        if component == 'api' and len(present) != 2:
            raise ValueError('API update requires both API and identity services.')
        if group != 'core' and present:
            if services[present[0]].get('environment', {}).get('OLDAP_BACKEND') != 'jena':
                raise ValueError('Batch service must explicitly select Jena.')
        rows.append({'component': component, 'group': group, 'services': present,
                     'current': {name: services[name]['image'] for name in present},
                     'image': image, 'status': 'installed' if present else 'not-installed',
                     'configuration_change': any(services[name]['image'] != image for name in present)})
    return rows


def overrides(root, selected, current, rows):
    """Merge selected images with earlier managed overrides; preserve other pins."""
    desired = {}
    for row in rows:
        if not row['services']:
            continue
        group = row['group']
        if group not in desired:
            target = root / MANAGED[group]
            if target.is_symlink():
                raise ValueError('Refusing symlink image override.')
            if target.exists() and target not in selected.get(group, []):
                raise ValueError('Unselected managed image file exists; inspect before updating.')
            desired[group] = json.loads(target.read_text()) if target.exists() else {'services': {}}
            if set(desired[group]) != {'services'} or not isinstance(desired[group]['services'], dict):
                raise ValueError('Invalid managed image override.')
            allowed = {service: component for component, names in COMPONENTS.items()
                       if (component == group if group != 'core' else component not in BATCH_KEYS)
                       for service in names}
            for service, spec in desired[group]['services'].items():
                if service not in allowed or not isinstance(spec, dict) or set(spec) != {'image'}:
                    raise ValueError('Managed overrides must contain only application image fields.')
                release_images({allowed[service]: spec['image']})
        for name in row['services']:
            desired[group]['services'][name] = {'image': row['image']}
    return desired


def atomic(path, content, mode=0o600):
    """Replace a private configuration file atomically on the same filesystem."""
    if path.is_symlink():
        raise ValueError('Refusing symlink destination.')
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if path.exists():
            stat = path.stat()
            os.chown(temp, stat.st_uid, stat.st_gid)
            mode = stat.st_mode & 0o777
        temp.chmod(mode)
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temp.unlink(missing_ok=True)


def container(root, files, service):
    """Inspect exactly one running container for an already deployed service."""
    ids = compose(root, files, 'ps', '-q', service).split()
    if len(ids) != 1:
        raise ValueError('Expected one running container for ' + service)
    info = json.loads(command(['docker', 'inspect', ids[0]]))[0]
    if not info['State']['Running']:
        raise ValueError('Service is not running: ' + service)
    return info


def activate(root, files, services):
    """Restart only requested application consumers, in dependency order."""
    ordered = [s for s in ('oldap-jena-identity', 'oldap-api', 'oldap-app', 'fasnachts-page', 'salsah-2') if s in services]
    for name in ordered:
        compose(root, files, 'up', '-d', '--no-deps', '--wait', '--wait-timeout', '90', name)
    if 'oldap-api' in ordered:
        info = container(root, files, 'oldap-api')
        command(['docker', 'exec', info['Id'], 'python', '-c',
                 "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:3031/health',timeout=10).read().strip()==b'ready'; assert urlopen('http://127.0.0.1:8000/status',timeout=10).status==200"])


def installed_locks(root):
    """Require recovery coordination and every installed batch coordination lock.

    Unscheduled home installations have neither the shared lock directory nor
    scheduler units/overlay. Do not manufacture a lock no other process uses.
    A partially installed or damaged scheduling setup must still fail closed.
    """
    batch, recovery = map(Path, LOCK_PATHS)
    batch_installed = (batch.exists() or batch.is_symlink() or batch.parent.exists()
                       or (root / 'harvest-schedule-compose.yml').exists()
                       or any(p.exists() or p.is_symlink() for p in SCHEDULE_UNITS))
    return ([batch] if batch_installed else []) + [recovery]


def apply(root, images):
    """Serialize with recovery/backup, preflight, then replace images or roll back.

    All selected images are pulled and imported before live selection changes.
    Backups are private and durable; a failed rollback retains the recovery path.
    On-demand tools/batches are never started. Namespace/Redis containers are
    inspected before and after, but never included in Compose up commands.
    """
    with ExitStack() as stack:
        for p in installed_locks(root):
            if p.is_symlink() or not p.is_file():
                raise ValueError('Required installed maintenance lock is missing: ' + str(p))
            stream = stack.enter_context(p.open('r+'))
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        env_text = (root / '.env').read_bytes().decode('utf-8')
        selected = selections(root, environment(env_text))
        inputs = {p: p.read_bytes() for files in selected.values() for p in files}
        current = configs(root, selected)
        rows = plan(images, current)
        desired = overrides(root, selected, current, rows)
        protected = {name: container(root, selected['core'], name)['Id']
                     for name in ('oldap-jena', 'redis') if name in current['core']}
        restart = set()
        for row in rows:
            if not row['services']:
                continue
            command(['docker', 'pull', row['image']], timeout=600)
            if row['component'] in ('api', 'tools', 'harvesters', 'harvesters_ocr'):
                command(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python', row['image'], '-c',
                         'from oldaplib.src.jena_connection import JenaConnection'])
            clis = (['oldap-tools'] if row['component'] == 'tools' else
                    ['oldap-harvest-europeana', 'oldap-harvest-swisscovery']
                    if row['component'] in BATCH_KEYS else [])
            for cli in clis:
                command(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', cli, row['image'], '--help'])
            if row['component'] == 'harvesters_ocr':
                command(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', '/opt/ocr-python',
                         row['image'], '-c', 'import torch, kraken, pypdf, pypdfium2; assert not torch.cuda.is_available()'])
            new_id = json.loads(command(['docker', 'image', 'inspect', row['image']]))[0]['Id']
            for name in row['services']:
                if row['group'] == 'core' and name not in ('oldap-tools', 'oldap-harvesters'):
                    if container(root, selected['core'], name)['Image'] != new_id:
                        restart.add(name)
        # API and identity consumers always roll together if either image differs.
        if restart & {'oldap-api', 'oldap-jena-identity'}:
            restart.update(('oldap-api', 'oldap-jena-identity'))
        updates, selectors = {}, {}
        for group, document in desired.items():
            target = root / MANAGED[group]
            updates[target] = (json.dumps(document, indent=2) + '\n').encode()
            files = [p for p in selected[group] if p != target]
            if group != 'core' and 'core' in desired:
                core_override = root / MANAGED['core']
                files = [p for p in files if p != core_override] + [core_override]
            files += [target]
            selectors['COMPOSE_FILE' if group == 'core' else BATCH_KEYS[group]] = ':'.join(p.name for p in files)
        updates[root / '.env'] = select_environment(env_text, selectors).encode()
        changed = {p: data for p, data in updates.items() if not p.exists() or p.read_bytes() != data}
        if not changed and not restart:
            return {'status': 'unchanged', 'plan': rows}
        backup = root / ('routine-update-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        backup.mkdir(mode=0o700)
        before = {p: p.read_bytes() if p.exists() else None for p in changed}
        for p, data in before.items():
            if data is not None:
                atomic(backup / p.name, data)
        atomic(backup / 'manifest.json', json.dumps({'files': {p.name: data is not None for p, data in before.items()},
                                                     'restart': sorted(restart)}).encode())
        applied = []
        activation_started = False
        try:
            # Validate candidates using temporary overrides before changing .env.
            candidates = {}
            for group, document in desired.items():
                candidates[group] = backup / ('candidate-' + MANAGED[group])
                atomic(candidates[group], (json.dumps(document) + '\n').encode())
            for group, document in desired.items():
                extra = ([candidates['core']] if group != 'core' and 'core' in candidates else []) + [candidates[group]]
                actual = json.loads(compose(root, selected[group] + extra, 'config', '--format', 'json'))['services']
                expected = json.loads(json.dumps(current[group]))
                for candidate in extra:
                    for name, spec in json.loads(candidate.read_text())['services'].items():
                        if name not in expected:
                            raise ValueError('Candidate introduces an uninstalled service.')
                        expected[name]['image'] = spec['image']
                if actual != expected:
                    raise ValueError('Candidate changes more than image references.')
            if any(p.read_bytes() != data for p, data in inputs.items()):
                raise ValueError('Installed Compose inputs changed during preflight.')
            if (root / '.env').read_bytes().decode('utf-8') != env_text:
                raise ValueError('Installed selection changed during preflight.')
            for p, data in changed.items():
                atomic(p, data)
                applied.append(p)
            final = selections(root, environment((root / '.env').read_bytes().decode('utf-8')))
            activation_started = True
            activate(root, final['core'], restart)
            for name, identity in protected.items():
                if container(root, final['core'], name)['Id'] != identity:
                    raise ValueError('Infrastructure container changed unexpectedly.')
        except Exception as failure:
            try:
                for p in reversed(applied):
                    if p.read_bytes() != changed[p]:
                        raise ValueError('Concurrent modification; refusing to overwrite it during rollback.')
                    data = before[p]
                    if data is None:
                        p.unlink(missing_ok=True)
                    else:
                        atomic(p, data)
                if activation_started:
                    activate(root, selected['core'], restart)
            except Exception:
                raise RuntimeError('Update and rollback failed; inspect private backup ' + str(backup)) from None
            raise RuntimeError('Update failed; preceding selection restored. Backup: ' + str(backup)) from failure
        return {'status': 'updated', 'backup': str(backup), 'restarted': sorted(restart), 'plan': rows}


def main():
    """CLI used by Ansible; preview is the default and has no persistent writes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/opt/oldap/compose'))
    parser.add_argument('--images', required=True, help='JSON component-to-digest mapping; no credentials')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        images = release_images(json.loads(args.images))
        root = args.root.resolve()
        if (root / '.env').is_symlink():
            raise ValueError('Refusing symlink environment file.')
        if args.apply:
            report = apply(root, images)
        else:
            selected = selections(root, environment((root / '.env').read_bytes().decode('utf-8')))
            report = {'status': 'preview', 'plan': plan(images, configs(root, selected))}
        print(json.dumps(report))
    except Exception as error:
        parser.exit(1, 'Jena update failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
