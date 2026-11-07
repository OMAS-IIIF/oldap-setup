# Home snapshot publication and Studio pull

This is a manual, single-operator rehearsal, not a production backup schedule.
Stop external/direct writers and exclude concurrent deployments or harvests.
The home playbook fixes the home hosts and paths and refuses unknown
containers or an existing snapshot ID. By default it drains writers, archives
both stopped hosts, compares archives with stopped sources and recovers services.
Hashing and publication follow successful recovery. The optional
`home_media_precopy=true` experiment is described in
[the media staging workflow](home-media-staging.md); it is disabled by default
because the full-size home measurement found a longer interruption.
Recovery runs even after snapshot failure, and failed comparison, recovery or
hashing prevents publication.

## Publish

```sh
ansible-playbook -i inventory.ini oldap-jena-home-backup.yml \
  -e snapshot_id=UNIQUE_IDENTIFIER -e home_snapshot_publish=true \
  -e @/absolute/private/home-become.json
```

Publication is opt-in. Only after a successful backup and service recovery does
it grant `rosenth` private access to the two archives (0700 directories, 0600
files), then atomically write `ready.json` on API. Archives are immutable by
operator convention; there is no filesystem write-protection guarantee. The
receiver rechecks the ready marker and all archive digests before acceptance.
The manifest without `ready.json` remains a local recovery record, not a pull
publication. Partial runs are retained for diagnosis; IDs must never be reused
for a new producer run.

## Pull on Studio

The deployed copy of `scripts/pull-home-snapshot.py` is
`/Users/rosenth/.local/lib/oldap/pull-home-snapshot.py`. Use:

```sh
/opt/homebrew/bin/python3.15 /Users/rosenth/.local/lib/oldap/pull-home-snapshot.py UNIQUE_IDENTIFIER
```

The dedicated SSH configuration is `~/.ssh/oldap_home_backup.conf`. No sudo or
live database access is required by the receiver. Only exact home snapshot
paths/hosts are accepted from the manifest. A nonblocking receiver lock prevents
overlapping pull processes. rsync writes to `OLDAP_BACKUP/incoming/ID`; interrupted
copies remain there and the same command retries them. Complete archives are
reused only after SHA-256 verification. Incomplete or corrupted archives are
retransmitted whole, avoiding expensive delta matching against large partial tar
files. Transport compression is intentionally omitted for this baseline: the
first compressed/delta retry was CPU-bound and did not improve the rehearsal. Every tar must match its advertised length
and SHA-256 before the directory is renamed to `OLDAP_BACKUP/snapshots/ID`.
Consumers must ignore `incoming/`. Accepted snapshots are never overwritten.

These archives contain configuration/secrets and must remain private. SSH
protects transport; this stage does not add at-rest encryption or a Borg archive.
The user has since approved unencrypted home Borg storage and 7/4/3 retention;
see [the Borg runbook](home-borg.md). Production encryption remains separate.
No pruning or extraction occurs in this script. Preserve original Linux tar
metadata for restoration on Linux, rather than extracting system files onto
macOS. This first version transfers full tar archives; production incremental
media handling remains a separate optimization.

## Verification and remaining acceptance

`tests/test_home_snapshot_pull.py` exercises interruption/retry, checksum failure,
manifest mutation, path/identity rejection and completed-snapshot overwrite
refusal. Existing recovery/mobile tests cover service ordering and failures.
The isolated application restore has now passed; see [the restore runbook](home-restore.md)
for evidence and remaining limits. This does not replace production recovery acceptance.

## First real rehearsal: 2026-11-06

Snapshot `20261106-studio-rehearsal-01` is accepted on Studio under
`/Users/rosenth/OLDAP_BACKUP/snapshots/20261106-studio-rehearsal-01`.
API archive: 23,383,111,680 bytes; media archive: 21,153,853,440 bytes. Both
match the source manifest SHA-256 values. The producer playbook took 1232.4
seconds (20.5 minutes, including preflight/recovery/publication; exact ingress
downtime was not independently recorded). All 26 checks before and after pass;
30 story results retain the same normalized digest, fulltext returns ten
matches, and a signed image is delivered successfully.

Two actual transfers were deliberately interrupted. Neither was accepted. The
compressed delta retry was CPU-bound; a full-length partial file did not yet
match the source hash. Final code uses whole-file retransmission for invalid
partials and reuses only verified complete archives. The final successful pull
took 225.63 seconds, including local verification, while services stayed online.
This does not measure compression alone in a controlled comparison.

Evidence: `home-snapshot-pull-results.json`. Five receiver failure/retry tests
and five existing recovery/mobile tests pass; Ansible syntax and diff checks
pass. At that checkpoint application restoration and Borg policy were still pending.
Both were subsequently exercised as documented in the Borg and restore runbooks;
no automatic schedule has been installed.

Archive hashing has now moved after recovery. Before a routine production
workflow, investigate pre-copy/final-sync or storage snapshots for media so full
copying/comparison does not keep writers offline.
Keep consistency guarantees explicit; do not replace the coordinated snapshot
with an uncoordinated live media copy. Capacity preflight and automatic exclusion
of concurrent maintenance/harvesting also need production hardening.

## Post-recovery hashing and image provenance

The producer captures actual container image identities on both hosts while the
stack is stopped and deployments are excluded. Manifest `images.api` and
`images.media` map container names to configured references, immutable image IDs,
available repository digests and OS/architecture/variant. Only this allowlisted
metadata is retained; raw Docker inspection output can contain secrets and is
never written into the manifest. Mounted Jena releases/configuration remain
part of the tar archive, not part of the Java base-image identity.

The receiver preserves these additional fields unchanged, while remaining
compatible with older manifests. A local image ID is not a registry pull URL:
use a matching repository digest and platform for recovery. Empty `repo_digests`
means that the image needs a separate export/build retention strategy. Recording
a digest does not guarantee that the registry will retain the image forever.

The first optimization keeps copying and source comparison offline, then
recovers services **before** hashing the two completed archives and publishing
the manifest. It does not weaken source consistency or make copying concurrent
with writers. Hashing still uses disk bandwidth while services are online.
Tests execute the actual Ansible block/always topology with injected comparison,
recovery and hashing failures; all must suppress publication. Image metadata was
also read successfully from eight live home containers without stopping them.
A subsequent full-size run passed: about 11m 25s observed interruption, with
187 seconds of hashing outside the offline phase. See [measured acceptance](home-backup-timing.md)
for methodology, limitations and the completed Studio/Borg round-trip.

The measured hashing-only flow remains the default. The subsequent staged media
experiment showed worse outage on home and is retained only for explicit selection.
