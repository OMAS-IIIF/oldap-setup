# Production receiver: encryption and recovery checkpoint

## Accepted setup

The office receiver is `rosenth@131.152.51.209` (`dhlab-da24-002`).
Its dedicated production Jena repository is
`/Users/rosenth/OLDAP_BACKUP/jena/borg`, using Borg 1.4.4 and
`repokey-blake2` encryption. Existing GraphDB and media repositories are separate
and remain unchanged. Use `/opt/homebrew/bin/python3` on this receiver; its
system Python currently requires an Xcode licence interaction.

Runtime credentials are in `~/.config/oldap/jena-backup.json`; the exported key
and recovery record are `jena-backup-key.export` and `jena-backup-recovery.json`
in the same directory. These three files are regular, owner-owned files with
mode 0600. Never include them in Git, code release bundles, logs or emails.
The repository ID is recorded in the adjacent results JSON.

The private recovery record was also retained on the development machine at
`/Users/rosenth/.config/oldap/production-backup-recovery.json`. The owner confirmed
on 2026-11-09 that both the passphrase and exported key were saved in Apple
Passwords. This confirmation records independent custody; the assistant has not
inspected the Apple Passwords entry. Keep the protected files until operational
acceptance is complete.

The office SSH configuration `~/.ssh/oldap_production_backup.conf` uses explicit
identity selection, batch mode, strict host checking and a separate pinned
known-hosts file. Harmless hostname commands succeeded against both production
servers through this configuration.

## Recovery evidence and limits

The encrypted repository contains only `acceptance-fixture-01`: three small
fixture files named `api.tar`, `media.tar` and `manifest.json`. These are synthetic
test contents, not a production snapshot or valid application tar archives.

The recovery test copied this tiny repository into a disposable directory,
removed the repository key from the copy's configuration, and imported the
exported key using the recovery record's passphrase. It used independent Borg
cache/security directories, extracted all three files and compared their exact
contents. `borg check --verify-data` passed on the recovered copy. The original
repository was unchanged; the disposable copy was removed.

The office evidence is `OLDAP_BACKUP/jena/key-recovery-acceptance.json`.
This proves exported-key recovery and fixture integrity. It does not prove a
complete production backup, Linux service restoration, or recovery directly
from the user's Apple Passwords entry. The first real matched Jena pair still
requires pull, Borg creation, extraction/hash verification and operational
acceptance after cutover.

## Approved retention policy

The owner approved these separate layers:

| Layer | Retention |
| --- | --- |
| New production Jena Borg archives | 30 daily, 12 weekly, 24 monthly |
| Completed server transport pairs | Latest 3 confirmed pairs |
| Office Mac transport pairs | Latest 2 confirmed pairs |

Calendar tiers overlap; they are not a guaranteed total of 66 archives.
Apply Borg pruning only to the dedicated production archive family. Synthetic
acceptance archives and existing GraphDB backups are outside this policy.

Transport cleanup must require durable confirmation that the matching pair is
stored and verified in Borg. Keep unconfirmed, partial and failed snapshots;
never infer acceptance from age, a successful transfer alone, or an archive name.
Both source hosts must agree on the pair before deleting either side. Keep the
receipts after transport cleanup so the decision remains auditable.

## Installed receiver workflow

`/Users/rosenth/OLDAP_BACKUP/jena/tools/` now contains the reviewed receiver,
transport helper and existing pair puller. No dependency installation is needed;
use `/opt/homebrew/bin/python3`. The API controller's shared producer publishes
`/srv/storage/oldap-jena-latest.json` atomically only after both archives and the
per-pair ready marker are complete. Its installed playbook passes syntax checks.

`run-production-backup-receiver.py` serializes the entire run and enforces:

1. The protected credential file, expected repository ID and `repokey-blake2`.
2. An automatic snapshot ID and a completion no older than 12 hours, with at
   most five minutes of clock lead. Missing/stale publication is FAILURE, never
   success based on yesterday's backup. Both clocks must be synchronized.
3. The existing fixed-endpoint puller's manifest equality and archive hashes.
4. Borg creation (or existing-archive retry), exact three-file inventory and
   stored manifest equality. Both tar files are streamed back from Borg and
   checked against source byte counts and SHA-256 values. No additional full-size
   extraction directory is required. Any Borg warning/nonzero exit fails the run.
5. A durable local receipt followed by media acknowledgement, then API
   acknowledgement. The source validates its tar before first acknowledgement;
   the API additionally compares its ready marker. Retries reuse the exact
   receipt and verify the stored archive again.
6. Comparison of both source receipt inventories. Before either side is retired,
   both sides of the complete deletion plan are validated. Only automatic-ID
   tar files beyond the latest three matching pairs are eligible. Matching Borg
   archive IDs must still exist. Missing archives are conservatively preserved.
7. Local transport retention keeps the latest two paired confirmations. Unknown
   files, symlinks, digest mismatches or inconsistent receipts stop cleanup.
   Small manifests, directories and receipts remain as audit records; the large
   tar files are removed. An interrupted deletion can safely be retried.
8. Borg pruning is restricted to `production-*`, with the approved calendar
   tiers, followed by compaction. This operates only on the new repository.

Copies without paired confirmation are retained regardless of age. Fixture and
manual archive names are outside automatic retention. Snapshot IDs are ordered
by the producer's UTC timestamp; only the controller generates eligible IDs.
Post-backup verification and cleanup run while application services are online.

SUCCESS/FAILURE emails contain a bounded status and the private log location,
not raw logs or credentials. The owner confirmed both explicit office test mails.
A mail submission failure makes the receiver invocation fail as well.

## Schedule and installation state

The 04:00 receiver plist is staged at
`OLDAP_BACKUP/jena/schedule/org.oldap.jena-backup.plist`, **outside LaunchAgents**,
and is not loaded. It uses Homebrew Python, a private umask and private logs at
`OLDAP_BACKUP/jena/logs/receiver.log`. Local Mac time must be Europe/Zurich for
this schedule. The new 03:15 producer timer remains disabled/inactive.

The production server's original GraphDB backup timer remains active. Inspection
of the office Mac found the legacy `OldapBackup` plist at its expected path but
**no loaded OldapBackup job** in the system/user/gui domains and no user crontab.
This step did not unload it or change its files. The reason is not established;
do not describe the existing office pull as active based solely on the plist.
Resolve its intended schedule state during the cutover decision. Do not leave
both receiver jobs registered for routine execution.

Deploy/update the three Python files together while the new receiver is inactive;
copy the plist only into `jena/schedule` until activation is approved. Install
producer changes through `oldap-jena-backup-controller-install.yml`. Keep
credentials separate. Never initialize an existing repository during deployment.

For a manual first Jena acceptance after cutover, invoke the installed receiver
with Homebrew Python and redirect output into its private log directory. Only
after a real matched production pair and its Borg restore pass should the new
plist be placed in `~/Library/LaunchAgents/` and bootstrapped in the intended
user login domain. The Mac must remain available overnight; a user LaunchAgent
requires the appropriate logged-in user session. Verify schedule registration
and the first actual scheduled completion rather than assuming file placement
is sufficient.

## Acceptance and remaining gate

- 83 production unit/contract tests pass; the ten backup-specific tests were
  repeated after making receipt writes interruption-safe with unique temp files.
- `tests/accept_production_receiver_borg.py`, run with Homebrew Python on the
  office Mac, passed against a **disposable encrypted repository** and five small
  synthetic pairs. Source operations were mapped to temporary directories; no
  real production tar was deleted. Real Borg creation, streamed restore hashes,
  three-server/two-office retention, five daily Borg archives, repeat invocation,
  corrupt-digest rejection and full Borg data checking passed.
- The installed helper's read-only inventory succeeds over actual pinned SSH to
  both servers; both have no acknowledged production Jena transports yet.
- The installed receiver correctly refuses the missing latest publication before
  pulling or creating an archive. No production snapshot was started.
- Plist validation and producer installation/syntax checks pass. Only the shared
  producer task file changed on the API controller; no application restart.

The first **real production Jena pair**, its independent restore/acceptance and
schedule switchover remain open. The fixture does not establish full-size runtime
or replace application restore testing. See
[the controller runbook](production-backup-controller.md) for snapshot execution.
