#!/usr/bin/env python3
"""Pull one published Jena snapshot; accept only a fully verified pair of archives.

Run on the approved receiver with its dedicated SSH configuration. Interrupted transfers remain
in incoming/ and can be retried with the same ID. No extraction, pruning, Borg
initialization or service operation is performed. Home remains the default; production requires explicit selection.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


# Receiver policy is local, never taken from the downloaded manifest.
ENDPOINTS = {
    'home': {'api': 'api.home.org', 'media': 'media.home.org'},
    'production': {'api': 'dhlab-oldap.dhlab.unibas.ch', 'media': 'dhlab-iii.dhlab.unibas.ch'},
}


def validate_manifest(data, snapshot_id, environment='home'):
    """Reject unexpected endpoints, paths, sizes or hashes before invoking rsync."""
    if data.get('snapshot_id') != snapshot_id or data.get('status') != 'offline-compared':
        raise ValueError('Snapshot identity/status mismatch')
    for role, prefix in [('api', '/srv/storage'), ('media', '/data')]:
        entry = data[role]
        expected = f'{prefix}/oldap-jena-snapshot-{snapshot_id}/{role}.tar'
        if entry.get('path') != expected:
            raise ValueError('Unexpected archive path')
        if type(entry.get('bytes')) is not int or entry['bytes'] <= 0:
            raise ValueError('Invalid archive size')
        if not re.fullmatch('[0-9a-f]{64}', entry.get('sha256', '')):
            raise ValueError('Invalid SHA-256')
    if data['media'].get('host') != ENDPOINTS[environment]['media']:
        raise ValueError('Unexpected media host')
    return data


def verify(path, entry):
    """Stream an archive to check exact length and digest without extracting it."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size != entry['bytes']:
        raise ValueError(f'Archive size/type mismatch: {path.name}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != entry['sha256']:
        raise ValueError(f'Archive checksum mismatch: {path.name}')


def pull(snapshot_id, root, config, environment='home'):
    """Download and atomically publish one verified set; retain failures for retry.

    A receiver-wide advisory lock excludes concurrent invocations. Remote ready.json
    is published only after the producer has compared archives and resumed services.
    The matching marker is re-read before local acceptance.
    """
    if not re.fullmatch('[a-zA-Z0-9_-]+', snapshot_id):
        raise ValueError('Invalid snapshot ID')
    endpoints = ENDPOINTS[environment]
    os.umask(0o077)
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.pull.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        incoming, complete = root / 'incoming', root / 'snapshots'
        for directory in (incoming, complete):
            directory.mkdir(mode=0o700, exist_ok=True)
        target = complete / snapshot_id
        if target.exists():
            raise FileExistsError('Snapshot already accepted; refusing overwrite')
        stage = incoming / snapshot_id
        if stage.is_symlink():
            raise ValueError('Staging directory must not be a symlink')
        stage.mkdir(mode=0o700, exist_ok=True)
        ssh = ['ssh', '-F', str(config)]
        manifest_path = f'/srv/storage/oldap-jena-snapshot-{snapshot_id}/ready.json'
        def fetch_manifest():
            return validate_manifest(json.loads(subprocess.check_output(
                ssh + [endpoints['api'], 'cat', manifest_path])), snapshot_id, environment)
        manifest = fetch_manifest()
        for role in ('api', 'media'):
            archive = stage / f'{role}.tar'
            if archive.is_symlink():
                raise ValueError('Archive destination must not be a symlink')
            # Reuse only an archive already verified against the source manifest.
            # Whole-file transport avoids expensive delta matching of huge tar
            # files against incomplete copies. A partial archive is retransmitted.
            reusable = False
            if archive.exists():
                try:
                    verify(archive, manifest[role])
                    reusable = True
                except ValueError:
                    pass
            if not reusable:
                subprocess.run(['rsync', '-t', '--whole-file', '--ignore-times',
                                '--partial', '-e', shlex.join(ssh),
                                f'{endpoints[role]}:{manifest[role]["path"]}',
                                str(archive)], check=True)
                verify(archive, manifest[role])
            archive.chmod(0o600)
        if fetch_manifest() != manifest:
            raise ValueError('Published manifest changed during transfer')
        with (stage / 'manifest.json').open('w') as stream:
            json.dump(manifest, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        # Only this rename marks a snapshot complete. Readers must ignore incoming/.
        stage.rename(target)
        return target


def main():
    """Parse the explicit snapshot ID and receiver paths; report accepted location."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot_id')
    parser.add_argument('--root', type=Path, default=Path.home() / 'OLDAP_BACKUP')
    parser.add_argument('--environment', choices=ENDPOINTS, default='home')
    parser.add_argument('--ssh-config', type=Path)
    args = parser.parse_args()
    if args.environment == 'production' and args.ssh_config is None:
        parser.error('Production requires an explicit --ssh-config')
    config = args.ssh_config or Path.home() / '.ssh/oldap_home_backup.conf'
    print(pull(args.snapshot_id, args.root, config, args.environment))


if __name__ == '__main__':
    main()
