# Final Jena production gates after home acceptance

This is the current Jena checklist. Older `production-preparation.md` checkpoints
refer to the September GraphDB/archive rollout and must not be interpreted as
instructions to resume historical maintenance.

Already demonstrated on home: application deployment, coordinated worker drain,
namespace/crash recovery, API/media comparisons, Borg file recovery, and one
isolated running application restoration. Backup manifests now retain actual
image identities. See the dated home runbooks for exact scope and limitations.

Before the first production cutover, close these bounded gates:

1. **Backup/recovery acceptance — passed, staged performance proposal rejected.**
   The full-size staged backup, Studio/Borg verification and isolated application
   restore passed; see `home-staged-backup.md`. Its 16m20s outage was worse than
   the prior 11m25s, so the simpler offline media tar/compare flow remains default.
   Retention/scheduling/monitoring and production image availability remain
   operational gates below; do not repeat every earlier test without a new reason.
2. **Restored write/worker acceptance — passed.** The isolated Borg-restored
   dataset passes editor/reader/public checks, object edits, PNG upload, ZIP
   validation/import/export, archive transformation and atomic publication/replay.
   SIGTERM during a claimed import drains to IMPORTED and exits 0; restart leaves
   exactly two imported resources and an unchanged publication receipt. All nine
   containers stopped, live source unchanged. See `home-restore-writes.md` and its
   evidence JSON. Bounded functional scope, not a load test or arbitrary crash
   matrix; mobile resumable workers and harvesting are excluded from this probe.
3. **Fresh-source cutover and rollback rehearsal — preflight in progress.**
   Fresh native RDF-star conversion and offline persisted import pass; source
   writer/configuration and legacy mobile shutdown differences are recorded in
   `production-backup-inventory.md` (2026-11-07). No coordinated snapshot or
   real fresh-source rollback has run yet. Preserve home test work before
   replacing it. Rehearse the documented GraphDB-to-Jena migration with a fresh,
   coordinated production export/media snapshot and the final pinned release set.
   Verify counts, relationships, permissions, search and media. Rehearse rollback
   to the matched old data/configuration/images before reopening writes. After
   new production writes are admitted, rolling back old snapshots would lose those
   changes; require an explicit reconciliation/restore plan, not just an image swap.
4. **Freeze and operate the accepted release — local preparation in progress.**
   Source inventory and timestamped snapshot health checks are prepared/tested;
   see `jena-release-operations.md`. All 14 running images match the accepted snapshot; Jena JAR hashes and
   Studio archive checks pass (legacy freshness unavailable). Accepted home images (including Tools and both batch harvesters) are now
   retained on Studio with SHA-256 verification and successful Docker load checks;
   see `jena-image-retention-results.json`. Growth mitigation and night-window
   compaction pass local acceptance and are checkpointed. Their new candidate
   still needs home rollout/observation. Production rollback image retention and
   final source/release freeze remain open.
   Growth mechanism is now reproduced: empty worker transactions persist receipts
   and amplify TDB index storage; see `tdb-growth-analysis.md`.
   Review/checkpoint pending Git
   changes, pin the tested images and retain them or guarantee registry retention.
   Write the production-specific maintenance, recovery and acceptance commands;
   establish capacity and backup success/age/failure monitoring. The owner requests
   no home email setup; production must preserve existing SUCCESS/FAILURE mail
   to lukas.rosenthaler@unibas.ch and verify delivery during cutover rehearsal. Investigate the observed TDB index/archive growth documented in
   `home-staged-backup.md` before capacity and maintenance decisions. Do not enable an untested schedule or modify existing production backups
   merely because home acceptance passed.

These are final acceptance gates, not a request to restart all earlier performance
or feature work. The known QName/full-IRI serialization variability should be
assessed against actual clients during the fresh-source acceptance. No unresolved
access-control, data-loss or recovery issue may be waived as cosmetic.
