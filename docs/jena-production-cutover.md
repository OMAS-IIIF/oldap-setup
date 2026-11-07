# Production cutover and GraphDB rollback plan

Status: preparation, 2026-11-07. No production write pause or cutover has been
performed. Home service b112fc4d is accepted; first nighttime compaction remains
unobserved. This plan does not remove home-only guards from existing playbooks.

## Fixed source and recovery boundary

API: `rosenth@dhlab-oldap.dhlab.unibas.ch`; media:
`rosenth@dhlab-iii.dhlab.unibas.ch`. Backup receiver:
`rosenth@131.152.51.209`. Production become input stays outside Git at
`/Users/rosenth/.config/oldap/production-become.json`.

There are two separate recovery artifacts:

1. **Preparation package:** exact installed image bytes, private configuration,
   deployment inputs and schedule definitions. It can be retained while online.
   It does not contain a consistent live database/media pair.
2. **Cutover snapshot:** one coordinated, immutable source set with GraphDB,
   both Redis coordinators, API state, media and worker registries. Create it
   only after every writer is drained. Refresh configuration and image inventory
   at that point and reject unexpected drift from the prepared package.

Keep both outside Git, directories 0700/files 0600, with SHA-256 manifests.
Never print environment contents, Compose-expanded configuration or credentials.
Store a verified off-host copy before discarding any source storage. Retain the
original source storage throughout the migration; do not overwrite it with Jena.

## Preparation before the maintenance window

- Confirm VPN/SSH/sudo on both hosts and receiver capacity. Inventory all running
  containers, exact image IDs, mounts, volumes, network dependencies and timers.
- Retain exact source images with `scripts/retain-production-images.py`; it saves
  by image ID, verifies Docker load locally and rejects changed source containers.
  Supplement this with configured Tools and standard/OCR harvester images before
  calling the whole rollback package complete (they need not be running).
- Retain `/opt/oldap` deployment inputs, excluding live Redis data from this
  configuration-only archive; retain `/opt/oldap-mediaserver` inputs, service/
  timer definitions, backup scripts and private backup environment. Include
  archive-writer ACL/TLS/policy inputs and every external configuration bind mount.
  Read actual mounts before selecting paths; do not infer secrets from examples.
- Record the original enabled/active timer states and office LaunchAgent/job.
  Keep the original mail transport and SUCCESS/FAILURE delivery behavior as an
  explicit operational acceptance item, not an assumption based on exit status.
- Pin the accepted Jena release by digest/JAR checksum, including API, identity,
  Tools, harvesters, mediahelper/workers and frontend apps. Keep the accepted
  previous images separately. Preload candidates before downtime.
- Prepare a new isolated target root and confirm capacity for source retention,
  converted import, fulltext index, backup and native compaction reserve. Never
  mount the production media or coordinator into a write-capable rehearsal.
- Capture source API comparison fixtures: projects/models/users, stories,
  archive counts/relationships, permissions, representative searches and media.
  Include parallel archive/story reads; a sequential status check is insufficient.

## Ordered maintenance procedure

The production-specific drain/snapshot/activation command runner still needs a
review and isolated rehearsal. The commands in `oldap-jena-freeze.yml` and
`oldap-jena-activate.yml` are historical home-only workflows, not production
entry points. Do not execute them against production by changing their guards.

1. Record the window start and original service states. Disable scheduled starts
   for backup/harvesting and acquire their existing maintenance lock; wait for
   active jobs to finish. Exclude concurrent deployment and direct GraphDB writes.
   Coordinate the office pull so it cannot accept a partial new snapshot.
2. Close media ingress (`oldap-media-caddy`), then drain mediahelper, ingest and
   export workers while the old API remains reachable. Verify terminal jobs and
   clean worker exit; a forced kill is an abort condition, not successful drain.
3. The current legacy mobile worker cannot use the new SIGTERM drain. With
   ingress/helper stopped, recheck **all** `mobile_*` SQLite tables are empty.
   Only then use its established SIGINT stop path. Any nonempty table requires
   resolving the work or a separately tested compatible drain before proceeding.
4. Close API ingress (`caddy`) and stop `oldap-api`. Recheck ordinary Redis and
   separate `compose-archive-writer-1` coordination for active owners/pending work.
   Do not clear keys or reset writer state to bypass a failed precondition.
5. Export asserted native TriG-star with `infer=false` while GraphDB is still
   running. Verify HTTP success, RDF syntax, export hash and graph inventory.
   Do not reuse a previous live export simply because counts look similar.
6. Stop GraphDB, Redis and archive-writer cleanly; retain all stopped persistent
   mounts. API snapshot includes `/srv/storage/graphdb`, API/coordination state,
   `/opt/oldap/compose/redis-data`, `/srv/storage/oldap-data/archive-writer`, full
   deployment inputs including `/opt/oldap/.env`, and proxy state. Media snapshot
   includes `/data/media`, `oldap-ingest`, `oldap-import-records`, `oldap-exports`,
   `oldap-mobile-uploads`, deployment inputs and actual Caddy state mounts.
7. Compare both archives with their stopped source; create SHA-256 hashes and
   one completion manifest for the pair plus exported RDF and image inventory.
   On failure, do not activate Jena: recover the source in dependency order.
8. Convert into a fresh target using the retained RDF-star conversion workflow;
   validate persisted RDF equivalence. Apply only reviewed, preflighted model/
   relationship changes. Recheck inverse archive assignment, `hasPart` reversal,
   model cleanup and configured fulltext fields. See sibling oldaplib migration
   documents. Four orphan memberships remain inactive; DATA_PERMISSIONS for the
   known conflicting recovery role remains the approved policy. New anomalies
   stop acceptance rather than being silently rewritten.
9. Start private Jena, independent identity verifier and API with final production
   configuration. Coordinate API/identity/media access-token keys; preserve the
   separate media signing key unless an explicit rotation is planned. Keep all
   public ingress and production workers closed during acceptance.
10. Verify counts, relationships, permissions, stories, searches, media access,
    official Fuseki authentication, parallel reads and private bounded writes.
    Test fixtures must be isolated or demonstrably removed before public opening.
    Any unexplained access-control, missing-data or recovery issue blocks opening.
11. Record a durable `target-opened` marker **before** any target worker, scheduled
    writer or public write route is enabled. Then open services in dependency
    order and perform public acceptance. Restore only the intended schedules.
    Keep the source database stopped and retained.

## Rollback before target writes

Abort before opening on failed snapshots/checksums, unknown writers, unsuccessful
drain, coordinator uncertainty, image mismatch, migration anomalies, failed
permissions/media/concurrency checks or insufficient storage.

- Keep ingress closed; stop candidate writers, API and identity, then Jena.
  Wait for native work to finish; inspect any compaction intent before recovery.
- Restore the **matching** original private configuration and exact image IDs.
  Do not use mutable tags or `latest`, and do not pull a newer GraphDB image.
- If untouched original GraphDB/Redis/media state remains intact, restart that
  matched set. If any old operational/media state was modified, restore the
  complete coordinated snapshot into fresh paths and select those paths. Never
  mix old RDF with new Redis, worker registries or partially migrated media.
- Start GraphDB and both coordinators; verify readiness and original writer
  topology, then API, media services/workers and finally ingress. Check old API
  fixtures and fresh-token media authentication before restoring scheduled work.
- Record rollback result and cause. Rehearse this sequence on isolated copies of
  the fresh production snapshot before the actual production cutover.

## After the first possible target write

The opening marker disables automatic GraphDB rollback, including if opening
failed halfway. First close ingress and drain writers, then preserve the new
Jena/operational/media state. Prefer repair on Jena. Returning to the old snapshot
requires an explicit reconciliation plan for every subsequent write; changing
images alone is not a rollback and would risk lost work.

## Remaining execution gates

- Production-specific executable drain/snapshot/activation/recovery adaptation
  and its isolated failure/rollback rehearsal.
- Verified configuration and running/batch image retention on an off-host receiver.
- Fresh coordinated source snapshot, model/fulltext acceptance and restored-source
  rollback test; existing home test data must be retained separately.
- First home nighttime compaction observation and final release freeze.
- Production backup completion/age/failure checks and real SUCCESS/FAILURE mail.
