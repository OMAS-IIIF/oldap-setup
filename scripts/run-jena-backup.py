#!/usr/bin/env python3
"""Run the installed matched-snapshot playbook and send a bounded status email.

The controller uses its dedicated root SSH key, never an interactive sudo password.
Raw Ansible logs remain private on the API VM. A successful process is insufficient:
its completed snapshot marker must also pass identity/path/hash-metadata checks.
Notification failure is a failed job even when the snapshot itself is valid.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import uuid

CONTROLLER = Path(__file__).resolve().parents[1]
LOG_ROOT = Path('/srv/storage/oldap-backup-runs')
SNAPSHOT_ROOT = Path('/srv/storage')


def check_ready(path, snapshot_id):
    """Validate the producer's completion contract; do not reread huge archives."""
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing ordinary completion marker')
    data = json.loads(path.read_text())
    if data.get('snapshot_id') != snapshot_id or data.get('status') != 'offline-compared':
        raise ValueError('Wrong snapshot identity or status')
    for role, prefix in [('api', '/srv/storage'), ('media', '/data')]:
        item = data[role]
        if item.get('path') != f'{prefix}/oldap-jena-snapshot-{snapshot_id}/{role}.tar':
            raise ValueError('Unexpected snapshot path')
        if type(item.get('bytes')) is not int or item['bytes'] <= 0 or not re.fullmatch('[0-9a-f]{64}', item.get('sha256', '')):
            raise ValueError('Missing archive verification metadata')
    if data['media'].get('host') != 'dhlab-iii.dhlab.unibas.ch':
        raise ValueError('Unexpected media endpoint')
    return data


def notify(success, snapshot_id, log, *, test=False):
    """Send no credentials/log excerpts; return False if mail submission fails."""
    status = 'SUCCESS' if success else 'FAILURE'
    subject = ('[TEST - no backup] ' if test else '') + status + ': OLDAP Jena backup'
    body = (f'{status}: matched Jena snapshot {snapshot_id}\n'
            f'Host: {socket.gethostname()}\n'
            f'Finished: {datetime.now(timezone.utc).isoformat()}\n'
            f'Private operator log: {log}\n')
    if test:
        body += 'Notification transport test only. No backup, pause or import was performed.\n'
    elif not success:
        body += ('Inspect the log and maintenance lock before retrying. '
                 'A failed snapshot may retain its lock for operator recovery.\n')
    try:
        result = subprocess.run(['mail', '-r', os.environ['HARVEST_MAIL_FROM'], '-s', subject,
                                 os.environ['HARVEST_MAIL_TO']], input=body, text=True, timeout=60,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except (OSError, KeyError, subprocess.TimeoutExpired):
        return False


def run_backup():
    """Serialize invocations; always report process/publication failures by email.

    The playbook owns the separate cross-job maintenance lock. This local flock
    merely prevents duplicate wrapper invocations. It never releases that lock.
    """
    os.umask(0o077)
    LOG_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    log = LOG_ROOT / (snapshot_id + '.log')
    success = False
    with (LOG_ROOT / 'job.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            notify(False, snapshot_id, 'Another backup invocation holds the controller lock')
            return 1
        with log.open('x') as stream:
            try:
                command = [str(CONTROLLER/'venv/bin/ansible-playbook'), '-i', str(CONTROLLER/'inventory.ini'),
                           str(CONTROLLER/'oldap-jena-production-backup.yml'),
                           '-e', 'snapshot_id='+snapshot_id, '-e', 'production_backup_approved=true']
                result = subprocess.run(command, cwd=CONTROLLER, stdout=stream, stderr=subprocess.STDOUT)
                if result.returncode == 0:
                    check_ready(SNAPSHOT_ROOT/f'oldap-jena-snapshot-{snapshot_id}/ready.json', snapshot_id)
                    success = True
            except (OSError, ValueError, KeyError) as error:
                stream.write('\nController/publication failure: '+type(error).__name__+'\n')
        mailed = notify(success, snapshot_id, log)
    print(('SUCCESS' if success and mailed else 'FAILURE') +
          f': snapshot {snapshot_id}; snapshot verified={success}; mail submitted={mailed}')
    return 0 if success and mailed else 1


def main():
    """Production-only entry point; explicit notification tests never run backups."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notification-test', choices=['success', 'failure'])
    args = parser.parse_args()
    if os.geteuid() != 0 or socket.gethostname().split('.')[0] != 'dhlab-oldap':
        parser.error('Run as root on the approved production API VM')
    if args.notification_test:
        return 0 if notify(args.notification_test == 'success', 'notification-test', 'No backup log', test=True) else 1
    return run_backup()


if __name__ == '__main__':
    raise SystemExit(main())
