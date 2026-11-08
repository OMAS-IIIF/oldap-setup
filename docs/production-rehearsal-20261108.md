# Fresh-source migration and rollback rehearsal — 2026-11-08

## Outcome and scope

The fresh paired production snapshot passed an isolated **six-service**
GraphDB → Jena → GraphDB test on api.home.org. Production was recovered after
snapshot capture and has not been switched to Jena. At the end of this isolated
test, normal home retained all eight API-host container IDs, images and start times.
The isolated rehearsal is now stopped; its inputs, both datasets and evidence remain.
See `production-rehearsal-results.json` for checksums and actual API results.

This is not full production acceptance: public proxies/frontends, scheduled jobs,
media workers, partial configuration installation and the two-host rollback
playbook were not exercised by this clone.

Later the same day, the separate fourteen-service two-host rehearsal passed and
normal home was restored with its original images and matching data. See
`home-production-rollback-rehearsal.md`; the limitations above describe this
earlier six-service test, not the later follow-up.

## Retained evidence and execution

- Private local directory: `~/Library/Application Support/OLDAP-Jena/releases/production-rehearsal-20261108`.
- Home root: `/srv/storage/oldap-restore-rehearsal-production-20261108`, root-owned 0700.
- Compose project: `oldap-restore-production-20261108`.
- Original source: `source-compose.json`, binds below `tree`.
- Separate candidate: `candidate-compose.json`, binds below `candidate`; active imported dataset `candidate/data/native-final/dataset`.
- Both networks/mount layouts passed `check-home-restore-isolation.py`; no host ports or external network access.
- Source and rollback API probes use `RESTORE_BACKEND=graphdb scripts/check-home-restore.py` inside the clone API. Jena uses its default mode.

`prepare-production-rehearsal.py` verifies all five captured artifacts before
extracting into a new tree, then builds isolated pinned source configuration.
`verify-rollback-image-archive.py` resolves legacy config IDs against the new
Docker engine by re-exporting and verifying config/rootfs identity when needed.
`prepare-production-jena-rehearsal.py` requires stopped accepted source containers
and copies source state plus accepted static Jena deployment files to new paths.

The packaged `ConvertLegacyRdfStar` converted source RDF with round-trip checks.
`PrepareReviewedProductionRdf.java`, compiled locally against the retained service
libraries, applied the already reviewed permission/default and part-direction
updates to a private RDF copy. It checked the complete before/after quad sets and
serialization round trip. `JenaInitialImport` imported that corrected file into
new native-final storage and verified the persisted dataset. Four orphan role
annotations remain inactive; one DATA_VIEW conflict is removed in favor of the
approved DATA_PERMISSIONS; two hasPart assertions are reversed to isPartOf.

`activate-rehearsal-fulltext.py` applied the nine-field Fasnacht plan. The
`fasnacht-jena.yaml` input is a fulltext plan, **not a full model replacement**.
Final model cleanup and all-project fulltext coverage remain separate work.

After candidate API acceptance, `docker stop -t -1` stopped only the isolated
native container. A socket probe inside its API namespace confirmed port 3031
unavailable. The remaining candidate processes were drained, stopped containers
removed with Compose `rm -f` (no volume deletion), and the original source config
recreated with `up -d --no-deps --pull never`: graphdb/redis/archive-writer first,
then API/media after writer health. Isolation and API acceptance passed again.
Finally the source clone was stopped with `stop -t -1` and live identities checked.

## Results and limits

Stories (30), the first 100 sorted archive results, public/admin capabilities,
and signed image bytes/dimensions agree with production. Story comparison expands
known list QNames to their equivalent IRIs; raw serialization hashes are retained.
GraphDB single-word searches match exactly after restore and rollback. Its legacy
multiword field scoping is order-dependent; Jena correctly returns the same ten
AND hits for either word order. This semantic difference is not migration loss.

The new `oldap-production-rollback-private.yml` is a **prepared, locally tested
production runner**, not a runner executed by the above six-container test. It
requires a root-owned held source checkpoint, no opening intent, closed public
writers, clean stopped GraphDB and original pinned images. It restores only
Compose inputs, excluding Redis and other persistent state, and permits changed
container IDs only while requiring original image IDs. A GNU tar sandbox probe
on home confirms selecting a directory with `--no-recursion` excludes its Redis
subtree. Local failure tests reject wrong hashes, traversal, public writers,
unclean GraphDB and wrong recreated images.

The subsequent two-host rehearsal covered this runner, including partial
configuration failure and all source services. If any original persistent
state was changed, this configuration-only rollback is insufficient: restore the
matched complete checkpoint into fresh storage. Once opening intent is durable,
simple rollback is forbidden even if public opening subsequently fails.
