#!/usr/bin/env python3
"""Reconnect persistent Jena clients after an unexpected namespace replacement.

Run as a root-owned systemd oneshot on the Docker host. Compare actual Linux
network namespace inodes, not merely container IDs (a restart can retain an ID).
Never restart Jena or replay application/batch work. A shared lock and persistent
maintenance marker exclude coordinated deployments. Failed repairs are bounded
and journalled without Docker output, which may contain deployment secrets.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

STATE_DIR = Path('/var/lib/oldap-jena-recovery')
COMPOSE_DIR = Path('/opt/oldap/compose')
OWNER = 'compose-oldap-jena-1'
CLIENTS = [('oldap-jena-identity', 'compose-oldap-jena-identity-1'), ('oldap-api', 'oldap-api')]


def command(args, *, cwd=None, timeout=15):
    """Capture Docker output privately; errors expose only their command category."""
    try:
        return subprocess.run(args, cwd=cwd, timeout=timeout, check=True,
                              capture_output=True, text=True).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise RuntimeError('Docker command failed or timed out: ' + args[1]) from None


def inspect(name):
    """Read lifecycle and actual namespace; missing/stopped containers have no netns."""
    # Do not read or print Config.Env. PID and label validation prevent selecting
    # an unrelated container that happens to reuse one of the expected names.
    try:
        text = command(['docker', 'inspect', '--format',
                        '{{json .State}}\n{{.Id}}\n{{index .Config.Labels "com.docker.compose.service"}}', name])
    except RuntimeError:
        # Compose may have removed the old container before creation failed.
        # Distinguish that from a Docker daemon failure, without logging stderr.
        found = command(['docker', 'ps', '-a', '--filter', 'name=^/' + name + '$', '--format', '{{.ID}}'])
        if found.strip():
            raise
        expected = {OWNER: 'oldap-jena', **{n: s for s, n in CLIENTS}}
        return {'id': '', 'service': expected[name], 'namespace': None,
                'started': '', 'running': False}
    lines = text.splitlines()
    state = json.loads(lines[0])
    namespace = None
    if state['Running'] and state['Pid']:
        namespace = os.readlink(f"/proc/{state['Pid']}/ns/net")
    return {'id': lines[1], 'service': lines[2], 'namespace': namespace,
            'started': state['StartedAt'], 'running': state['Running']}


def ready():
    """Require the backend's own ready response before touching consumers."""
    try:
        text = command(['docker', 'exec', OWNER, 'bash', '-c',
                        'exec 3<>/dev/tcp/127.0.0.1/3031; '
                        'printf "GET /health HTTP/1.0\\r\\n\\r\\n" >&3; cat <&3'], timeout=5)
        return '200' in text.splitlines()[0] and 'ready' in text
    except (RuntimeError, IndexError):
        return False


def save(path, state):
    """Atomically persist repair ownership before a potentially interrupted restart."""
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def reconcile(directory=STATE_DIR, compose=COMPOSE_DIR):
    """Perform at most one ordered repair pass under the caller's maintenance lock.

    Stopped clients are respected unless an earlier repair explicitly owns them.
    Three attempts per client/backend generation, spaced by at least 30 seconds,
    prevent recreation loops. Exhaustion remains visible until operator reset or
    a new backend generation; unrelated batch containers are never recreated.
    """
    if (directory / 'maintenance').exists():
        return 'maintenance'
    owner = inspect(OWNER)
    if owner['service'] != 'oldap-jena':
        raise RuntimeError('Unexpected backend container label')
    if not owner['namespace'] or not ready():
        return 'backend-not-ready'
    generation = [owner['id'], owner['started'], owner['namespace']]
    path = directory / 'state.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    if state.get('generation') != generation:
        # Retain ownership of interrupted repairs across another backend restart,
        # while giving the new generation its own retry budget.
        pending = {name: {'attempts': 0, 'last_attempt': 0, 'complete': False}
                   for name, repair in state.get('repairs', {}).items()
                   if not repair.get('complete')}
        state = {'generation': generation, 'repairs': pending}
    changed = False
    for service, name in CLIENTS:
        client = inspect(name)
        if client['service'] != service:
            raise RuntimeError('Unexpected client label: ' + service)
        repair = state['repairs'].get(service)
        if client['namespace'] == owner['namespace'] and not repair:
            continue
        if not client['running'] and (not repair or repair.get('complete')):
            return 'client-intentionally-stopped: ' + service
        if repair and repair.get('complete'):
            if client['namespace'] == owner['namespace']:
                continue
            # Another unexpected change within this generation gets its own
            # bounded repair, rather than silently treating old success as current.
            repair = None
        if repair and repair['attempts'] >= 3:
            raise RuntimeError('Repair exhausted; operator intervention required: ' + service)
        if repair and time.time() - repair['last_attempt'] < 30:
            return 'retry-backoff'
        # Recheck the owner immediately before mutation. Never accept a repair
        # against a namespace that changed during readiness/inspection.
        current = inspect(OWNER)
        if [current['id'], current['started'], current['namespace']] != generation:
            return 'backend-changed'
        repair = {'attempts': (repair or {}).get('attempts', 0) + 1,
                  'last_attempt': time.time(), 'complete': False}
        state['repairs'][service] = repair
        save(path, state)
        print('Reconnecting ' + service, flush=True)
        command(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate',
                 '--wait', '--wait-timeout', '30', service], cwd=compose, timeout=60)
        current = inspect(OWNER)
        updated = inspect(name)
        if ([current['id'], current['started'], current['namespace']] != generation
                or updated['namespace'] != owner['namespace']):
            raise RuntimeError('Namespace changed during repair; retry next pass')
        if service == 'oldap-api':
            # An anonymous login is a read-only end-to-end DB/identity check.
            command(['docker', 'exec', name, 'python', '-c',
                     'import urllib.request; '
                     'r=urllib.request.urlopen(urllib.request.Request('
                     '"http://127.0.0.1:8000/admin/auth/unknown",data=b"{}",'
                     'headers={"Content-Type":"application/json"}),timeout=10); '
                     'assert r.status==200; r.close()'], timeout=15)
        repair['complete'] = True
        save(path, state)
        changed = True
    if changed:
        print('Jena namespace recovery complete', flush=True)
    return 'recovered' if changed else 'healthy'


def main():
    """Serialize checks and maintenance controls; return nonzero on failed repair."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'pause', 'resume', 'reset'], nargs='?', default='check')
    args = parser.parse_args()
    STATE_DIR.mkdir(mode=0o700, exist_ok=True)
    with (STATE_DIR / 'lock').open('a') as lock:
        try:
            flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if args.action == 'check' else 0)
            fcntl.flock(lock, flags)
        except BlockingIOError:
            return 0
        if args.action == 'pause':
            (STATE_DIR / 'maintenance').touch(mode=0o600)
        elif args.action == 'resume':
            (STATE_DIR / 'maintenance').unlink(missing_ok=True)
        elif args.action == 'reset':
            (STATE_DIR / 'state.json').unlink(missing_ok=True)
        else:
            try:
                reconcile()
            except (RuntimeError, OSError, ValueError) as error:
                print('Jena recovery failed: ' + str(error), flush=True)
                return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
