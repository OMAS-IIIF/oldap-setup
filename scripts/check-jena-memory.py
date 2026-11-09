"""Sample Linux cgroup v2 Jena memory during a separately started workload.

Run on the Docker host. This read-only probe records anonymous and file memory,
OOM counters, swap and host headroom without inspecting container credentials.
It does not infer a leak from resident database mappings or file cache.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path


def counters(text):
    """Parse a kernel two-column counter file into integer values."""
    return {key: int(value) for key, value in (line.split() for line in text.splitlines())}


def sample(container):
    """Read one memory snapshot; fail if the selected container disappears."""
    paths = ['memory.current', 'memory.max', 'memory.swap.current', 'memory.swap.max',
             'memory.events', 'memory.stat']
    # The delimiter is fixed code, never derived from caller-provided shell input.
    command = '; printf "\\n---\\n"; '.join('cat /sys/fs/cgroup/' + path for path in paths)
    sections = subprocess.check_output(['docker', 'exec', container, 'sh', '-c', command], text=True).split('\n---\n')
    events, stats = counters(sections[4]), counters(sections[5])
    info = {line.split(':')[0]: int(line.split()[1]) * 1024
            for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:', 'MemAvailable:'))}
    return {'unix_seconds': time.time(), 'current': int(sections[0]),
            'limit': sections[1].strip(), 'swap_current': int(sections[2]),
            'swap_limit': sections[3].strip(), 'events': events,
            'anon': stats['anon'], 'file': stats['file'], 'file_mapped': stats['file_mapped'],
            'host_available': info['MemAvailable']}


def main():
    """Write bounded sampling evidence; nonzero exit indicates new OOM events."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container', default='compose-oldap-jena-1')
    parser.add_argument('--seconds', type=int, default=180)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('--seconds must be between 1 and 3600')
    def identity():
        # Read only lifecycle metadata, never the environment/signing secrets.
        return subprocess.check_output(
            ['docker', 'inspect', '--format',
             '{{.Id}} {{.State.StartedAt}} {{.RestartCount}} {{.State.Running}}', args.container],
            text=True).strip()

    original_identity = identity()
    samples = []
    deadline = time.monotonic() + args.seconds
    while True:
        samples.append(sample(args.container))
        if time.monotonic() >= deadline:
            break
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    delta = {key: samples[-1]['events'][key] - samples[0]['events'][key] for key in samples[0]['events']}
    unchanged = identity() == original_identity
    report = {'container': args.container, 'lifecycle_unchanged': unchanged, 'samples': samples,
              'peak_bytes': max(row['current'] for row in samples),
              'peak_anon_bytes': max(row['anon'] for row in samples),
              'minimum_host_available_bytes': min(row['host_available'] for row in samples),
              'event_deltas': delta}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    return 1 if not unchanged or delta.get('oom', 0) or delta.get('oom_kill', 0) else 0


if __name__ == '__main__':
    raise SystemExit(main())
