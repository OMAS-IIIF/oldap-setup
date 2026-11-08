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
3. **Fresh-source migration and pre-opening rollback — rehearsals passed.**
   The November 8 coordinated production snapshot is verified locally and on the
   office Mac. The isolated source-to-Jena conversion/import/API comparison and
   rollback pass; see `production-rehearsal-20261108.md`. The later full two-host
   rehearsal also passes: fourteen source services, partial configuration failure,
   private native outage, exact image recovery and source API/media comparison.
   Normal home was restored and compared; see
   `home-production-rollback-rehearsal.md`. The owner approved the documented
   single-word legacy versus multiword Jena AND search difference.
   Final model cleanup/all-project fulltext now pass, including cold-cache API
   acceptance. The pinned core API/media/runtime package is prepared and validated
   offline; see `production-model-package.md`. Final source drift/capacity/image
   preload and all nine private production acceptance checks remain open.
   These rehearsals establish pre-opening recovery against untouched source
   state; after target opening, require reconciliation of new writes rather than
   a simple rollback to old snapshots.
4. **Freeze and operate the accepted release — local preparation in progress.**
   Source inventory and timestamped snapshot health checks are prepared/tested;
   see `jena-release-operations.md`. All 14 running images match the accepted snapshot; Jena JAR hashes and
   Studio archive checks pass (legacy freshness unavailable). Accepted home images (including Tools and both batch harvesters) are now
   retained on Studio with SHA-256 verification and successful Docker load checks;
   see `jena-image-retention-results.json`. Growth mitigation and night-window
   compaction pass local acceptance and are checkpointed. Their new candidate
   passed home rollout and 31 isolated write/27 live checks; first live nighttime
   compaction observation passed on November 8 (38.7 GB to 314 MB). Production rollback images/configuration have now been retained and verified
   (see `jena-production-retention-results.json`); coordinated source data/media
   rollback is rehearsed; the final source/release freeze remains open.
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

November 8 operational follow-up: pinned provider overlays, explicit selectors,
shared snapshot mechanics, complete application/proxy mount coverage and an
explicit production receiver policy are prepared. See
`production-operational-integration.md` and its results JSON. These changes do not
close unattended producer/controller credentials, production backup mail or
receiver Borg/key/scheduling acceptance. Core images and final private cutover
gates remain separate.
