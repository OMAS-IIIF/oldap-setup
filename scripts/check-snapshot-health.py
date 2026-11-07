#!/usr/bin/env python3
"""Check one accepted snapshot without modifying it or sending notifications.

Exit 0 means the requested checks passed; exit 2 requires operator attention.
The default checks metadata, age, archive sizes and available space. Use
--verify to additionally stream both archive SHA-256 hashes. This does not
verify Borg, restore an application, or establish that the latest job succeeded.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil


def check_snapshot(
    directory, *, max_age_hours, min_free_percent, verify=False, now=None
):
    """Return a credential-free report for a receiver snapshot directory.

    Missing or invalid completion timestamps fail closed, including legacy
    manifests: filesystem mtimes are not evidence of backup freshness.
    Files are inspected in place; no remote paths from manifests are followed.
    """
    if max_age_hours <= 0 or not 0 <= min_free_percent < 100:
        raise ValueError("Invalid age or capacity threshold")
    now = now or datetime.now(timezone.utc)
    issues = []
    report = {
        "status": "attention",
        "checks": "sha256" if verify else "metadata",
        "issues": issues,
    }
    try:
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Snapshot directory missing or symlinked")
        manifest = directory / "manifest.json"
        if manifest.is_symlink() or not manifest.is_file():
            raise ValueError("Completion manifest missing or symlinked")
        data = json.loads(manifest.read_text())
        if not isinstance(data, dict):
            raise ValueError("Invalid manifest object")
        if (
            data.get("snapshot_id") != directory.name
            or data.get("status") != "offline-compared"
        ):
            raise ValueError("Snapshot identity/status mismatch")
        try:
            timestamp = data.get("completed_at")
            if not isinstance(timestamp, str):
                raise ValueError("Missing timestamp")
            completed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if completed.tzinfo is None:
                raise ValueError("Missing timezone")
            age = (now - completed).total_seconds() / 3600
            report["age_hours"] = round(age, 3)
            if age < 0 or age > max_age_hours:
                issues.append(
                    "Snapshot timestamp is in the future or exceeds maximum age"
                )
        except (ValueError, TypeError, OverflowError):
            # Legacy freshness stays unverified, but still inspect file integrity.
            issues.append("Completion timestamp missing/invalid; freshness unverified")
        report["archives"] = {}
        for role in ("api", "media"):
            entry = data.get(role)
            if not isinstance(entry, dict):
                raise ValueError("Missing archive metadata")
            size, digest = entry.get("bytes"), entry.get("sha256")
            if (
                type(size) is not int
                or size <= 0
                or not isinstance(digest, str)
                or not re.fullmatch("[0-9a-f]{64}", digest)
            ):
                raise ValueError("Invalid archive size/hash metadata")
            archive = directory / f"{role}.tar"
            if (
                archive.is_symlink()
                or not archive.is_file()
                or archive.stat().st_size != size
            ):
                issues.append(f"{role} archive missing or size/type mismatch")
                continue
            report["archives"][role] = "size-matched"
            if verify:
                checksum = hashlib.sha256()
                with archive.open("rb") as stream:
                    for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                        checksum.update(block)
                if checksum.hexdigest() != digest:
                    report["archives"][role] = "checksum-mismatch"
                    issues.append(f"{role} archive checksum mismatch")
                else:
                    report["archives"][role] = "sha256-verified"
        usage = shutil.disk_usage(directory)
        free_percent = usage.free / usage.total * 100
        report["free_percent"] = round(free_percent, 2)
        if free_percent < min_free_percent:
            issues.append("Receiver filesystem below minimum free capacity")
    except (OSError, ValueError, TypeError, OverflowError):
        # Never emit raw exceptions: manifests and paths may contain private data.
        issues.append(
            "Snapshot metadata/files unavailable or invalid; check completion timestamp and archives"
        )
    report["status"] = "passed" if not issues else "attention"
    return report


def main():
    """Run an explicit operator check; thresholds are never silently assumed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--max-age-hours", required=True, type=float)
    parser.add_argument("--min-free-percent", required=True, type=float)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if (
        not 0 < args.max_age_hours < float("inf")
        or not 0 <= args.min_free_percent < 100
    ):
        parser.error("Age must be positive and finite; free percentage must be 0..99")
    report = check_snapshot(
        args.directory,
        max_age_hours=args.max_age_hours,
        min_free_percent=args.min_free_percent,
        verify=args.verify,
    )
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
