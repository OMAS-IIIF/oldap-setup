# TDB storage growth investigation — 2026-11-07

## Finding

The combination of empty worker polling, durable OLDAP transaction receipts and
TDB2 copy-on-write index growth is a demonstrated growth mechanism. The large
restored dataset is not explained by its current RDF content alone. This is an
application polling issue amplified by normal TDB storage behavior, not evidence
of OWL inference, duplicate domain imports or Java heap exhaustion.

Apache documents that TDB2 copies modified blocks in write transactions and that
compaction reclaims historical blocks:
https://jena.apache.org/documentation/tdb/faqs.html
https://jena.apache.org/documentation/tdb2/tdb2_admin.html

## Controlled experiment

`TdbIdleGrowthProbe` uses the exact deployed OLDAP service JAR SHA-256
`42901bf6b98d8a92df2fce65b3799ee5dd45abb6e843ef7016a5a6d6da038694` and the
reviewed Fuseki dependency SHA-256
`2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee`.
Each mode creates a separate fresh local dataset with 10,000 synthetic domain
triples, then performs 1,000 empty-job checks through the real session engine.
No fulltext wrapper, HTTP/authentication, production data or running services
are involved. These are storage-mechanism tests, not deployment throughput tests.
Mac filesystem timings must not be compared with home VM throughput.

- READ: no receipts and no file-size growth.
- BEGIN/QUERY/COMMIT: 2,000 receipt triples, domain still 10,000. Logical files
  grow from 201,714,747 to 361,148,414 bytes: 159,433,667 additional bytes
  (152.05 MiB). Allocated size after close is 361,230,336 bytes.
- BEGIN/QUERY/ABORT: 1,000 reservation triples remain, domain still 10,000.
  Logical files grow by 58,770,338 bytes (56.05 MiB); replacing commit with
  abort does not avoid the durable BEGIN reservation. Full measurements are in
  `tdb-growth-results.json`.

The fixed initial allocation and block-sized file extensions make short-run
per-operation estimates approximate; do not linearly extrapolate a daily disk
budget from this small synthetic fixture.

## Restored snapshot inspection and fresh rebuild

The stopped disposable `oldap-restore-staged-03` dataset, including the preceding
write-acceptance fixtures, was opened exclusively in a temporary no-network
container. The live dataset was never mounted. Queries found 272,226 named-graph
triples: 205,955 internal receipt triples and 66,271 others (domain, vocabulary,
model, authorization and operational graphs). Counts alone do not tell which
individual receipts came from idle polling.

A new independent TDB dataset received all 272,226 source quads in one transaction,
including the receipt graph. Verification checked every source quad in the target
and equal total counts. No receipt or domain triple was removed.

| TDB generation | Allocated KiB |
| --- | ---: |
| Restored source `Data-0001` | 31,999,064 |
| Fresh copy `Data-0001` | 116,208 |

This is about 30.52 GiB versus 113.48 MiB of physical storage for the same RDF
content. The source managed-text directory occupies an additional 1,560 KiB and
is excluded from that comparison. The fresh copy is diagnostic only: it lacks
the application markers, managed-text configuration/index and deployment state.
It is not a replacement backend or a complete restore. No native compaction or
live dataset replacement was performed. Original backup archives remain intact.

## Concrete application paths

- `oldap_api/imports/repository.py`, `GraphDbImportJobRepository.claim_next`:
  starts and commits even with no job candidate.
- `oldap_api/exports/worker_service.py`, `ExportWorkerService.claim_next`:
  invokes expiry, audit purge and claim in succession. Their SPARQL repository
  methods each start and commit a transaction even if nothing is due.
- `oldap_api/mobile_media/lifecycle.py`, `claim_next`: same empty transaction
  pattern for the mobile lifecycle outbox.
- `JenaSessionEngine.reserve` persists one reservation for every BEGIN;
  COMMIT adds an owner receipt. Reservations intentionally survive ABORT and
  are not TTL-pruned, to reject delayed/replayed operations safely.

Both running ZIP workers specify a ten-second poll interval. The mobile worker
source bounds lifecycle polling to twenty seconds. With continuously empty queues
and those intervals, ignoring request time, these paths alone can initiate roughly
38,880 transactions/day: import 8,640, export 25,920 and mobile 4,320. This is a
code/configuration estimate, not a measured live transaction count or proof that
all historical growth originated in these paths.

## Recommended order

1. Add a read-only eligibility precheck to these concrete repository operations.
   Return without BEGIN when there is no work. If a candidate exists, begin the
   transaction and **repeat selection and validation inside it** before changing
   anything. Preserve existing public signatures, leases, atomic claims and replay
   protection. Cover candidate disappearance/change and competing workers in tests.
2. Compare idle growth with the same images/data in an isolated rehearsal before
   deploying: empty queues should not generate receipts; real jobs must retain
   existing exactly-once/recovery behavior. Do not merely increase polling delays.
3. After preventing avoidable writes, rehearse a coordinated compact/rebuild on a
   stopped clone, including fulltext, namespace recovery, permissions/search/media
   and rollback. Only then reclaim live historical storage in an agreed procedure.
4. Measure legitimate write-heavy growth and establish a compaction/capacity policy.
   Preserve recoverable older generations until acceptance; no receipt pruning or
   automatic compaction schedule is justified by this experiment alone.

This analysis changes diagnostic tooling/documentation only. Production and home
application code, worker schedules and live database contents are unchanged.

## Reproduction

Sources are in `scripts/tdb-growth`. Compile with JDK 25 and the two pinned JARs;
run the compiled classes on the same classpath (Java source-launcher classloaders
cannot access the package-private engine helpers). `TdbIdleGrowthProbe` refuses
existing paths and accepts only read/commit/abort and 1..10,000 rounds.
`SnapshotCounts` and `SnapshotRebuild` use fixed `/snapshot` and `/rebuilt` mounts.
Bind only an exclusively stopped disposable clone; TDB needs writable locks even
for read transactions. Run without network, with bounded memory/CPU and no live
volumes. `SnapshotRebuild` refuses an existing destination dataset.

Private working evidence: `/tmp/oldap-tdb-growth-20261107` locally and diagnostic
fresh dataset `/home/rosenth/oldap-tdb-growth-rebuild-20261107` on api.home.org.
These retained working files are not backups or deployed services.


Example local mechanism probe (use a new root for every run):

```sh
javac -cp "$SERVICE_JAR:$FUSEKI_JAR" -d "$CLASSES" scripts/tdb-growth/*.java
java -Xmx1g -cp "$CLASSES:$SERVICE_JAR:$FUSEKI_JAR" TdbIdleGrowthProbe "$NEW_ROOT" commit 1000
```

The variables must identify the verified JARs, a diagnostic class directory and
an absent dataset directory. Run read and abort modes against separate new roots.
