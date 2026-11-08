# Reviewed model, fulltext and production core package — 2026-11-08

## Accepted result

The frozen production snapshot contains six projects and 23 named graphs. Its
GraphDB filesystem backup contains one Lucene connector: `fasnacht`, with exactly
the nine fields and predicate paths in the reviewed portable plan. Chama, mkb_pc,
oldap, shared and tgb had no source connector; no indexes were invented for them.
Connector settings do not appear in the RDF export: retain the paired
`storage/lucene-connector/config.json` from `api.tar` for every final inventory.
GraphDB type/language/analyzer options are recorded, not silently translated.
The previously accepted Jena AND/folding semantics remain unchanged.

After the existing membership/default-permission and data-part corrections,
`PrepareProductionModel` removes exactly **27 model quads**: the two inline
`dcterms:hasPart` fields on Fasnacht Place/CarnivalThing (including owner links),
the two project inverse axioms and the unused project property declaration.
It leaves all other quads unchanged and verifies RDF round-trip and idempotence.
External vocabulary proposals remain vocabulary metadata, not modeled fields.
Chama's four legacy inverse axioms remain unchanged under the existing bounded
query compatibility; this is not an OWL reasoner or a global inverse migration.
Unexpected owners, shared/nested/annotated shapes or other hasPart restrictions
stop cleanup for review. Ordinary API deletion guards are not weakened.

The cleaned RDF was imported into a new isolated native dataset, closed/reopened
and compared by the importer. All six model APIs return 200. Fasnacht retains
16 classes; both obsolete fields are absent, isPartOf remains, and Place still
has maximum one parent. All thirteen API baseline fields match, including
permissions, stories, archive, fulltext and signed media. The same checks pass
after clearing derived caches and restarting. The six isolated services are
stopped; all eight live API-host container IDs/images/start times stayed unchanged.

See `production-model-package-results.json`. Validation: 66 Python production
workflow tests, seven Java cleanup safety scenarios, real isolated API/model/cache
checks, complete archive/hash/Compose validation and both exact Caddy images
validating with networking disabled. Production was not changed.

## Private, immutable artifacts

Private directory:
`~/Library/Application Support/OLDAP-Jena/releases/production-candidate-20261108`.
Use **`package-final`**, not the earlier intermediate package directories.
All five package artifacts are additionally retained and SHA-256 verified on
Studio under `OLDAP_BACKUP/releases/production-candidate-20261108`.
`release-manifest.json` binds these artifacts with SHA-256:

- `package-final/candidate-api.tar`: complete pinned API/identity/Jena/Redis,
  frontends and proxy configuration; the selected `.env` chooses only that file.
- `package-final/candidate-media.tar`: complete pinned media services and proxy.
- `package-final/candidate-runtime.tar`: accepted native release, identity entry
  point, production archive policy and private native service configuration.
- `candidate-migration.tar`: reviewed offline Java operators and compiled classes,
  correction/preflight SPARQL, fulltext plan/check and selective cache cleanup.
- `package-final/manifest.json`: file hashes, image identities, input provenance,
  source configuration hashes and remaining activation gates.

The package uses accepted home topology/images with **production** account/JWT
keys, URLs, mail settings and archive policy. It refuses fallback to home account
secrets. Internal Jena keys are newly generated and agree between native service,
API, identity and proxy. The production Fuseki console uses the existing production
GraphDB proxy account/hash, with a separate fresh native administration key.
Both API hostnames block private identity callback routes. Existing media and
Caddy storage paths are preserved. Jena/API/Redis writable state goes below the
new `/srv/storage/oldap-jena-production-20261108/data` root.

This is the **core runtime package**, not approval to open production. It does not
include or enable batch schedules. Final source drift/capacity checks, exact image
preloading, all nine private production checks, and Jena backup/harvester/receiver
wiring remain mandatory. Do not resume old GraphDB jobs against Jena.

## Reuse at the actual cutover

1. Take the final coordinated production checkpoint with writers held stopped.
   Verify the complete pair and recheck the package's source configuration hashes.
   A configuration change requires a newly reviewed package, not editing locked
   archives. Never install the old rehearsal dataset as the final production data.
2. Convert the **fresh final** RDF using the pinned service converter. Run the
   existing `PrepareReviewedProductionRdf` default-permission/part-data correction
   against that converted file with its actual checksum and reviewed SPARQL.
3. Run `InventoryProductionModel INPUT SHA NEW-INVENTORY-DIR`. Compare every
   filesystem connector with explicit portable plans using
   `check-production-fulltext.py --projects projects.json --connectors config.json
   --plan fasnacht-fulltext-plan.json`. New/unknown connectors or changed fields
   fail instead of being skipped. Review the source restrictions separately.
4. Run `PrepareProductionModel REVIEWED-RDF SHA NEW-OUTPUT-DIR`. Retain its report
   and output checksum. This is an offline, narrowly scoped target transformation;
   do not load the complete ontology YAML over an existing model to imitate it.
   Java classpath: `migration/classes:release/lib/*`, using the accepted JDK 25.
5. Install the verified runtime into a **new** target root. Preserve source paths.
   Copy frozen API operational storage into `data/api` and ordinary Redis into
   `data/redis`; create `data/native` for UID/GID 1000. Import the cleaned RDF with
   `JenaInitialImport` into the new `data/native/dataset`, using its actual checksum.
   The importer must verify persisted RDF and publish the service marker.
6. Before starting target API/identity clients, verify via Docker inspection that
   target Redis mounts the new `data/redis`, and that all its clients remain
   stopped. Run `clear-migrated-model-cache.py` against that target copy, first
   without `--apply`, then with it. The URL is supplied through `OLDAP_REDIS_URL`,
   never through a logged command-line password. Run with the accepted API Python
   image on the target Redis network namespace if no operator Python environment
   is installed. **Never run this on source Redis or use FLUSHDB.**
7. Start the private candidate in namespace dependency order. Activate the reviewed
   fulltext configuration through the existing API helper and verify it. Keep
   ingress/media writers closed until all nine private acceptance checks from
   `production-cutover-runner.md` pass and the explicit opening step is approved.

Cache cleanup selects only explicit `CacheSingletonRedis` object classes and uses
compare-and-delete to refuse a concurrently changed value. Revocation/session
records, unknown JSON, other Redis types and other databases remain untouched.
Real sentinel checks prove auth and coordination preservation; the real clone's
derived objects were rebuilt successfully. The ordinary Redis copy does not
replace the old separate GraphDB writer coordinator; Jena uses its accepted
native coordination and target staging Redis wiring.

Runtime directories/data ownership and external bind inputs must be checked on
the production hosts before startup. Local archive validation does not establish
that those paths, images, DNS or capacity are already present on production.
