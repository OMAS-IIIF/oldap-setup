#!/usr/bin/env python3
"""Hold the existing backup/harvester flock until systemd stops this process.

The ready file is created only after exclusive acquisition. This avoids treating
an active systemd process that has not acquired its lock as maintenance ownership.
A fresh checkpoint directory is required; never remove the shared lock inode.
"""
import fcntl
import json
import os
from pathlib import Path
import signal
import sys


def hold(lock, ready):
    """Acquire without waiting, publish readiness, then wait for SIGTERM/SIGINT."""
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    def finish(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, finish)
    signal.signal(signal.SIGINT, finish)
    try:
        with ready.open('x') as stream:
            json.dump({'pid':os.getpid(), 'lock':str(lock)}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        ready.chmod(0o600)
        while True:
            signal.pause()
    finally:
        ready.unlink(missing_ok=True)
        os.close(descriptor)


if __name__ == '__main__':
    hold(Path(sys.argv[1]), Path(sys.argv[2]))
