# Jena release and operating gate — 2026-11-07

Gate 4 is in preparation, not a production release approval. Gate 3 still needs
its coordinated source snapshot and real rollback exercise. The local revision
inventory is `jena-release-inventory.json`; all eight application repositories
are clean on `migration/jena`, while setup contains the backup/recovery work.
The inventory records source revisions, not proof that deployed images were
built from every current revision. No merge, push or image publication occurred.

## Release identity and retention

Before freezing the release, capture live identities again with
`scripts/snapshot-images.py` on both Docker hosts (explicit container names).
Keep image IDs, repository digests and platform fields. Compare them with the
accepted snapshot and home write-test evidence. Include the non-containerized
Jena service bundle and its build manifest/hash: pinning the Java runtime image
alone does not identify the deployed Jena code/configuration.

Keep the tested target release and the matched GraphDB rollback release. Export
unique image IDs with `docker image save` to protected off-host storage, hash
those files and verify loading in the isolated rehearsal; alternatively require
an explicit registry retention guarantee. Local image availability and mutable
tags are not such a guarantee. No export/registry-retention verification has yet
been performed for the final release set. Harvesters and optional-profile images
must be included even when no container is currently running.

## Backup checks implemented locally

New home producer manifests include `completed_at` in UTC, read after successful
service recovery and archive hashing. The receiver preserves it. Historical
manifests remain unchanged; their filesystem mtime is not substituted for a
verified completion timestamp.

On the receiver, an explicit accepted snapshot can be checked with:

```sh
python3 scripts/check-snapshot-health.py /path/to/OLDAP_BACKUP/snapshots/SNAPSHOT_ID \
  --max-age-hours 30 --min-free-percent 20
```

Add `--verify` to read both archives completely and compare SHA-256 hashes.
The thresholds above are a suggested daily-backup policy, not an installed
schedule. Exit 0 means the selected checks passed; exit 2 requires attention.
The JSON output is limited to status, issues, age, archive verification status
and free-space percentage.
Metadata mode detects missing/truncated archives but intentionally cannot detect
same-size corruption. Neither mode proves Borg integrity or application restore.

This checks one explicitly selected accepted set. It does not select the latest
backup, detect every failed producer invocation, send alerts or monitor Borg.
An older valid set can coexist with a failed newer attempt. A future scheduler
must separately retain the latest attempt result and invoke failure notification
on all nonzero exits (including errors before snapshot publication). Missing
completion, excessive age, receiver capacity and failure to deliver an alert
must all be visible to the operator. Test those paths before enabling scheduling.

Current operator: the owner using the `rosenth` account; confirm the chosen
alert destination and delivery before installing notifications. Production key
recovery belongs in Apple Passwords as requested, with a tested recovery path.
No secret is stored in this repository. Home remains a rehearsal, not a required
nightly backup target. Existing production GraphDB/office-Mac jobs are unchanged.

## Capacity and live verification still open

Previous API archives grew from 23.38 to 28.70 to 32.82 GB; observed TDB index
files grew too. This is evidence of growth, not proof of a leak or its cause.
Compare logical and allocated file sizes, dataset generations, write/job activity
and archive members over a bounded observation window. Do not compact live TDB
or delete generations as an exploratory fix. Plan spare space for old source,
new dataset, fulltext indexes, a complete matched snapshot and isolated restore,
while retaining the existing 20% filesystem reserve.

Initial SSH checks timed out because the university VPN blocked home routing.
After the owner disabled it, all three hosts were reachable. All 14 running
image IDs match the accepted `20261106-studio-staged-03` manifest. Both deployed
Jena JAR hashes match the build manifest; all eleven listed Java source hashes
also match the current local oldaplib checkout. This verifies the running set, not
registry retention or optional stopped harvester images.

The real Studio check streamed and verified both complete snapshot archives.
Exit 2 correctly reports only the missing legacy completion timestamp; archive
integrity passes and the receiver has 62.68% free space. Timestamp errors now
leave independent archive checks running, with separate per-archive results.
Seven unit tests include a legacy snapshot with same-size corruption.

Live TDB occupies 32,419,192 KiB allocated versus 32,534,388 KiB apparent,
under one `Data-0001` generation. POSG/SPOG index files are each 3,430,940,672
bytes. Most storage is physically allocated, not sparse apparent size. The
cause and sustainable growth rate remain unproven; no compaction performed.
See `jena-live-release-check.json`. No service restart or schedule installation.
Production-specific maintenance/recovery commands must be completed against the
source inventory and accepted in gate 3; home-only first-cutover playbooks must
not be relabelled as production commands.


### Concrete idle-write lead (source inspection)

`oldap_api/imports/repository.py::GraphDbImportJobRepository.claim_next` and the
SPARQL export repository's `claim_next` / `expire_next_ready` start and commit
transactions even when no candidate exists. `JenaSessionEngine.reserve` writes
a permanent reservation for BEGIN, and COMMIT writes the owner receipt. Thus
empty polling can persist metadata despite making no domain-data change. This
is a confirmed code path, not yet a measured attribution of the 31 GiB footprint.

Next isolate idle polling and measure receipt counts, allocated bytes and write
rate. A maintainable mitigation is a read-only candidate precheck followed by
selection **again inside the write transaction** when work appears; the second
check preserves concurrency correctness. Never remove reservation/replay guards
or simply prune receipts to reduce size. No application code changed in this
inspection; validate races and job transitions before deploying any mitigation.

Two live samples 224 seconds apart (23:23:16–23:27:00 UTC, November 6;
00:23:16–00:27:00 Swiss time, November 7) show each POSG/SPOG index extending
by 8 MiB logically and about 2.65 MiB in allocated blocks. No workload was
isolated or paused, so this is continuing growth evidence, not a controlled
idle-rate benchmark or a daily capacity forecast.


### Media system disk relief completed

Two old media transfer archives (21,462,362,646 bytes total) were copied from
`/home/rosenth` to private `/data/oldap-retained-transfers-20261107`, fsynced,
SHA-256 checked against both the target and unchanged source, then removed from
the old location. Names and timestamps are preserved; target files are mode
0600 in a 0700 directory. A transfer receipt and hashes are retained both there
and in the sanitized live evidence. These archives were relocated, not discarded.
The media system filesystem fell from 93% to 47% used, with 24,581,968 KiB
available (about 23.4 GiB). No Docker image pruning or service changes occurred.


Follow-up investigation completed: see `tdb-growth-analysis.md` and
`tdb-growth-results.json` for controlled read/commit/abort experiments and the
verified fresh snapshot copy. Idle-write mitigation and full application
compaction/recovery acceptance remain pending; diagnostic analysis is complete.


## Implemented maintenance follow-up (2026-11-07)

The initial revision inventory and unchanged-source statements above describe
the earlier checkpoint. API, library and setup now contain the locally tested
idle-poll mitigation and native compaction changes; refresh source and artifact
identities before freezing the release. Acceptance is recorded in
`jena-compaction-acceptance.json`; the service policy and recovery procedure are
in `../oldaplib/docs/migration/jena-compaction.md` relative to the setup root.

No new API image or service bundle has been deployed to home. Enable
`oldap_jena_compaction_enabled` only with the new bundle and a verified backup.
The default policy checks every 900 seconds, waits 86400 seconds between runs,
and requires both 536870912 bytes of growth and a 2.0 size ratio. The initial
unmaintained store uses the byte threshold. The next periodic check also catches
growth from large operations; no additional public mutation endpoint is needed.

Before activation, verify space for a complete second TDB generation plus the
20% filesystem reserve. The current large home generation may fail this guard;
resolve capacity or use the separately reviewed offline recovery workflow,
never weaken the guard just to force the first run. During compaction new
requests receive 503; active transactions/readers defer maintenance. Observe
real idle growth and successful job processing after the coordinated rollout.

Night-window follow-up: enabled compaction now also requires
`oldap_jena_compaction_zone` (default Europe/Zurich),
`oldap_jena_compaction_window_start` (01:00) and
`oldap_jena_compaction_window_end` (03:00). These defaults restrict admission;
a running compaction finishes safely after the end if necessary. Coordinate
backup timing and verify sufficient runtime margin before enabling on home.
The earlier four-key bundle has been superseded locally; regenerate artifact
identities before deployment.

## Accepted home artifact retention (2026-11-07)

`docs/jena-image-retention-results.json` records exact running image identities,
archive sizes/SHA-256, off-host rehash and development-Docker load checks.
Fourteen running containers use the archived API/media image sets. Separate
archives retain the published Tools image and standard/OCR harvester variants.
Studio location: `/Users/rosenth/OLDAP_BACKUP/releases/home-accepted-20261107`.
The deployed native Jena bundle is retained alongside them; both JAR hashes
match its build manifest. No source services or data were stopped or changed.

Restore procedure: verify the selected archive SHA-256 against the evidence,
then stream it into `docker image load` on the target Docker host. Inspect every
recorded content ID and platform before selecting it in a deployment. Images
saved by content ID may load without repository tags/digests: use the retained
content IDs locally, or assign separate recovery tags explicitly. Never silently
substitute `latest` or assume a registry digest was restored by `docker load`.
The test used the development daemon, not a new empty daemon or a complete
application recovery. The existing full application restore evidence is separate.

This set is the accepted pre-maintenance home release, not the pending new
API/Jena candidate or production GraphDB rollback set. Keep all three identities
distinct. No production release is frozen while gate 3 remains open.

### Notification decision

The owner explicitly declines mail setup on home. Production retains its
existing SUCCESS/FAILURE emails to `lukas.rosenthaler@unibas.ch`; no new SMTP
credentials are needed for home. At production rehearsal verify both success
and an early failing backup path send their result, and separately check stale
backup/capacity monitoring. Existing inventory shows `set -e` can bypass the
legacy final failure-mail branch; fix and test that path before declaring the
production operating gate complete. No email was sent by this work.

Measured maintenance capacity at this checkpoint: TDB logical bytes
33,749,945,586; free bytes 72,719,212,544; required copy-space plus reserve
86,366,742,974. Shortfall is 13,647,530,430 bytes (about 12.7 GiB).
Do not activate compaction until capacity has been increased or separately
verified retained artifacts have been relocated safely. Production has its own
capacity calculation. The idle-poll fix does not depend on compaction admission.

## New maintenance candidate accepted locally

API and Tools `jena-1.0.0-rc1-a30230d5b695` are built for AMD64 and ARM64.
Package imports/dependencies, 10 packaged idle-poll cases per API architecture,
and real Jena network/namespace replacement acceptance pass. Exact IDs, service
source hashes, image archive hash and remaining gates are recorded in
`jena-maintenance-candidate-results.json`. The complete local bundle and a
Studio copy retain wheels, sources, images and service. No registry publication
or application deployment occurred. The prior home release remains active.

## Home client rollout and disk expansion

The existing data disk was expanded from 250 to 350 GiB, followed by online
`growpart /dev/sdb 1` and `resize2fs /dev/sdb1`. Mount, filesystem UUID and
services remain intact. The partition table was retained under root before
changing it. Free capacity now passes the complete-generation plus 20% reserve
check. Exact measurements and rollout identities are in
`jena-maintenance-rollout-results.json`.

API/identity and Tools now select the published a30230d5b695 candidates.
All 27 home checks pass with the old-image semantic story baseline. Raw story
hashes vary because `fasnacht:storyKeywords` IRIs can be serialized as the
registered `L-StoryKeywords:` prefix or full URI. The optional semantic checker
expands only that known IRI field; literal text and all other values remain
exact. Three tests cover equivalence, unchanged input and real differences.
Old/new packaged API reads on the same dataset returned 30 identical stories.

During a 45-second post-update observation neither logical nor allocated TDB
bytes grew. This is short-term evidence, not a sustainable-rate forecast.
The subsequent native write-job acceptance passed all 31 checks in the isolated
restore clone, including ZIP import/export, publication, permissions and graceful
worker restart. The clone is stopped again. Service b112fc4d is now active after a
verified stopped-source snapshot. All 27 live checks pass; recovery is active.
See `jena-maintenance-service-results.json` for exact evidence.

The seven-key policy now enables growth-triggered compaction starts only between
01:00 and 03:00 Europe/Zurich. First live nighttime duration and reclaimed bytes
remain unmeasured; no daytime compaction was forced. About 122 GiB remains free.
The native upgrade play shares the policy template with initial provisioning,
checks snapshot plus compaction reserve before interruption, and rejects rollback
to an old service if a compaction intent remains. Coordinated maintenance stop
waits indefinitely for native completion; do not substitute an ordinary Compose
stop with its finite grace period during compaction. The pre-update API archive
is a local database/configuration recovery point, not a newly paired external
media backup. Previously verified Studio backups and release archives are retained.
