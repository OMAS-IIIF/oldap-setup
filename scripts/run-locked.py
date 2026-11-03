#!/usr/bin/env python3
"""Hold a local-filesystem flock across exec, including the command's children.

Usage: run-locked.py LOCKFILE COMMAND [ARG ...]. Never replace/delete an active
lock file. Used inside containers and by the host backup service on the same inode.
"""
import fcntl
import os
import sys


def main() -> None:
    """Wait for maintenance exclusivity, then replace this process with the job."""
    if len(sys.argv) < 3:
        raise SystemExit("Usage: run-locked.py LOCKFILE COMMAND [ARG ...]")
    descriptor = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR, 0o600)
    print("Waiting for the OLDAP backup/harvesting lock...", flush=True)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    os.set_inheritable(descriptor, True)
    os.execvp(sys.argv[2], sys.argv[2:])


if __name__ == "__main__":
    main()
