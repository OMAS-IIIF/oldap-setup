#!/usr/bin/env python3
"""Run both deployed harvesters sequentially and mail concise per-source results.

Logs stay on the VM with mode 0600; no raw log, credentials or source metadata are
mailed. Missing final summaries and nonzero exits are failures, never zero imports.
An independent job or mail failure does not prevent the second source from running.
"""
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from datetime import datetime, timezone

COMPOSE = Path('/opt/oldap/compose')
LOG_ROOT = Path('/srv/storage/oldap-data/oldap-harvesters/scheduled-runs')


def read_summary(path: Path, source: str) -> dict | None:
    """Find the CLI's final validated source summary among ordinary console lines."""
    found = None
    with path.open(errors='replace') as stream:
        for line in stream:
            try:
                candidate = json.loads(line)
            except ValueError:
                continue
            if (isinstance(candidate, dict) and candidate.get('source') == source
                    and all(type(candidate.get(key)) is int and candidate[key] >= 0
                            for key in ('created', 'updated', 'skipped', 'seen'))):
                found = candidate
    return found


def describe_result(source: str, code: int, summary: dict | None, log: Path) -> tuple[str, str]:
    """Describe reliable counters; never claim a partial failed run added nothing."""
    success = code == 0 and summary is not None
    status = 'SUCCESS' if success else 'ERROR'
    if success:
        result = 'No new entries added.' if summary['created'] == 0 else f"{summary['created']} new entries added."
    else:
        result = f'Harvesting failed (exit {code}). Partial writes may have occurred.'
    lines = [source.capitalize(), result]
    if summary:
        lines.append(f"Created: {summary['created']}; updated: {summary['updated']}; skipped: {summary['skipped']}; seen: {summary['seen']}.")
        # These are aggregate counters, not catalog identifiers or log excerpts.
        media = summary.get('media')
        if isinstance(media, dict):
            counters = {key: value for key, value in media.items() if type(value) is int}
            lines.append('PDF/OCR counters: ' + json.dumps(counters, sort_keys=True))
    elif code == 0:
        lines.append('The CLI did not emit a valid final summary; please inspect the log.')
    lines.extend([f'Host: {socket.gethostname()}', f'Finished: {datetime.now(timezone.utc).isoformat()}', f'VM log: {log}'])
    return f'{status}: OLDAP {source} harvesting', '\n'.join(lines) + '\n'


def main() -> int:
    """Run one weekly cycle using installed configuration and the host mail command."""
    os.umask(0o077)
    recipient = os.environ['HARVEST_MAIL_TO']
    sender = os.environ['HARVEST_MAIL_FROM']
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    with (LOG_ROOT / 'weekly.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('A weekly harvesting cycle is already running.', flush=True)
            return 75
        run = LOG_ROOT / (datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ') + f'-{os.getpid()}')
        run.mkdir()
        failed = False
        for source in ('europeana', 'swisscovery'):
            log = run / f'{source}.log'
            print(f'Starting {source}; log: {log}', flush=True)
            with log.open('w') as output:
                try:
                    code = subprocess.run([str(COMPOSE / 'run-harvester.sh'), source], stdout=output, stderr=subprocess.STDOUT).returncode
                except OSError as error:
                    output.write(f'Launcher unavailable: {type(error).__name__}\n')
                    code = 127
            summary = read_summary(log, source)
            failed |= code != 0 or summary is None
            subject, body = describe_result(source, code, summary, log)
            print(subject, flush=True)
            try:
                mail = subprocess.run(['mail', '-r', sender, '-s', subject, recipient], input=body, text=True, timeout=60)
                failed |= mail.returncode != 0
                if mail.returncode:
                    print(f'Mail delivery command failed for {source}: {mail.returncode}', file=sys.stderr)
            except (OSError, subprocess.TimeoutExpired) as error:
                failed = True
                print(f'Mail delivery command failed for {source}: {type(error).__name__}', file=sys.stderr)
        return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
