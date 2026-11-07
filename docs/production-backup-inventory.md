# Production backup inventory — 2026-11-05

## Scope

Read-only inspection over the user-enabled VPN of `dhlab-oldap.dhlab.unibas.ch`
and `dhlab-iii.dhlab.unibas.ch`. No backup was started, no production file or
service/timer was changed, and no database export was copied locally. The user
identified the office pull host as `131.152.51.209` /
`dhlab-da24-002.dhlab.unibas.ch` (macOS). Its job was subsequently inspected
read-only using SSH as `rosenth`; no backup or Borg operation was started.

## Observed API/GraphDB job

- `/etc/systemd/system/oldap-backup.timer`: daily at 03:15 server time,
  `Persistent=true`.
- Root oneshot `oldap-backup.service`, with credentials supplied by
  `/etc/oldap-backup.env` (contents were not read).
- Effective ExecStart uses `/opt/oldap/compose/run-locked.py` with
  `/srv/storage/oldap-data/job-locks/maintenance.lock`, then
  `/usr/local/bin/oldap-backup.sh`. The installed systemd drop-in confirms the
  existing harvesting/backup exclusion. This is not a global application-write
  or cross-host media snapshot lock.
- Last run: 2026-11-05 03:15:05–03:15:13 CET; systemd result success, exit zero.
- The script exports `/repositories/oldap/statements?infer=false` through the
  GraphDB container, with `Accept: application/x-trig`, then gzip-compresses it.
- It separately invokes oldap-tools `project dump fasnacht`.
- Both outputs live in `/srv/storage/oldap-data/backups`, with timestamped names
  and `graphdb_oldap_latest.trig.gz` / `fasnacht_latest.trig.gz` symlinks.
- Only Fasnacht exports have a server-side age deletion rule (`mtime +60`).
  Observed counts: 169 complete-name/non-symlink GraphDB-prefixed files and 61
  Fasnacht files; one GraphDB filename has an empty timestamp. No claim about
  external retention follows from these counts.
- Script sends a summary email using the host mail transport; no email was sent
  during this inspection.

## Latest archive checks

Both gzip streams were read to EOF on the server (CRC/trailer validation). RDF
syntax and restore were not tested by this inspection.

| Export | Compressed bytes | Uncompressed bytes | SHA-256 of compressed file |
| --- | ---: | ---: | --- |
| GraphDB 2026-11-05 | 2189498 | 9240214 | `7ea001fe9d99fe1b916c1c7b16bed5c64cda53aaa6f4305f9dd86e60692202e2` |
| Fasnacht 2026-11-05 | 1331706 | 6067841 | `2a411954f2fb8c17a559f2dc2e87301324eca79b03c6f803ec87c3cd1fb8cbe9` |

The directory is mode 0755 and the current regular export files are mode 0644.
Assess access requirements when redesigning the complete backup, particularly
for configuration/secrets. No permissions were changed.

## Media host and office pull

No dedicated backup timer or recognizably named backup script was found in the
inspected systemd/cron/local-bin locations on the media host. `/data` contains a
`media-repair-backup` directory; that alone is not evidence of a scheduled media
backup. Neither user has a personal crontab. An external pull of live media or
configuration may exist and is not visible from those server schedules.

### Office pull job (verified)

- User LaunchAgent `~/Library/LaunchAgents/oldap_backup.plist`, label
  `OldapBackup`, runs `/usr/local/bin/oldap_backup.sh` daily at 04:00.
  Loaded job reports last exit zero. This is a user agent, not a system daemon;
  unattended operation across logout/reboot needs an explicit acceptance check.
- `rsync -a` copies timestamped `fasnacht_*` and `graphdb_oldap_*` exports from
  `api.oldap.org:/srv/storage/oldap-data/backups/` to
  `/Users/rosenth/OLDAP_BACKUP/graphdb`. Both latest symlinks are excluded.
  There is no deletion/retention rule for this local RDF collection in the job.
- `rsync -a --delete` mirrors `media.oldap.org:/data/media/fasnacht/` into
  `/Users/rosenth/OLDAP_BACKUP/fasnacht_media_latest/`.
- Borg 1.4.4 creates a versioned, zstd-compressed media archive in
  `/Users/rosenth/OLDAP_BACKUP/fasnacht_media_borg`, then prunes with
  `--keep-daily=30 --keep-weekly=12 --keep-monthly=24`.
- The inspected job covers Fasnacht media only, not all projects, deployment
  configuration, Redis or worker state. It reads live media approximately
  45 minutes after the database export; the two are not a coordinated snapshot.
- Latest log `/tmp/media-backup.log`: 2026-11-05 04:00:01–04:00:41, success.
  Two RDF files transferred. Borg archive `media-2026-11-05_04-00-07` contains
  3472 files, 19.57 GB logical size; reported total deduplicated data 9.39 GB.
  No media bytes changed in this run. Mail command returned zero (delivery not
  independently verified).
- Both Nov 5 RDF copies have exactly the server SHA-256 values listed above.
  This verifies those transfers, not Borg content integrity or restorability.
- Destination is on the Mac's `/System/Volumes/Data` filesystem, with about
  1.6 TiB available at inspection. The script's directory-existence check does
  not establish an independently mounted backup volume.
- The office script has the same `set -e`/explicit-exit error-notification issue
  as the server job. Its GraphDB failure prevents that run's media backup too.

Still required: a documented/tested restore procedure, Borg encryption/key
recovery policy (secrets were not inspected), and unattended scheduling behavior.
A Borg extraction or integrity check was deliberately not run during this
read-only inventory.

## Observed script weaknesses to address in the Jena successor

- `curl` does not use HTTP failure handling: an HTTP error response could be
  compressed successfully. The latest checked files are not HTML error pages,
  but gzip integrity alone is not RDF validation.
- `set -e`/`pipefail` and explicit exits inside the redirected command block can
  terminate the script before its final error-mail branch. A successful timer
  run does not establish that failure notification works.
- Latest pointers are updated separately and there is no shared completion
  manifest for database, media and operational state.
- The inspected script is an RDF export job, not by itself a complete backup of
  API state, Redis coordination, media worker registries and deployment inputs.
  The office pull additionally covers Fasnacht media only; it does not fill
  these operational-state gaps.

These are findings only, not changes to the production GraphDB job.

## Proposed Jena adaptation (not implemented by this inventory)

Preserve the office computer's pull model. The servers should publish immutable,
matched backup artifacts with one snapshot ID and checksums. A central completion
manifest is made available only after both host snapshots are verified. The pull
job downloads completed snapshots and verifies all referenced files before
accepting them; incomplete staging files must not be treated as backups.

Reuse the existing harvesting exclusion and the tested graceful mobile drain /
Jena recovery maintenance controls. Keep the API available until media writers
finish; snapshot database, fulltext, receipts, Redis, application/worker state,
media and configuration consistently. Resume services before the potentially
long external copy. Keep a portable RDF export as an additional convenience,
not as the sole reconstruction source for the whole Jena installation.

Retain rsync transport and Borg deduplication/versioning where practical.
Extend the pull to completed matched Jena/media sets and preserve older good
sets when a transfer fails. Avoid replacing incremental media handling with
unnecessarily large daily full transfers. Final packaging, access protection
and Borg key recovery still require explicit design and restore verification. Test restoration on isolated home storage/containers
using the corresponding pinned versions; home is a rehearsal target, not a new
permanent off-host backup requirement. No production switch is authorized by
this inventory alone.

## Home rehearsal receiver: Mac Studio

`rosenth@studio.home.org` is reachable via SSH. ARM64 Homebrew exists at
`/opt/homebrew/bin/brew`; approximately 2.6 TiB is available. The protected
(mode 0700) `/Users/rosenth/OLDAP_BACKUP` directory contains `incoming`, `borg`
and `restore-test`. No repository has been initialized or schedule installed.

Preparation is blocked by an unaccepted Xcode license (Homebrew refuses even
formula inspection). The owner must review/accept that license. Studio resolves
both `api.home.org` and `media.home.org` to `240.254.254.254`; SSH attempts time
out. Correct home DNS must be available before configuring receiver SSH access.
No license, resolver, host-key trust or authentication configuration was changed.

Observed AC power settings already disable system sleep (`sleep 0`) and turn
off the display after ten minutes (`displaysleep 10`). Automatic restart after
power failure is disabled; consider it when setting up unattended operation.
Borg 1.4 compatibility is the intended target, not yet installed/verified.

Follow-up: Homebrew formula inspection now succeeds and advertises Borg 1.4.5.
Installation fails with `unknown or unsupported macOS version: :dunno` on
macOS 27. `brew update` reports already up-to-date; Borg remains uninstalled.
Direct DNS queries to 192.168.1.1 correctly resolve API to 192.168.1.230 and
media to 192.168.1.223, while macOS dscacheutil still returns 240.254.254.254.
An unprivileged cache flush did not resolve it; owner asked to perform the
privileged DNS cache reset. No resolver configuration was changed.

2026-11-06: After the user changed the Private Relay / Limit IP Address
Tracking setting, Studio system resolution returns the correct API
(192.168.1.230) and media (192.168.1.223) addresses. SSH reaches both servers
and stops at strict host-key verification: host keys are not yet trusted on
Studio. Verify those keys against the established development-machine access
before adding trust; receiver authentication remains untested.

### Studio Borg installation acceptance (2026-11-06)

Homebrew now reports 7.0.12 and recognizes macOS 27.2 natively. The official
`brew install borgbackup` path installed Borg 1.4.5 (formula revision 1) at
`/opt/homebrew/bin/borg`; no OS-version override or alternative tap was used.
The earlier Homebrew 5.0.14 failure is resolved. Installation also installed
libb2, OpenSSL 4, Python 3.15 and xxhash and updated required dependencies.
Homebrew relinked default Python 3 commands to 3.15 and OpenSSL to version 4;
previous overwritten Python links were backed up by Homebrew under its cache.
No unrelated package upgrade command was run.

A synthetic smoke test passed archive creation (zstd), `borg check --verify-data`
and extraction. Exact file contents, Unicode text, an empty file, binary data,
a symlink and mode 0640 survived restoration. Evidence and test data remain on
Studio at `/Users/rosenth/OLDAP_BACKUP/restore-test/borg-smoke-_fc1p1hp/result.json`.
This disposable synthetic repository is unencrypted; it does not determine the
encryption policy for actual backups. No real data, production repositories,
scheduled jobs or home services were touched. Full snapshot/pull/restore
acceptance and authenticated Studio-to-server SSH access remain pending.

Official installation reference:
https://borgbackup.readthedocs.io/en/stable/installation.html

### Studio receiver SSH access (2026-11-06)

A dedicated unattended Ed25519 key lives only on Studio at
`/Users/rosenth/.ssh/oldap_home_backup` (mode 0600). Its public fingerprint is
`SHA256:rj/EuAcdyyuafL6LVumS+DJe5vmOdC3ROA56wK8sAog`. Its public key was
appended to `rosenth` authorized_keys on API/media home hosts using `restrict`
(no forwarding, PTY or user rc). This does not force read-only commands: normal
noninteractive commands retain the account's existing filesystem permissions.
A forced read-only command can be designed once published snapshot paths and
transfer commands are finalized. No production host was changed.

Server Ed25519 keys were read through the development machine's existing
strictly verified SSH connections and installed in Studio's separate
`~/.ssh/oldap_home_known_hosts`. Dedicated `~/.ssh/oldap_home_backup.conf` selects
this identity, strict host-key checking and BatchMode without modifying the
existing SSH configuration. Both commands successfully return the expected
hostname/account; rsync exists on both endpoints:

```sh
ssh -F /Users/rosenth/.ssh/oldap_home_backup.conf api.home.org hostname
ssh -F /Users/rosenth/.ssh/oldap_home_backup.conf media.home.org hostname
```

The future pull job must explicitly use this configuration (rsync `-e` option).
Existing keys were preserved; no private key left Studio. No timer, backup job
or service restart was triggered. Snapshot file access and transfer acceptance
remain separate from this SSH connectivity check.

## Fresh-source migration preflight — 2026-11-07

Separate protected production become credentials were verified on both VMs.
Inspection remains read-only: no service, timer, image or configuration changed.
Ansible reports its command/script probes as changed; these probes only inspect
state. Do not mistake that status for an application deployment.

The running source has eight API-host containers and six media-host containers.
Source application references include oldap-api v0.2.37, mediahelper/workers
v0.2.17, Fasnacht v0.1.49, oldap-app v0.2.7, SALSAH v0.0.2, GraphDB 11.3.0
and SIPI-2 1.0.0. Actual IDs, image IDs, start times and bind mounts are retained
in private preflight evidence; mutable tags alone are not rollback identities.

### Additional source snapshot requirements

- Include the separate `compose-archive-writer-1` Redis coordinator, its
  `/srv/storage/oldap-data/archive-writer` state and `/opt/oldap/.env` inputs.
  The old home freeze tar includes `/opt/oldap/compose` but omits those separate
  credential inputs. Preserve them privately; never put them in evidence JSON.
- Preserve ordinary Redis `/opt/oldap/compose/redis-data`, GraphDB storage,
  API operational state and the deployed Compose/proxy inputs together.
- Media host paths are `/data/media`, `/data/oldap-ingest`,
  `/data/oldap-import-records`, `/data/oldap-exports`, and
  `/data/oldap-mobile-uploads`, plus `/opt/oldap-mediaserver` configuration and
  Caddy state. Container paths differ: mobile registry is mounted at
  `/data/mobile-uploads` inside the worker. SIPI's named cache is disposable.
- The deployed mobile worker lacks the `stop` parameter in `run_forever`.
  The home SIGTERM drain preflight therefore correctly rejects this image.
  All eight `mobile_*` tables in the real source registry were empty at
  inspection. This permits considering the established legacy SIGINT path,
  but **only after rechecking emptiness with ingress/helper stopped**. This
  observation does not guarantee that the registry will still be empty later.
- The 03:15 backup timer and weekly harvesting share a maintenance lock. That
  lock does not stop API/media writes. Exclude scheduled jobs and drain all
  writers before taking the matched snapshot. Preserve coordinator state and
  confirm no active operations before stopping the databases.

### Portable RDF preflight (not the matched snapshot)

A fresh read-only whole-repository export used `application/x-trigstar` with
`infer=false`: 8,895,109 bytes, SHA-256
`936cc697fce0ad74bbbbd5078826db771188b8b8bfc56ab4f7106e0b4f8ab088`.
The existing converter preserved 59,066 ordinary quads and converted 3,139
membership annotations. Four known orphaned memberships remain inactive;
no asserted memberships were added. Round-trip verification passed. Converted
SHA-256: `e09777cd1147ab7fd4ff8e1760d634a326d9f1e33d4998d1538f1d7a872d6684`.
The accepted packaged importer opened a new local dataset, verified persisted
RDF equivalence and recorded 23 graphs. Domain patches, fulltext setup and
API comparisons have not yet run against this fresh dataset.

Private working evidence is `/tmp/oldap-cutover-20261107`; it is temporary,
not a durable backup. This live export is not synchronized with media. Gate 3
remains open until a coordinated source set, isolated target acceptance and
rollback to matched source data/configuration/images have all passed.

### Execution boundary

Do not rerun the home first-cutover playbooks against already-active Jena or
remove their target-opened guard. Prepare a separate rehearsal root, preserve
current home test data, and plan storage before copying full media archives.
The production write pause is a distinct maintenance action: prepare and review
its concrete drain/snapshot/recovery commands before requesting approval. This
preflight has not paused production and does not authorize a production cutover.
