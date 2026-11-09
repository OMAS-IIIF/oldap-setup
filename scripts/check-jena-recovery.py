"""Home-only disruptive acceptance, called after the playbook quiesces writers.

Exercise graceful restart and a host-side SIGKILL of the exact Jena PID. Docker,
then the installed timer, must recover without a manual reconciliation command.
Never use against a live production stack. The wrapper restores access on error.
"""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def run(args):
    return subprocess.check_output(args, text=True, timeout=120)


def main():
    """Write evidence to stdout; fail unless both faults recover and remain stable."""
    spec = importlib.util.spec_from_file_location('recovery', '/usr/local/lib/oldap/jena-recovery.py')
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    assert run(['docker', 'inspect', '--format', '{{.State.Running}}', 'caddy']).strip() == 'false'
    assert run(['systemctl', 'is-active', 'oldap-jena-recovery.timer']).strip() == 'active'
    assert not (recovery.STATE_DIR / 'maintenance').exists()
    report = []
    for fault in ('restart', 'process-kill'):
        before = {name: recovery.inspect(name) for name in [recovery.OWNER, *dict(recovery.CLIENTS).values()]}
        started = time.monotonic()
        if fault == 'restart':
            run(['docker', 'restart', '--timeout', '90', recovery.OWNER])
        else:
            # A Docker CLI kill is an operator stop and suppresses automatic restart.
            # Killing only this verified host PID exercises the runtime crash path.
            pid = int(run(['docker', 'inspect', '--format', '{{.State.Pid}}', recovery.OWNER]))
            assert pid > 1 and recovery.inspect(recovery.OWNER)['service'] == 'oldap-jena'
            os.kill(pid, signal.SIGKILL)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                after = {name: recovery.inspect(name) for name in before}
                owner = after[recovery.OWNER]
                if (owner['started'] != before[recovery.OWNER]['started'] and owner['namespace']
                        and all(c['namespace'] == owner['namespace'] for c in after.values())
                        and recovery.ready()):
                    run(['docker', 'exec', 'oldap-api', 'python', '-c',
                         'import urllib.request; r=urllib.request.urlopen(urllib.request.Request('
                         '"http://127.0.0.1:8000/admin/auth/unknown",data=b"{}",'
                         'headers={"Content-Type":"application/json"}),timeout=10); assert r.status==200'])
                    break
            except (RuntimeError, OSError, subprocess.SubprocessError):
                pass
            time.sleep(2)
        else:
            raise RuntimeError('Automatic recovery timed out after ' + fault)
        seconds = round(time.monotonic() - started, 3)
        # A second timer interval must not recreate already healthy clients.
        time.sleep(15)
        stable = {name: recovery.inspect(name) for name in before}
        assert stable == after, 'Healthy clients were recreated again'
        report.append({'fault': fault, 'recovery_seconds': seconds, 'before': before,
                       'after': after, 'stable_next_interval': True})
    print(json.dumps({'status': 'passed', 'faults': report}, indent=2))


if __name__ == '__main__':
    main()
