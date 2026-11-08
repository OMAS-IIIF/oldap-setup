#!/usr/bin/env python3
"""Pull a fresh matched snapshot, verify encrypted Borg storage, then retain safely.

Run on the office Mac using explicit Homebrew tools and pinned SSH. Credentials
stay in a private JSON file and subprocess environment; notifications contain no
raw logs. Nonzero Borg exits (including warnings) stop acknowledgement/pruning.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess


def sibling(name):
    """Load adjacent operator scripts without depending on a Python package install."""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


transport = sibling('production-backup-transport')
puller = sibling('pull-home-snapshot')
ROOT = Path('/Users/rosenth/OLDAP_BACKUP/jena')
CREDENTIALS = Path('/Users/rosenth/.config/oldap/jena-backup.json')
SSH_CONFIG = Path('/Users/rosenth/.ssh/oldap_production_backup.conf')
BORG = '/opt/homebrew/bin/borg'
LATEST = '/srv/storage/oldap-jena-latest.json'


def fresh_manifest(data, now=None):
    """Require this night's completion, not yesterday's apparent success (12h max)."""
    sid = data['snapshot_id']
    if not re.fullmatch(transport.ID_PATTERN, sid):
        raise ValueError('Invalid automatic snapshot ID')
    puller.validate_manifest(data, sid, 'production')
    completed = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
    if completed.tzinfo is None:
        raise ValueError('Completion needs timezone')
    age = ((now or datetime.now(timezone.utc)) - completed).total_seconds()
    if age < -300 or age > 12 * 3600:
        raise ValueError('Missing current-night snapshot: completion is stale or in future')
    return data


def retirement_candidates(api, media, keep=3):
    """Retire only identical paired acknowledgements, preserving unconfirmed copies."""
    paired = []
    for sid in api.keys() & media.keys():
        if api[sid] != media[sid]:
            raise ValueError('Source acknowledgement mismatch')
        if transport.validate_receipt(api[sid]) != sid:
            raise ValueError('Receipt identity mismatch')
        paired.append(sid)
    return sorted(paired, reverse=True)[keep:]


class Receiver:
    """One serialized office backup with explicit storage/trust boundaries."""

    def __init__(self):
        info = CREDENTIALS.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
            raise ValueError('Credentials must be an owned mode-0600 regular file')
        config = json.loads(CREDENTIALS.read_text())
        self.repository = str(ROOT / 'borg')
        if config['repository'] != self.repository or config['repository_id'] != transport.REPOSITORY_ID:
            raise ValueError('Unexpected repository configuration')
        self.env = {key: value for key, value in os.environ.items() if not key.startswith('BORG_')}
        self.env.update(BORG_PASSPHRASE=config['passphrase'], TZ='Europe/Zurich')
        info = json.loads(self.borg('info', '--json', self.repository))
        if info['repository']['id'] != transport.REPOSITORY_ID or info['encryption']['mode'] != 'repokey-blake2':
            raise ValueError('Wrong repository identity/encryption')

    def borg(self, *arguments, cwd=None):
        """Treat warnings as failure; keep diagnostic output in the private job log."""
        return subprocess.check_output([BORG, *arguments], env=self.env, cwd=cwd)

    def remote(self, role, action, receipt=None):
        """Send fixed helper code over verified SSH; data travels only through stdin."""
        import shlex
        code = Path(transport.__file__).read_text()
        command = shlex.join(['python3', '-c', code, role])
        request = {'action': action}
        if receipt is not None:
            request['receipt'] = receipt
        return json.loads(subprocess.check_output(
            ['ssh', '-F', str(SSH_CONFIG), puller.ENDPOINTS['production'][role], command],
            input=json.dumps(request).encode()))

    def verify_borg(self, archive, manifest):
        """Read all stored bytes and compare the exact manifest before acceptance."""
        target = self.repository + '::' + archive
        items = [json.loads(line) for line in self.borg('list', '--json-lines', target).splitlines()]
        expected = {'api.tar': manifest['api']['bytes'], 'media.tar': manifest['media']['bytes']}
        if len(items) != 3 or {item['path'] for item in items} != {*expected, 'manifest.json'}:
            raise ValueError('Unexpected Borg contents')
        for item in items:
            if item['type'] != '-' or not item['healthy'] or item['path'] in expected and item['size'] != expected[item['path']]:
                raise ValueError('Invalid Borg file type/health/size')
        if json.loads(self.borg('extract', '--stdout', target, 'manifest.json')) != manifest:
            raise ValueError('Stored manifest mismatch')
        # Stream restored bytes through SHA-256. This proves manifest agreement
        # even when retrying an archive created before a prior job was interrupted.
        # No second full-size transport copy is needed on the receiver.
        for role in ('api', 'media'):
            with subprocess.Popen([BORG, 'extract', '--stdout', target, role + '.tar'],
                                  env=self.env, stdout=subprocess.PIPE) as process:
                digest = hashlib.sha256()
                length = 0
                for block in iter(lambda: process.stdout.read(4 * 1024 * 1024), b''):
                    digest.update(block)
                    length += len(block)
                if process.wait() != 0:
                    raise ValueError('Borg extraction failed')
            if length != manifest[role]['bytes'] or digest.hexdigest() != manifest[role]['sha256']:
                raise ValueError('Restored transport differs from source digest')
        archives = json.loads(self.borg('list', '--json', self.repository))['archives']
        return next(item['id'] for item in archives if item['name'] == archive)

    def backup(self):
        """Accept once; retries reverify the existing archive and reuse its receipt."""
        manifest = fresh_manifest(json.loads(subprocess.check_output(
            ['ssh', '-F', str(SSH_CONFIG), puller.ENDPOINTS['production']['api'], 'cat', LATEST])))
        sid = manifest['snapshot_id']
        archive = 'production-' + sid
        receipts = ROOT / 'receipts'
        receipts.mkdir(mode=0o700, exist_ok=True)
        marker = receipts / (sid + '.json')
        target = ROOT / 'snapshots' / sid
        names = {item['name'] for item in json.loads(self.borg('list', '--json', self.repository))['archives']}
        if archive not in names:
            if not target.exists():
                puller.pull(sid, ROOT, SSH_CONFIG, 'production')
            if target.is_symlink() or transport.read_json(target / 'manifest.json') != manifest:
                raise ValueError('Local snapshot differs from publication')
            for role in ('api', 'media'):
                puller.verify(target / (role + '.tar'), manifest[role])
            self.borg('create', '--compression=zstd', self.repository + '::' + archive,
                      'api.tar', 'media.tar', 'manifest.json', cwd=target)
        archive_id = self.verify_borg(archive, manifest)
        receipt = {'repository_id': transport.REPOSITORY_ID, 'archive': archive,
                   'archive_id': archive_id, 'manifest': manifest,
                   'verified_at': datetime.now(timezone.utc).isoformat()}
        if marker.exists():
            old = transport.read_json(marker)
            if any(old.get(key) != receipt[key] for key in ('repository_id', 'archive', 'archive_id', 'manifest')):
                raise ValueError('Prior receipt differs from verified archive')
            receipt = old  # Stable receipt permits interrupted acknowledgement retries.
        else:
            transport.atomic_json(marker, receipt)
        self.remote('media', 'acknowledge', receipt)
        self.remote('api', 'acknowledge', receipt)
        self.retain()
        return sid

    def retain(self):
        """Prune only after verification; keep receipts and all unconfirmed transports."""
        inventories = {role: self.remote(role, 'inventory') for role in ('api', 'media')}
        archives = {item['name']: item['id'] for item in
                    json.loads(self.borg('list', '--json', self.repository))['archives']}
        def still_archived(receipt):
            return archives.get(receipt['archive']) == receipt['archive_id']
        retired = [sid for sid in retirement_candidates(inventories['api'], inventories['media'])
                   if still_archived(inventories['api'][sid])]
        # Validate both sides of the complete plan before any deletion. Retrying a
        # half-completed deletion is safe because receipts remain on both hosts.
        for sid in retired:
            for role in ('api', 'media'):
                self.remote(role, 'validate-retirement', inventories[role][sid])
        for sid in retired:
            for role in ('media', 'api'):
                self.remote(role, 'retire', inventories[role][sid])
        local = {}
        for marker in (ROOT / 'receipts').glob('*.json'):
            receipt = transport.read_json(marker)
            sid = transport.validate_receipt(receipt)
            if marker.stem != sid:
                raise ValueError('Local receipt identity mismatch')
            local[sid] = receipt
        paired = {sid: receipt for sid, receipt in local.items()
                  if inventories['api'].get(sid) == receipt and inventories['media'].get(sid) == receipt}
        for sid in sorted(paired, reverse=True)[2:]:
            if not still_archived(paired[sid]):
                continue
            directory = ROOT / 'snapshots' / sid
            if not directory.exists():
                continue
            if directory.is_symlink() or transport.read_json(directory / 'manifest.json') != paired[sid]['manifest']:
                raise ValueError('Unexpected local transport directory')
            if any(p.name not in ('api.tar', 'media.tar', 'manifest.json') or p.is_symlink() for p in directory.iterdir()):
                raise ValueError('Unknown files in local transport')
            for role in ('api', 'media'):
                path = directory / (role + '.tar')
                if path.exists():
                    puller.verify(path, paired[sid]['manifest'][role])
                    path.unlink()
            # Keep the small manifest alongside the durable receipt.
        self.borg('prune', '--glob-archives', 'production-*', '--keep-daily=30',
                  '--keep-weekly=12', '--keep-monthly=24', self.repository)
        self.borg('compact', self.repository)


def notify(success, detail, *, test=False):
    """Mail only a bounded status; no source data, subprocess output or secrets."""
    status = 'SUCCESS' if success else 'FAILURE'
    subject = ('[TEST - no backup] ' if test else '') + status + ': OLDAP Jena office backup'
    body = f'{status}: {detail}\nHost: {socket.gethostname()}\nPrivate logs: {ROOT}/logs\n'
    result = subprocess.run(['/usr/bin/mail', '-s', subject, 'lukas.rosenthaler@unibas.ch'],
                            input=body, text=True, timeout=60, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    return result.returncode == 0


def main():
    """Require the office host; serialize the whole workflow and report failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notification-test', choices=['success', 'failure'])
    args = parser.parse_args()
    if socket.gethostname().split('.')[0] != 'dhlab-da24-002':
        parser.error('Run on the approved office receiver')
    if args.notification_test:
        return 0 if notify(args.notification_test == 'success', 'Notification test; no backup executed', test=True) else 1
    os.umask(0o077)
    success, detail = False, 'Receiver failed; inspect private logs'
    try:
        with (ROOT / 'receiver.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            detail = 'Verified snapshot ' + Receiver().backup()
            success = True
    except Exception as error:
        # Keep raw exception details out of mail (SSH/tool messages may contain paths).
        import traceback
        traceback.print_exc()  # Private job log only; never included in mail.
    try:
        mailed = notify(success, detail)
    except (OSError, subprocess.TimeoutExpired):
        mailed = False
    print(f'Backup verified={success}; mail submitted={mailed}', flush=True)
    return 0 if success and mailed else 1


if __name__ == '__main__':
    raise SystemExit(main())
