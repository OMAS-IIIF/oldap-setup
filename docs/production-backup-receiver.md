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

**This policy is approved but automatic pruning is not installed or activated
at this checkpoint.** No transport copy or historical backup was removed.

## Remaining integration before scheduling

1. Publish a latest-completed production snapshot marker only after successful
   comparison, recovery and hashing; detect missing/stale publications.
2. Wire the office pull to encrypted Borg creation and verification, with
   success/failure mail, retry handling and serialized execution.
3. Implement paired durable acknowledgements and guarded retention; test refusal
   for missing receipts, wrong identities, incomplete pairs and failed Borg runs.
4. Accept the first real production Jena pair and its restore before switching
   schedules. The new producer timer remains disabled, and the old GraphDB jobs
   remain active until the coordinated switch.

See [the controller runbook](production-backup-controller.md) for production
snapshot execution and activation boundaries.
