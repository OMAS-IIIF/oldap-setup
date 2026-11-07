# Studio Borg repository and restore rehearsal

The user approved an **unencrypted home-only** repository, with 7 daily,
4 weekly and 3 monthly archive retention. Production encryption remains a
separate decision; recovery information for an encrypted production repository
will be stored independently in Apple Passwords. This home repository needs no
passphrase or encryption-key export.

## Storage and boundaries

- Receiver: `rosenth@studio.home.org`, Borg `/opt/homebrew/bin/borg` (1.4.5).
- Repository: `/Users/rosenth/OLDAP_BACKUP/borg`, mode 0700.
- Inputs: only accepted `OLDAP_BACKUP/snapshots/ID` directories, never `incoming`.
- Each `home-ID` archive contains `api.tar`, `media.tar`, and `manifest.json`.
- Keep the Linux tar files intact on macOS. Their Linux ownership/ACL metadata
  will be applied only during the separate isolated Linux application restore.
- Restore into a new private `restore-test` directory, never a live service path.
- No LaunchAgent/LaunchDaemon or other schedule is installed. Production and
  office-Mac backups are untouched. Staging/source copies are not automatically
  deleted by the Borg retention policy.

The repository was initialized once with `borg init --encryption=none`. Do not
run initialization over an existing repository or change its encryption mode
as part of routine maintenance.

## Manual archive creation

Use one operator and an accepted, immutable snapshot. Verify its two hashes
against `manifest.json` before creation. Example for the first real snapshot:

```sh
cd /Users/rosenth/OLDAP_BACKUP/snapshots/20261106-studio-rehearsal-01
/opt/homebrew/bin/borg create --stats --compression=zstd \
  /Users/rosenth/OLDAP_BACKUP/borg::home-20261106-studio-rehearsal-01 \
  api.tar media.tar manifest.json
```

Use a new archive name for each new snapshot. Treat any nonzero Borg return code
(including warnings) as requiring review. Never prune after failed creation or
verification. A checkpoint archive is not an accepted complete snapshot.

## Integrity and restore

```sh
/opt/homebrew/bin/borg check --verify-data /Users/rosenth/OLDAP_BACKUP/borg
umask 077
mkdir /Users/rosenth/OLDAP_BACKUP/restore-test/NEW_EMPTY_DIRECTORY
cd /Users/rosenth/OLDAP_BACKUP/restore-test/NEW_EMPTY_DIRECTORY
/opt/homebrew/bin/borg extract \
  /Users/rosenth/OLDAP_BACKUP/borg::home-20261106-studio-rehearsal-01
```

Compare the restored manifest to the separately retained accepted source manifest.
Then check lengths and hashes from inside the new restore directory:

```sh
/opt/homebrew/bin/python3.15 - <<'PY'
import hashlib
import json
from pathlib import Path
manifest = json.loads(Path('manifest.json').read_text())
for role in ('api', 'media'):
    path = Path(role + '.tar')
    expected = manifest[role]
    assert not path.is_symlink() and path.is_file()
    assert path.stat().st_size == expected['bytes'], role + ': size mismatch'
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert actual == expected['sha256'], role + ': checksum mismatch'
print('Both archives match the restored manifest.')
PY
```

This proves recovery of the backup files, not recovery of running OLDAP services.
The latter still requires isolated Linux paths/containers and API/media checks.

## Approved retention, manually invoked

Preview first; only archive names in the dedicated `home-*` family are considered:

```sh
TZ=Europe/Zurich /opt/homebrew/bin/borg prune --dry-run --list \
  --glob-archives 'home-*' --keep-daily=7 --keep-weekly=4 --keep-monthly=3 \
  /Users/rosenth/OLDAP_BACKUP/borg
```

After successful backup/verification and review of the preview, apply the same
command without `--dry-run`. Run `borg compact` after actual pruning to reclaim
unreferenced storage. These are calendar retention tiers, not a guaranteed sum
of fourteen archives. With the initial single archive, it is retained.

Official references: [create](https://borgbackup.readthedocs.io/en/stable/usage/create.html),
[extract](https://borgbackup.readthedocs.io/en/stable/usage/extract.html),
[prune](https://borgbackup.readthedocs.io/en/stable/usage/prune.html).

## Real acceptance — 2026-11-06

Archive `home-20261106-studio-rehearsal-01` was created from the accepted
44,536,965,647-byte input set (two tar files plus manifest). Borg reports
10,574,949,949 deduplicated bytes added, plus repository metadata. Creation
took 123.30 seconds, full `check --verify-data` 45.95 seconds, extraction
45.38 seconds and restored-file verification 19.21 seconds. All returned success.

Restored files are retained at
`/Users/rosenth/OLDAP_BACKUP/restore-test/borg-20261106-studio-rehearsal-01`.
Both exact lengths/SHA-256 values and manifest equality match the separately
retained accepted source. The 7/4/3 retention preview and application both kept
the sole archive; nothing was pruned, so compaction was unnecessary.

Evidence: [home-borg-results.json](home-borg-results.json). The private full
execution report lives under Studio's `OLDAP_BACKUP/reports/`. A copy of this
runbook is installed at `OLDAP_BACKUP/BORG_README.md`. No production host,
service or schedule was changed. The subsequent isolated application restore passed (see `home-restore.md`).
The second measured backup and Borg round-trip also passed; see
[home-backup-timing.md](home-backup-timing.md). Media copy/comparison still dominate
the interruption; no automatic schedule is installed.
