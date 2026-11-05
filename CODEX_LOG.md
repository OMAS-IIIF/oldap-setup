### Update 2026-11-05 14:03
- Decisions: Bound total Jena memory on the 16-GB home VM to 10 GiB, with 6 GiB heap, 512 MiB direct buffers and no container swap. Preserve images, service binary, data and public APIs.
- Implementation: Added Compose/candidate budgets, capacity preflight, guarded home rollout with configuration rollback, cgroup sampler and runbook/evidence. Deployed successfully on home with coordinated writer shutdown and namespace consumer recreation. 375 read requests pass, common responses match before/after, 90-second sample peaks at 2.52 GiB without OOM/swap/restarts. 82 setup cases: 78 passed, four skipped; syntax checks pass.
- Open: Automatic namespace recovery, mobile SIGTERM draining, longer/write-heavy capacity acceptance and off-host restore before production. No production deployment, image publication, push or merge.
- Risks/Assumptions: Cache residency/accounting changes across restart; do not claim measured resident-memory reduction as a lasting saving. The historical native OOM cause remains unidentified; the cgroup protects host capacity but can still terminate Jena under extreme demand. Rollback was not fault-injected on home. See docs/jena-memory.md and results JSON.

### Update 2026-11-05 12:09
- Decisions: Secure reviewed migration sources as local per-repository commits before further production readiness work; do not push, merge, publish or deploy in this step.
- Implementation: Added coordinated revision/verification inventory in docs/jena-git-checkpoint.md. Setup suite: 81 cases, four skipped; all executed tests pass. Reviewed deployment evidence and candidate changes; whitespace and Python syntax checks pass. Read-only home browser checks render archive records and stories.
- Open: Total Jena memory bounds, coordinated namespace recovery, mobile draining, authenticated acceptance and off-host restore before production; then coordinated release/merge.
- Risks/Assumptions: Existing skipped tests and earlier runtime checks retain their documented scope. No production or home configuration/data changed.

### Update 2026-11-05 00:52
- Decisions: Accept the official, unmodified Apache Fuseki UI on home with native administrative writes; keep dataset lifecycle in deployment and production unchanged.
- Implementation: Activated the single-JVM native listener (service SHA 42901bf6b98d8a92df2fce65b3799ee5dd45abb6e843ef7016a5a6d6da038694). Browser index matches the pinned Apache JAR; query editor, file upload, SPARQL updates and cleanup pass. 20 administration, 22 existing service, 13 setup and 26 public API/media checks pass. Updated configuration example, runbook and acceptance evidence.
- Open: Production-specific activation and existing production readiness gates. No public Python signatures or application images changed.
- Risks/Assumptions: Direct admin writes intentionally bypass OLDAP validation/permissions; protected receipts and managed text remain enforced. Initial Compose CLI failure was recovered, corrected and guarded by dry-run before successful activation. Offline snapshot: /srv/storage/oldap-fuseki-before-20261105T004721/api.tar. GraphDB credentials unchanged; test graph removed.

### Update 2026-11-05 00:45
- Decisions: Replace the custom query reader with official Fuseki, retaining independent console passwords and unchanged GraphDB credentials.
- Implementation: Added native administration overlay and coordinated home installer with preflight, offline API-host snapshot and rollback. Shared home stop/start tasks with the snapshot workflow. Removed custom reader source; official UI stays in the pinned Apache JAR. Home activation and browser verification in progress.
- Open: Finish home activation and live browser/API verification; production remains unchanged.
- Risks/Assumptions: Direct administrator writes bypass OLDAP validation/resource permissions by design. Native transactions share the single TDB owner and managed text index. No dataset creation/deletion/compaction through UI.

### Update 2026-11-05 00:28
- Decisions: Use independent home console credentials from the operator's private file; preserve GraphDB credentials exactly. Production remains undeployed.
- Implementation: Added independent Caddy/console credential variables and rollback of proxy environment; deployed fingerprinted console. Fixed RDF 1.2 nested term rendering and WSGI bytearray response; disabled unused Gunicorn control socket. Added live browser acceptance and raw WSGI regression assertion. Documented deployment, rollback and acceptance.
- Open: Existing production migration/recovery gates remain; console is read-only SELECT/ASK, not full Fuseki management.
- Risks/Assumptions: Administrator has dataset-wide read access. All 16 regressions and live browser checks pass, including 23 graphs and authentication/query barriers. Original GraphDB credential lines unchanged. Seven existing API/Jena/Redis/frontend containers retained IDs/start times; only Caddy recreated for credentials. Evidence: docs/jena-console-home-results.json.

### Update 2026-11-05 00:16
- Decisions: Add a Basic-authenticated administrative SELECT/ASK console to the existing Jena reader; do not open TDB in a second JVM or expose transaction routes. Reuse existing GraphDB administrator credentials; no normal OLDAP role semantics implied.
- Implementation: Added isolated console source/Compose overlay, fingerprinted deployment with rollback, optional home/production Caddy host, same-origin query gate, bounded results/time/concurrency and text-only rendering. Preserved SALSAH overlay compatibility and optional console namespace recovery during snapshots. Eight focused tests plus SALSAH/recovery regressions pass; deployment syntax checked.
- Open: Activate on home, verify real read queries and browser authentication using the operator's private credential file. Production hostname is prepared but not deployed.
- Risks/Assumptions: Admin reader can inspect application/admin graphs; receipt graph remains hidden by the existing protected dataset. Only SELECT/ASK with bounded SELECT limits; SERVICE/FROM and Unicode escapes disabled. Existing Jena 60-second query timeout remains authoritative. Original GraphDB and production images/configurations remain unchanged.

### Update 2026-11-04 23:56
- Decisions: Accept the four isolated app candidates on home after live verification; retain stable tags, production, data and existing roles.
- Implementation: Published/deployed digest-pinned oldap-app, SALSAH, Fasnacht and mediahelper/three workers. 28 live API/media checks pass; real browser views pass. Packaged HE-AAC ZIP/conversion succeeds on a two-second copy of the 1946 film, retaining original hash and audio profile. Six infrastructure container IDs/start times unchanged; seven protected registry tags unchanged. Exact references/backups: oldap-setup/docs/jena-apps-home-results.json and jena-apps-home.md.
- Open: Interactive authenticated writes/uploads and audible cross-browser HE-AAC acceptance; existing production migration/recovery/drain gates. No commits/merges made.
- Risks/Assumptions: SALSAH DNS now correct. API recreated only for registry/CORS. Media preflight profile omission was corrected before stopping services; successful run used guarded legacy mobile SIGINT with empty registry and no forced kill. SIPI-2 stays on 0.1.0.

### Update 2026-11-04 23:54
- Decisions: Include all Compose profiles in the staged media-image preflight.
- Implementation: Installed workers are profile-gated; default Compose config omits them. Added explicit --profile '*' to candidate validation and a real Compose regression resolving all four services. Four focused deployment tests pass.
- Open: Retry guarded media activation and complete live acceptance.
- Risks/Assumptions: Initial preflight stopped before any service shutdown or installed configuration change. The published runtime image is unchanged.

### Update 2026-11-04 23:39
- Decisions: Publish isolated, source-fingerprinted AMD64 candidates for home without moving stable or latest tags.
- Implementation: Added secret-free source snapshot preparation, digest-only frontend update/rollback and additive SALSAH candidate support with configuration backups. Sixteen deployment tests and playbook syntax checks pass.
- Open: Complete image/runtime verification, publication and home activation; SALSAH DNS requires correction.
- Risks/Assumptions: Working-tree fixes are included in the fingerprinted source bundle; no commit/merge or production deployment.

### Update 2026-11-04 23:02
- Decisions: Support SALSAH as an additive frontend on existing Jena installations without changing backend selection or exposing private identity callbacks.
- Implementation: Extended the known Compose topology guard for Jena/archive-policy overlays; added the internal-Jena path block to api.salsah.org. Regression coverage resolves the actual four-overlay stack and checks both public API domains. 13 SALSAH/Jena deployment tests and Ansible syntax validation pass.
- Open: SALSAH home hostname/DNS/TLS, API/media origin and trusted mail configuration, followed by explicit installation and browser acceptance.
- Risks/Assumptions: Existing GraphDB topology remains accepted. No playbook deployment, API restart, role or resource changes. Sibling SALSAH migration checkout records frontend/API compatibility results.

### Update 2026-11-04 22:53
- Decisions: Accept digest-pinned harvester RC2 on home after bounded real-source and native OCR checks; preserve normal GraphDB tags and production state.
- Implementation: Published/tested all three RC2 images (136 tests each), installed standard/OCR on home, completed one new Europeana publication and existing Swisscovery/PDF replay. Repeated CLI runs leave API snapshots identical; three public reads pass and preexisting resources are unchanged. Native OCR: 24.07 seconds, 34 lines, exact reference hash. Added reusable publication/home/OCR probes, first-install inputs and credential preflight. Evidence: harvester docs/jena-home-results.json and setup docs/jena-harvesters.md.
- Open: Production cutover, broader harvesting and optional scheduling remain separate. Source changes are not committed/pushed by this operation.
- Risks/Assumptions: RC1 was superseded after pre-write endpoint/configuration failures; published candidate tags were not overwritten. Existing PDF text was reused; fresh OCR was verified separately on a retained page. One new real Europeana record remains on home. No role changes or active API/backend restarts.

### Update 2026-11-04 22:43
- Decisions: Publish immutable Jena candidates and validate bounded real home harvesting; retain GraphDB tags and production state.
- Implementation: Extended home installer with optional retained first-install Swisscovery config/model, approved checksum validation and mounted config validation. Installed rc1 candidates and inputs on home; legacy endpoint rejection occurred before writes. Subsequent rc2 installation and bounded acceptance are in progress.
- Open: Complete native OCR, import/replay acceptance and record final published digests.
- Risks/Assumptions: Real home writes are authorized; no production imports or role changes. Source/model identities are retained from the synchronized production baseline.

### Update 2026-11-04 22:29
- Decisions: Keep harvester candidate tags separate and preserve installed Jena networking, policy and batch locks; retain independent harvester versioning.
- Implementation: Added standard/OCR batch image overlays, home-only digest installation playbook and backend-aware launchers. Candidate lock helper accepts the harvester version independently while enforcing coordinated core versions. 17 deployment/scheduling tests and three offline lock tests pass; playbook syntax passes.
- Open: Publish accepted images and execute home installation plus bounded real-source acceptance before production.
- Risks/Assumptions: Existing source configuration, Swisscovery mounts/model and publisher permissions are prerequisites. No batch, schedule or live service was started or changed. BMG-Archivist membership remains unchanged by user decision.

### Update 2026-11-04 22:05
- Decisions: Restore reviewed publication configuration on home; keep publisher role membership separate from private workspace roles and preserve resource-level authorization.
- Implementation: Added Fasnacht publication block from the established frontend policy example. Deployment now stages/validates references before replacing live policy, retains previous file and force-recreates only API for bind-mount refresh. Seven deployment tests and syntax validation pass; live publisher capability and two-resource DATA_RESTRICTED preview pass without apply. Account BMG-Archivist currently lacks ArchiveMediaEditor; assignment question remains pending.
- Open: User decision on that account's extra editorial role; then verify its capability. Actual publication remains user acceptance.
- Risks/Assumptions: No membership/resource changes, no public grants, no image rebuild, no production deployment. Configuring publication also enforces the existing publication-command safeguards and configured root creation grants. System/bootstrap admin status alone does not bypass publisher membership.

### Update 2026-11-04 12:22
- Decisions: Activate the exact published 1.0 RC API/Tools digests on home after a verified two-host offline snapshot; preserve test data and existing Java service bytes.
- Implementation: Snapshot 20261104-rc1-b completed: API 7,884,646,400 bytes, media 21,166,551,040 bytes; tar comparison with stopped sources and SHA-256 manifest pass. Recreated old namespace consumers during recovery, then updated API/identity and Tools selection through existing playbook. All 27 public checks pass, including exact equality of all 30 pre-update stories; 48 requests at concurrency 16 return 200 with complete response equality. Native Tools help and 21 setup tests pass. Recorded full sanitized evidence in docs/jena-1.0rc1-home-results.json.
- Open: Manual write/upload acceptance; total Java memory bounds, automatic namespace recovery, mobile SIGTERM draining, off-host restore and remaining production gates.
- Risks/Assumptions: Kernel journal proves global OOM killed Java at 08:32:27 CET with 14,790,676 kB anonymous RSS, despite post-restart Docker OOMKilled=false. Post-acceptance Jena memory about 2.2 GiB is not a long-run memory guarantee. First failed snapshot has no completion manifest; second legacy SIGINT stop required all eight mobile tables empty. Production and media image versions unchanged; no data migration. Credentials stayed in private local storage.

### Update 2026-11-04 12:02
- Decisions: Use supplied private Ansible credentials without displaying contents; retain current home test data and take an offline two-host snapshot before updating clients.
- Implementation: Added home-only snapshot playbook with fresh-path/container admission, writer shutdown, stopped-state checks, tar comparison/SHA manifest and ordered recovery. Recovery recreates namespace consumers after owner restart and refuses ingress after failures. Added fake-Docker success/failure tests and Make integration. First run rejected legacy mobile SIGTERM timeout/exit 137 and restored old services; second run uses explicitly guarded SIGINT only after verifying all mobile registry tables empty.
- Open: Snapshot verification, candidate client activation and public/concurrent acceptance are in progress. Proper mobile worker draining and automatic namespace-consumer recovery remain production gates.
- Risks/Assumptions: Single operator/no external writers; snapshots remain on their source hosts. Two recovery tests (including four injected failure subcases) and Ansible syntax/readiness checks pass. No mobile work was registered. Never accept the first incomplete snapshot as a backup; no source data or media image changes.

### Update 2026-11-04 11:46
- Decisions: Publish accepted 1.0 RC image IDs and prepare home update without resynchronizing production/test data.
- Implementation: Published API/Tools AMD64/ARM64 and multiarch indexes; verified protected tags unchanged. Pulled exact digests on home; native isolated transport passes nine checks. Recovered preexisting HTTP 502: Jena had restarted but API/identity retained a stale network namespace. Stopped/restarted existing clients in order; 26 public checks pass, 30 stories. Recorded publication/digests/current baseline; prepared deployment vars and checked playbook syntax.
- Open: Administrator access requested for coordinated backup on both hosts and client image update; no backup/image replacement yet. Investigate backend restart trigger and implement durable coordinated recovery before production.
- Risks/Assumptions: Current service source and jar hashes equal locally accepted wrapper despite older version label. API/identity use old images until explicit pending update. Docker reported OOMKilled=false; that does not establish restart cause. Current recovery changed only old client process state; data preserved. No production changes.

### Update 2026-11-04 00:20
- Decisions: Build isolated 1.0.0rc1 Jena API/Tools candidates locally from clean committed sources; preserve exact accepted IDs for later explicit publication.
- Implementation: Prepared durable release bundle, rebuilt matching Java service, built AMD64/ARM64 images with fingerprint 4d3c5ef8e1e1. All package/pip/UID checks and Tools CLI checks pass; both API architectures pass real packaged transport, authentication, contention, isolation and namespace replacement (18 PASS records). Recorded source commits, image IDs and dependency inventories in docs/jena-1.0rc1-images-results.json. Owned containers cleaned up.
- Open: Explicit publication and native home full-workflow/concurrency/recovery acceptance; media/harvester compatibility and production gates remain.
- Risks/Assumptions: AMD64 runs under Docker Desktop emulation; dependency resolution follows constraints rather than exact Poetry locks. Images reside in local Docker; bundle retains wheels/service/logs but no image archive. No push, registry manifest, deployment or stable/latest tag change. Docker emits a harmless missing-default build-argument lint warning; pinned base digest is explicitly supplied.

### Update 2026-11-03 23:54
- Decisions: Prepare 1.0.0rc1 for library/API/tools and the OLDAP Jena wrapper; final 1.0.0 waits for acceptance. Keep independent media/harvester versions and running environments unchanged.
- Implementation: Checkpointed HTTP pooling (e62651a) and API evidence (44cecf7). Aligned runtime/package/bump/OpenAPI/wrapper metadata; API/tools use portable 1.x requirements. Poetry solver regenerated locks offline from existing packages plus the exact new library wheel, with no path/source entry; library lock now tracked. Setup pins candidate wrapper and supports existing isolated image tags with prerelease metadata. Fixed tools bump command typo; documented local wheel/editable workflows and artifact hashes.
- Open: Final clean candidate images/home acceptance, media/harvester 1.x compatibility, production recovery/update gates and explicit package/image publication. Index installation cannot fetch the unpublished library RC; use local wheels/editables as documented.
- Risks/Assumptions: 297 installed offline tests + 26 subtests, 3 installed HTTP tests, 22 rebuilt-service checks including 300 commits, pip check, OpenAPI and three rc-to-final dry runs pass. Offline lock tests: 2 + 2 subtests; image candidate tests: 7. API/tools locks retain third-party versions; fresh pip wheel test uses declared constraints, not exact lock versions. No push, tag, merge, published image or deployment. Existing Poetry/Typer/RDFLib deprecations remain.

### Update 2026-11-03 23:41
- Decisions: Checkpoint setup migration and inherited harvesting work locally; distinguish accepted home rehearsal from unfinished production release/restore workflows. No remote execution, merge, push or publication.
- Implementation: Reviewed candidate preparation, frozen source/activation, callback namespace lifecycle, bounded updates, media-key alignment and isolated image publisher. Activation refuses prior target-opening markers; freeze requires GraphDB. Rollback enumerates existing containers, stops/removes clients before backend and aborts on errors instead of ignoring them. Extended test target and release/readiness documentation.
- Open: Commit library HTTP pooling/API evidence, coordinate 1.0 wrapper/package versions and consumer constraints, exact final artifact/home acceptance, production writer inventory/update lifecycle and off-host restore. Home-only playbooks must not be relabelled as production automation.
- Risks/Assumptions: 60 tests + 34 subtests pass; one optional Linux/container harvesting lock test skipped. Nine Jena playbook syntax checks pass. Actual rollback commands tested under fake Docker failures (inventory/stop/remove), partial and empty container sets; no real backend started. Existing same-host backup and earlier library restore evidence do not establish off-host production recovery. Concurrent operators during cutover remain unsupported.

### Update 2026-11-03 22:10
- Decisions: Prepare coordinated core OLDAP 1.0 release before merge; keep independent media/frontend versions and current working trees intact.
- Implementation: Fetched four origins, checked ancestry and committed merge trees, inventoried working-file hashes, compared setup harvesting changes with the original checkout, reviewed local workflows/version/publishing recipes. Added concrete merge plan and four PR drafts; documented dependency and final artifact gates.
- Open: Review/commit outstanding migration files, verify hosted automation, update/test 1.x dependency ranges and final release tooling, record deployed GraphDB baselines, then merge and perform final home acceptance. No version files, branches, indexes, tags, remotes or services changed apart from fetch-updated remote refs; no merge/push/publication.
- Risks/Assumptions: Clean committed merges do not cover uncommitted behavior. Library main predates the 134-commit ontology refactor. API has an editable dependency; tools/media/harvesters exclude 1.x. Existing home images were built from dirty snapshots. GitHub/Docker Hub external triggers not verified. Preparation is documentation-only; inventory references pre-documentation hashes.

### Update 2026-11-03 19:33
- Decisions: Accept and deploy RC4 bounded BEGIN-only retry on home. No public signature, GraphDB, worker event, lease or uncertain-write semantics change.
- Implementation: Library retries explicit BEGIN 409 with fresh journaled IDs, at most five attempts and 50/100/200/400 ms backoff. Published isolated API/tools RC4 fingerprint e3903e70a220, stable/latest unchanged; bounded client playbook updated API/identity, retained Jena/Redis/data/policy and timestamped environment backup. Real contender test passes on both local architectures and isolated native home before/after replacement, with exactly one UPDATE and COMMIT. Public home checks pass; 30-story response equals RC3, fulltext/media unchanged, 3 IMPORTED/1 INVALID and no active claims, normal worker polling.
- Open: User may run a ZIP practice test. Persistent contention and other failures still surface normally; worker lease recovery remains a separate policy. The original unlogged validation callback cause cannot be proven retroactively.
- Risks/Assumptions: Explicit BEGIN 409 proves no admission; every other admission failure retains uncertain ownership and is not retried. No UPDATE/COMMIT replay. Tests: 61 library + 3 subtests, 54 API, 29 packaged transport; native acceptance used temporary separate data and cleaned its containers/storage. Two stale resource test doubles gained the existing resolved_properties method; no resource runtime change. Evidence: sibling setup docs/jena-begin-retry-rc4-home-results.json. Production and media image unchanged.

### Update 2026-11-03 19:01
- Decisions: Package bounded Jena BEGIN-only retries in RC4; preserve public APIs, worker leases and uncertain-write recovery.
- Implementation: Sibling library uses at most five fresh-ID admissions after explicit 409 only (750 ms total backoff). Added synchronized real-service contender acceptance to setup peer; no test data on home. Sixty-one library tests plus three subtests and 54 API import tests pass. Two stale SimpleNamespace resource test doubles now provide the existing resolved_properties method; runtime resource code unchanged.
- Open: Build/accept/publish RC4 fingerprint e3903e70a220, then bounded home update and native acceptance.
- Risks/Assumptions: Persistent writer contention can still surface normally; no retry of UPDATE/COMMIT, lost replies or HTTP errors other than BEGIN 409. No production or media image update.

### Update 2026-11-03 18:35
- Decisions: Deploy private-safe import 503 diagnostics; retain public contracts, validation rules and transaction/lease behavior. Distinguish proven current BEGIN contention from the unlogged historical validation callback failure.
- Implementation: Released/deployed RC3 fingerprint 55372bad3896 on home. Native diagnostic self-test and public auth/search/media checks pass; import states remain 3 IMPORTED / 1 INVALID. Actual post-update import claims logged OldapErrorAlreadyExists in transaction_start/_send (HTTP 409), later normal 204; export polling recovered to 200. Nine setup tests, 54 local import tests, 10 packaged audit/view tests and both-architecture transport/replacement/BEGIN-contention checks pass. Client update now retains a timestamped environment backup per run. Evidence: setup docs/jena-diagnostics-rc3-home-results.json.
- Open: Original 16:39 validation callback exception cannot be reconstructed from old logs. Next improvement should address explicitly refused BEGIN admission and/or exact-event result-publication retry while retaining heartbeat; uncertain UPDATE/COMMIT must never be blindly replayed. No retry behavior was changed in this diagnostic task.
- Risks/Assumptions: Five-minute stall is the persisted worker lease after failed publication. Current contention was observed immediately after client replacement and recovered without intervention. Publishing resumed after network interruption only after exact accepted OCI digest checks; existing tags were not overwritten, stable/latest before/after unchanged. A broader network-disabled packaged test needed Redis and failed only at its staging lock; its local Redis-backed test passed, and packaged diagnostics-only tests passed. No production or media image change.

### Update 2026-11-03 17:59
- Decisions: Release bounded import failure diagnostics without changing public errors or retry semantics. Historical callback exception remains unknown.
- Implementation: Added a real concurrent-BEGIN refusal assertion to disposable network acceptance; API logging regression suite has 21 passing tests. Preparing separate Jena RC3 for home only.
- Open: Complete release acceptance/publication/deployment and observe private-safe import errors; document whether admission contention occurs in practice. Keep existing user import records untouched.
- Risks/Assumptions: Five-minute delay follows worker claim expiry after failed result publication; simultaneous export/import transactions are a plausible trigger. No automatic replay of writes, shortening of leases or production change.

### Update 2026-11-03 17:44
- Decisions: Diagnose the stalled 18.6 MB home ZIP import without resubmitting, cancelling, changing validation policy or altering job state.
- Implementation: Read-only investigation confirmed upload HTTP 201 at 16:38:51 UTC; validation report completed at 16:39:02; first validation-result callback returned 503 at 16:39:04. Worker automatically reclaimed after its five-minute lease and published INVALID at 16:44:04. Verified retained report through the API record client including checksum: three PDF_NOT_PDFA_1_OR_2 and one TEXT_INVALID_UTF8; 15 packaging artifacts ignored. No application code or deployment changed. User confirmed earlier ZIP export browser download works.
- Open: First callback's transient 503 cause is unknown: the existing handler suppresses OldapError/RuntimeError detail. Investigate diagnostic logging and retry behavior before claiming this delay is fixed. The user can inspect the now-available report and correct files. Separate observed mobile lifecycle 503 reports missing/short service JWT configuration; not changed in this investigation.
- Risks/Assumptions: The long wait was not transfer or validation throughput. Automatic recovery completed during diagnosis. No records were imported; INVALID policy already removed temporary ZIP/extraction, retaining the report. No diagnostic write/transaction was executed; a proposed abort-only probe stopped before transaction start because recovery had already cleared the claim.

### Update 2026-11-03 14:54
- Decisions: Complete the existing stalled home export, without cancellation/recreation; keep worker JWTs and public/library signatures unchanged. Production and stable/latest image tags untouched.
- Implementation: Deployed narrow Caddy Jena-only matcher and API RC2 service-account access tokens. Separate API/tools AMD64/ARM64 images use fingerprint 95c8b339149f; bounded playbook updated identity/API only, preserving Jena storage/Redis/policy. Fixed network acceptance to use the independent identity sidecar and remove both consumers before namespace replacement. Existing worker claimed the original job and reached READY: 13 files, 12,724,905 ZIP bytes, CRC/integrity and SHA256 match; build ~0.37 s, claim-to-worker completion ~1.84 s. Evidence: sibling setup docs/jena-service-rc2-home-results.json.
- Open: User downloads the ready artifact in the browser; delivery itself has not been exercised as the owner. Full import/mobile workflows remain separate acceptance work. Frozen story hash differs; RC1 and RC2 read-only requests against current data return identical 30-story responses, so no exact frozen-source parity is claimed.
- Risks/Assumptions: Original delay was queue blockage, not ZIP compression throughput. Public login/upload-auth/fulltext/media/frontend checks pass; 43 focused API tests and both-architecture packaged transport acceptance pass. New access tokens stay inside API. Caddy recreation is required after atomic bind-file replacement; reload alone sees the old inode.

### Update 2026-11-03 14:42
- Decisions: Repair stalled home ZIP export without replacing/cancelling the user's queued job. Narrow proxy isolation to the Jena namespace; service-authenticated import/export/mobile routes must remain reachable. Keep GraphDB non-token service behavior; API-owned Jena service connections issue an internal transport token using existing API signing access.
- Implementation: Corrected Caddy matcher/template and added home proxy repair playbook; atomically replaced bind-mounted configuration requires Caddy recreation, not in-container reload of its old inode. Live unauthenticated export claims now return 401 instead of proxy 404; Jena callback remains blocked. Corrected four API service-connection constructors and added both-backend regression coverage (43 focused tests pass). Preparing new isolated RC2 API/tools images and a bounded home client-update playbook; no library API/signature or worker credentials changed.
- Open: RC2 build/accept/publication/deployment running; verify existing job reaches READY and ZIP integrity/download afterwards. Extend acceptance to worker-authenticated paths, not only public read/upload probes.
- Risks/Assumptions: Original job remained QUEUED, 13 files / 12,721,419 bytes, no attempt progress. Two independent blockers: broad /internal/* proxy rule and explicit issue_access_token=False incompatible with Jena. Production and normal image tags remain untouched; internal API tokens are never returned to media workers.

### Update 2026-11-03 14:18
- Decisions: User requested enabling archive structure management on home. Activate only Fasnacht structure policy using established ArchiveStructureEditor/ArchiveMediaEditor roles; do not enable the separate publication policy or assign users new roles.
- Implementation: Added reviewed structure-only policy, optional read-only Compose policy mount for API and future direct clients, and home-scoped enable playbook. Validated every referenced role/class/property against the live Jena model before activation, retained original environment, then recreated only API. Runtime capabilities report enabled/manage/create for admin, enabled but no manage/create for anonymous; user's existing structure role confirmed. Evidence: setup docs/jena-archive-policy-results.json.
- Open: User reloads archive management and exercises actual edits/creation in home testing. No test archive records were created and no end-to-end structure mutation is claimed. Production unchanged; direct writer release gates remain.
- Risks/Assumptions: Home had no OLDAP_ARCHIVE_POLICY_FILE, so the disabled message was accurate. Policy preserves existing data-level permission checks; role membership alone does not replace them. API, tools and harvester configuration share the read-only policy; only API runs/recreated. Fifteen focused setup tests and playbook syntax pass. Policy deployment and Jena overlay selection must be preserved on future updates.

### Update 2026-11-03 14:00
- Decisions: Synchronize the active API access-token verification key/issuer/audience to existing home media consumers after cutover rotation; never distribute refresh/admin secrets or introduce new access-token consumers.
- Implementation: Added shared home media-access tasks and a bounded repair playbook. Inventoried five environment files; only mediahelper-access.env contains the access key. Privately backed up and updated its three settings; Compose recreated the helper to load the new environment, other workers remained unchanged. First activation now synchronizes media before reopening and uses Compose recreation instead of docker start. Added valid/missing/invalid-token upload checks to the public acceptance runner.
- Open: User retries the real image upload. Acceptance intentionally omits project/file fields and verifies the exact form-validation response, proving authentication without creating data; it is not an end-to-end conversion/storage test. Production release/recovery gates remain. Any future full provisioning must use coherent signing keys for API, identity verifier and mediahelper.
- Risks/Assumptions: The initial activation rotated API access/refresh keys but omitted the media access verifier, causing HTTP 401 for newly issued valid tokens. Runtime verification settings now match exactly; media-token key and all images/data remain unchanged. Fresh admin-token upload reaches HTTP 400 Missing projectId field, missing/invalid tokens return 401. Full public smoke passes: 30-story digest unchanged, fulltext AND search, signed IIIF/JPEG and frontend availability. Evidence: setup docs/jena-media-access-results.json. No credentials/token bodies are retained in repository evidence.

### Update 2026-11-03 00:41
- Decisions: Accept the separate private identity pool after native home parallel/browser tests; retain access verification semantics and public API signatures. No data import, cache clearing, credential rotation or registry publication.
- Implementation: Home repair completed with oldap-jena-identity healthy on loopback 8001; API/backend/identity namespace recreated together and media resumed. Public smoke rerun passes including exact 30-story baseline, fulltext and signed image. Browser shows archive 665 media/422 objects/15 events and populated stories. Final parallel test: all 48 responses HTTP 200 at concurrency 16 and equivalent complete content. Updated lifecycle, templates, README, master context and evidence. Fourteen focused tests, four playbook syntax checks and both diff checks pass.
- Open: Production gates from the preceding activation remain. API workers can emit full list IRIs or equivalent QNames depending on loaded prefixes; deterministic serialization can be addressed separately. Native/non-container deployments must also avoid sharing a bounded public worker pool with callbacks.
- Risks/Assumptions: Initial strict parallel hashes differed solely for known list IRI/QName spellings; retained those reports and added property-scoped normalization using the frozen export's namespaces, with a regression ensuring changed resources/literal text are still detected. Successful evidence: setup docs/jena-concurrency-semantic-results.json and docs/jena-home-after-identity-results.json. Private callback startup works with network disabled; no admin/database secrets are distributed to it. Existing mobile shutdown delay remains unchanged.

### Update 2026-11-03 00:36
- Decisions: Isolate private identity callbacks from the public API worker pool; increasing public worker counts cannot remove the cyclic capacity dependency. Public API signatures, data and published images remain unchanged.
- Implementation: Added a minimal deployment WSGI entry point reusing the installed identity blueprint and TokenCodec, in a separate loopback-only container on port 8001 with only access-token/callback credentials. Updated Compose, preparation and activation lifecycle; added a coordinated home repair playbook and representative sequential/parallel archive acceptance runner. Added topology assertions; installed-image verifier passes with networking disabled.
- Open: Home repair is running; complete 16-way archive/story/taxonomy acceptance and browser verification, then record final evidence.
- Risks/Assumptions: Original 16-way Agent burst reproduced nine HTTP 503 responses at roughly 2/4 seconds while Jena remained running. Sequential initial cutover checks missed this capacity cycle. Namespace owner and all persistent consumers must be recreated together; no GraphDB rollback or data import is involved.

### Update 2026-11-03 00:30
- Decisions: Activate only home.org; retain GraphDB data/backups and preserve normal DockerHub tags. User-approved DATA_PERMISSIONS correction and inactive orphan memberships are applied. Rotate access/refresh keys; passwords are unchanged.
- Implementation: Completed two-host frozen backup and public Jena activation with pinned images. First private activation rolled back successfully after detecting missing explicit staging Redis configuration in the legacy Compose base; fixed API/tools/harvester settings, retested the exact base privately, then repeated freeze/backup and activated successfully. Removed stopped rehearsal containers/network, retaining all bind data. Added public acceptance runner and scalar-preservation regression; recorded sanitized evidence in setup docs/jena-home-results.json. Final 12 deployment/image/content-verifier tests and both repository diff checks pass.
- Open: Production-specific writer/harvester releases, reviewed mediahelper authorization fix, graceful mobile-worker shutdown, independent off-host backup/restore and coordinated Jena routine updates. Canonical ontology cleanup and other projects' fulltext field inventory remain separate. No production deployment or Git commit/push.
- Risks/Assumptions: Final source SHA matches rehearsal; 65,376 target application quads, 16 users; synthetic write-test user removed. All 30 story responses match GraphDB; fulltext AND search yields 10 equal hits in either word order; real login, signed IIIF/JPEG and frontends pass, local HTTPS status passes. New verifier initially dropped scalar values; corrected and exact baseline hash now matches. Source GraphDB had no fulltext connectors, so no fulltext parity claim. Backup directories dated 20261103 on API/media; earlier 20261102 copies retained. Mobile worker required forced stop after 90s with no queued operation files; all media workers now run. Reopened target writes prevent blind GraphDB rollback.

### Update 2026-11-03 00:01
- Decisions: User selected DATA_PERMISSIONS for the duplicate WriterRecoveryOperator default; four orphan annotations remain inactive. Preserve the original source export. Target API rotates access/refresh keys at cutover so stale claims cannot survive.
- Implementation: Added target-only guarded SPARQL correction and applied it to the candidate. Corrected Redis durability to appendfsync=always/noeviction after the library rejected default configuration. Candidate API create/login/update/delete acceptance passes; synthetic user removed. Added home-only freeze/backup and rollback-protected activation playbooks; documented operator sequence.
- Open: Media backup is running with source API/GraphDB/Redis and media writers stopped; activate only after successful two-host manifest. Final public endpoint/media verification and production-specific release/update gates remain.
- Risks/Assumptions: Final frozen RDF hash equals the initial source export exactly. Source coordination DB 1 empty; two imports IMPORTED, one export DELETED; no application timers found. Jena and GraphDB story responses match (30). Source GraphDB has zero Lucene connectors; Jena has nine configured fields and positive search results, so no fulltext parity claim. Installed mediahelper auth functions differ from reviewed local fixes; media release acceptance remains a production gate.

### Update 2026-11-02 23:45
- Decisions: Prepare and rehearse full source data on home.org before replacing its public GraphDB API; user authorizes stopping GraphDB there after readiness.
- Implementation: Prepared /srv/storage/oldap-jena-home-20261102 with verified release/service keys and digest-pinned images. Added isolated rehearsal overlay/playbook: own Redis/data/API, localhost:18000 only, no public route changes. Fixed copied launcher permissions explicitly to 0755. Added read-only account/project/model parity command; five Compose/deployment tests pass.
- Open: Resolve one account role-map discrepancy and four orphan membership annotations with user. Complete canonical model/data migration, source freeze/backup, writer/media recovery and coordinated public activation.
- Risks/Assumptions: Source stack unchanged. Candidate full API/Jena/Redis running; initial import is a live-read rehearsal. Failed initial startup was launcher mode, corrected; partial Ansible resume then stopped at undefined build fact after applying chmod, original copied artifact hashes were already verified. Resume of rehearsal startup succeeded. Credentials not written to repository or command arguments.

### Update 2026-11-02 23:25
- Decisions: Separate Jena RC image workflow is the only publication path in migration checkouts; normal registry tags and latest remain untouched.
- Implementation: Added allowlisted source snapshots, source-matched local wheels, staged local package versions, digest-pinned runtime, per-architecture builds, installed-image acceptance and guarded no-rebuild publication. Candidate Compose/Ansible require explicit API/tools digests. Recorded workflow and published references in README.md and docs/jena-images-results.json.
- Open: Full API startup with real accounts/data, migration and coordinated activation/update; harvester release remains separate. Preserve source snapshots because these checkouts contain uncommitted work.
- Risks/Assumptions: Ten publication/deployment tests, wheel inspection, both-architecture imports/dependency/CLI/UID checks and packaged real-Jena transport acceptance pass. Published API digest also passes on native x86_64 api.home.org. Registry multiarch indexes verified; current normal version/latest digests unchanged. Initial candidates superseded to preserve runtime UID contracts; only final c1cb0919375a candidates published. Existing GraphDB/API unchanged; owned test resources removed. No Git/PyPI publication. Evidence: oldap-setup/docs/jena-images-results.json.

### Update 2026-11-02 22:58
- Decisions: Dedicated migration/jena checkout under OLDAP-Jena, based on local main 938f7ed plus inherited uncommitted working-tree changes; original checkout untouched. Jena owns a private shared network namespace; API/tools/harvesters join it, preserving the API bridge alias.
- Implementation: Added opt-in Compose overlay, private config templates, new-candidate-only Ansible preparation and Make targets. Removed only GraphDB dependencies, preserving writer health/policy. Proxy rejects /internal/*; legacy provision/reset refuse selected Jena. Added network acceptance runner, real identity-route fixture, merge/template/proxy checks and production migration/lifecycle instructions in README.md.
- Open: Matched immutable application/direct-writer releases, full API startup and source/account/media migration, writer fencing/reconciliation, coordinated activation/update automation and production acceptance. Preparation playbook not executed remotely; candidate env must not replace installed .env.
- Risks/Assumptions: Both local ARM Docker and x86_64 api.home.org pass real callback/transaction/isolation and namespace-replacement checks, including persisted data before the next write. Nine configuration/writer tests and three Ansible syntax checks pass. Fixture PID 1 now handles SIGTERM; inherited API expose metadata is reset. Final local/remote runs repeated with this merge correction. Owned test resources/uploads removed, existing GraphDB/API continue running; Java runtime image cached. No source/production data, installed configuration or endpoint changes. Evidence: docs/jena-network-results.json.

### Update 2026-10-26 23:09
- Decisions: Make harvesting launchers independent of the caller working directory.
- Implementation: Use absolute COMPOSE_FILE paths; --project-directory alone does not anchor relative environment-provided paths. Added a regression invoking real Compose configuration from another directory for both sources, including an overridden .env selector. Ten focused scheduling/Compose/update tests, shell syntax and diff checks pass; no import or mail sent during tests.
- Open: Rerun make install-harvest-schedule-vm to replace the deployed launcher and finish activation.
- Risks/Assumptions: First installation stopped at CLI preflight, before service/drop-in/timer installation and enablement. Existing configuration and data are preserved on retry.

### Update 2026-10-26 23:06
- Decisions: Add opt-in VM-only Sunday 05:00 Europe/Zurich harvesting; serialize backup and per-source jobs on one local-filesystem lock, and email separate concise source summaries using the backup's existing mail transport/addresses.
- Implementation: Added first-install playbook/Make target, shared installation/update tasks, systemd service/timer, source launcher and lock overlay, inherited-fd lock wrapper and sequential reporting script. Backup script/env/timer remain unchanged; a service drop-in wraps ExecStart. Manual Swisscovery delegates to shared locking after installation. Existing deployed image/config versions are reused; routine deploy maintains installed scheduling without enabling paused timers. Versioned private per-source logs remain on VM; missing summaries/nonzero exits/mail failures fail the cycle without suppressing the second source.
- Open: Operator must run make install-harvest-schedule-vm with sudo password; no timer or backup service configuration was activated. No real report email sent yet. Future manual backup runs must use systemctl rather than executing the script directly.
- Risks/Assumptions: Direct Compose/ad hoc launches bypass coordination. Lock is shared only between cooperating backup/harvesting jobs, not ordinary interactive writers. Local Linux filesystem and existing root containers required; installer checks idle jobs and current backup command. Persistent timers can catch up missed runs. Nine focused tests plus both Ansible syntax checks and shell syntax pass. Real VM test with deployed 0.1.13 image confirmed container-to-host lock exclusion across exec and release after container stop; isolated test container/temp files cleaned. VM calendar confirms next regular run 2026-11-01 05:00 CET. Mail success means local transport acceptance, not confirmed inbox delivery.

### Update 2026-10-26 21:17
- Decisions: Report missing first-install input files explicitly rather than failing silently.
- Implementation: Added actionable Make preflight diagnostics; created the user's private installation input file from the documented approved VM paths/model checksum without credentials.
- Open: User reruns installation; no VM changes performed.
- Risks/Assumptions: Remote input paths and published OCR tag remain subject to installer validation.

### Update 2026-10-26 00:20
- Decisions: Integrate the OCR image into normal releases and serialize Swisscovery batches on the production VM without adding a scheduler.
- Implementation: Added explicit Swisscovery Compose override/launcher, approved-input installer and routine release preflight. Inherits installed writer configuration, keeps Europeana defaults, stores config/model/reports/lock persistently and limits CPU/RAM. Shared flock covers complete run; exit 75 on overlap. Added Compose merge and Docker overlap/crash-release tests. Validation: 36 setup tests pass plus the separately enabled Docker overlap/TERM/KILL test; both Ansible syntax checks and package-version check pass. Complete amd64 image builds on Mac and natively on the VM; CLI and actual production Kraken model load pass natively. OCR dependency inventory exactly matches the successful production image. Local model execution encountered a QEMU segmentation fault; native checks pass. VM lock filesystem confirmed ext4. Removed only this verification image and its 14 newly created cache records from the VM after testing.
- Open: Publish a new immutable release pair and run the first-install playbook on the VM. No registry publication, production activation, import or scheduler changes performed.
- Risks/Assumptions: Batch lock requires a shared local Linux filesystem on one host; macOS file sharing does not provide equivalent flock behavior. Ad hoc launchers/entrypoint overrides bypass it. Existing imported data, ontology and selection rules are unchanged.

### Update 2026-10-01 11:50
- Decisions: Accept user-deployed project-identity optimization on the VM; retain four workers/two threads.
- Implementation: Recorded deployed API 0.2.31 / oldaplib 0.7.25 source verification and read-only before/after evidence; updated context and relevant performance/worker documentation. No application code or deployment configuration changed.
- Validation: 1,152 timed reads pass; all 17 baseline contents and public HTTPS checks match. Resource medians improve 10–13%, summaries 4–10%. At 16 readers: median/p95 167/591→143/559 ms, API CPU 1.78→1.57 cores. Existing 50,396-binding RDF fingerprint, containers and service PIDs unchanged; temporary VM files removed.
- Open: Larger representative data and sustained mixed-user sizing remain separate; no worker maintenance indicated by this workload.
- Risks/Assumptions: One sequential short warm anonymous comparison, not maximum capacity. Search/fresh-model gains not demonstrated; recovery p95 varies upward. Separate final verifier excludes the completed load-client process; within-run service-process guard passed. Existing local changes preserved.

### Update 2026-10-01 00:27
- Decisions: Retain four workers/two threads after successful measurement of the user-deployed serializer optimization.
- Implementation: Documented API 0.2.30 / oldaplib 0.7.24 runtime/source verification and linked accepted VM before/after evidence; preserved existing local documentation edits.
- Validation: Complete rerun passes 1,132 timed reads and public HTTPS checks; all 17 references and the 50,396-binding RDF fingerprint match. Median/p95 at 16 readers: 232/649→167/591 ms, API CPU 2.13→1.78 cores. Containers/PIDs unchanged; temporary VM files removed.
- Open: Local Project/model-copy profiling; no worker maintenance needed for current findings.
- Risks/Assumptions: First attempt excluded after transient helper processes triggered the old sampler guard; corrected sampler has 19 passing offline checks and a successful complete rerun. Short warm anonymous workload, not capacity/HMB sizing. No infrastructure/configuration change or data write during measurement.

### Update 2026-09-30 23:30
- Decisions: Record read acceptance of the user-deployed API without changing workers, configuration or existing data.
- Implementation: Updated Docker worker documentation/context with VM baseline and linked the API repository's reproducible Linux/Docker read tooling and reports.
- Validation: 2,409 successful timed reads across exact-reference/full-batch runs; full batches at 16 readers reach 16.13 requests/s and 649 ms p95. Unchanged 50,396-binding RDF fingerprint, container identities and service PIDs; public HTTPS read checks pass; temporary VM directory removed.
- Open: API/library per-request CPU profiling; controlled worker-count comparison and isolated release-image write/recovery rehearsal remain separate.
- Risks/Assumptions: Short closed-loop warm anonymous reads on current data; no pre-deployment VM baseline, HMB sizing or Enterprise/async conclusion. No deployment, restart, cache flush or RDF update performed during these measurements.

### Update 2026-09-30 01:15
- Decisions: Keep native laptop single-process; expose Docker worker tuning without silently changing existing 4-worker/2-thread defaults. Reuse and validate existing container-level recovery rather than redesigning it.
- Implementation: Added bounded Ansible worker/thread variables, rendered Compose settings, shared preflight and explicit installed-config maintenance playbook. Extended isolated Docker probe with current real API/library sources, worker SIGKILL/replacement, all-worker gate checks, fresh-container recovery and post-finish commit. Documented maintenance, cache lifecycle, limits and acceptance evidence.
- Validation: 34 setup tests and both playbook syntax checks pass. Final source-verified 2/4-worker Docker probes pass all recovery/rollback/preservation/commit checks; no core recovery library changes. Preliminary fixture issues (legitimate contention and bundled-source precedence) corrected before acceptance.
- Open: Build and rehearse the actual release image; perform controlled 2/4-worker measurements on the eight-vCPU VM. Configuration changes require the existing stopped-writer maintenance boundary.
- Risks/Assumptions: No deployment or production credentials used. Tests own isolated GraphDB 11.3.0/TLS Redis/cache and synthetic marker transactions; not full business-operation or distributed-failure coverage. Existing unrelated SALSAH changes remain intact. Runtime source assertions prevent accidentally testing the dependency image's older API.

### Update 2026-09-27 23:43
- Decisions: Preserve the deployed mobile-media feature selection during the SALSAH CORS rollout; do not infer activation from the host default.
- Implementation: Corrected the guide to explain the production mobile=true inventory override, the previously documented false rollout override, safe JWT-preflight troubleshooting and the conditional deployment command.
- Open: Confirm current production mobile-worker state and which Vault validation fails; read-only SSH Docker inspection required interactive sudo and could not complete.
- Risks/Assumptions: No secrets read or changed; no deployment performed. The 2026-09-11 rollout log is historical evidence, not confirmation of current runtime state.

### Update 2026-09-27 23:21
- Decisions: Make SALSAH deployment instructions explicit about repository, machine and workflow scope.
- Implementation: Expanded the guide with repository/path and environment tables, ordered release/install commands, registry examples, update boundaries, acceptance checks and rollback limitations; checked targets against current Makefiles/playbooks.
- Open: Release publication and production acceptance remain separate operational steps.
- Risks/Assumptions: Documentation only; no code, deployment configuration or server state changed. Example release tags must be replaced with reviewed published versions.

### Update 2026-09-27 23:08
- Decisions: Preserve existing deployments; add trusted server-owned mail destinations and opt-in SALSAH installation.
- Implementation: Added optional SALSAH Compose overlay, explicit first-install targets, shared frontend-only update tasks and conditional combined updates. Existing hosts remain opt-in. See docs/salsah-deployment.md.
- Open: Publish immutable compatible releases; perform coordinated initial installation and real DNS/TLS/browser/SMTP acceptance.
- Risks/Assumptions: No server deployment or image publication performed. Initial configuration requires an API restart; frontend-only updates do not.
- Validation: 31 deployment regression tests and Ansible syntax checks passed. Synthetic Compose merge validated; no SSH, provisioning or production execution performed.

# CODEX_LOG

### Update 2026-09-15 01:13
- Decisions: Preserve accepted production publication configuration in the authoritative local deployment input.
- Implementation: Backed up private writer-production/archive-policy.json, added the reviewed publication definition, validated with oldaplib 0.7.20 and verified all other fields unchanged. Confirmed deployment-vars.yml references this file. Updated activation evidence and master context.
- Open: User Git commit for tracked documentation; retain private configuration backup. No further deployment needed for this synchronization.
- Risks/Assumptions: Remote activation/285 visible records evidenced by user output and acceptance; remote full policy not byte-compared. No production writes or secrets committed.

### Update 2026-09-15 00:55
- Decisions: Verify running services and actual host policy mount before production publication activation.
- Implementation: Recorded supplied version/capability evidence and source references in docs/publication-activation-status.md.
- Open: Host mount, running-image checks, coordinated activation and acceptance.
- Risks/Assumptions: One-off image checks do not establish the running API image or identical host policy mounts; no server changes.

### Update 2026-09-15 00:45
- Decisions: Harvester creates private drafts before controlled publication.
- Implementation: TOML template now grants ArchiveMediaEditor DATA_UPDATE; removed generic Editor write and Unknown public grants. Matching harvester release uses generic publication inside the creation transaction.
- Open: Existing VM TOML must be updated separately; routine deployment preserves configuration.
- Risks/Assumptions: Configured account needs publisher membership; no live server changes.

### Update 2026-09-15 00:30
- Decisions: Provide the harvester with the installed access-token signing configuration required by direct oldaplib login.
- Implementation: Compose harvester environment now forwards the access secret, issuer and audience; no additional token secrets exposed.
- Open: Apply the same service configuration to the existing VM; routine version deployment does not copy Compose files.
- Risks/Assumptions: Secret values remain in installed configuration; no secrets printed, no server action or import executed.

### Update 2026-09-15 00:25
- Decisions: Match the harvester configuration to its all-pages CLI contract.
- Implementation: Removed unsupported default_max_pages from the provisioning template; retained page size and query filters.
- Open: Existing VM configuration needs the same one-line removal; routine deploy-vm intentionally preserves installed configuration.
- Risks/Assumptions: New harvester retrieves every result page. No live server changes or harvesting executed here.

### Update 2026-09-11 23:30
- Decisions: Separate routine application releases from infrastructure provisioning. Preserve authoritative installed secrets/Writer settings instead of re-rendering them from potentially stale local files.
- Implementation: deploy-vm now invokes oldap-update.yml; explicit image validation/pull, installed-overlay check, API/tools/harvester store preflights before tag writes, private configuration backup, application-only no-dependency update and API readiness. Added Make comments and routine update guide. Five update/preparation tests pass (including mocked Make dispatch and real Ansible guard test); Ansible syntax and git diff checks pass.
- Open: First real routine update has not been executed. User commits the deployment changes; review make show-versions, especially retained production oldap-app v0.2.4 versus local tags.
- Risks/Assumptions: Existing migrated production installation required. Finish active work before update; running tools/harvester jobs are not replaced. No automatic rollback after partial failure. Default system Python lacked test dependencies; tests passed in the existing API Poetry environment. No server mutation, deployment, secret rotation, ontology or frontend changes.

### Update 2026-09-11 02:29
- Decisions: Accept media service deployment/basic endpoint checks; keep end-to-end acceptance and backup resumption outstanding.
- Implementation: User deployment recap ok=41 changed=8 failed=0. Helper/ingest/export use v0.2.11 and both worker-running assertions pass; image server remains v0.2.1. Mobile worker is created but not running. Independent public curl checks with certificate verification: API v0.2.23 /health 200, mediahelper 0.2.11 /health 200, unauthenticated IIIF probe 401.
- Open: Ordinary-user archive UI, image delivery and small ZIP export acceptance; resume oldap-backup.timer after acceptance. No native CaptureApp changes or SALSAH-2 deployment.
- Risks/Assumptions: Media container state evidenced by deployment output (Docker requires sudo); public endpoints independently checked. Local Python default trust store failed, system curl verified TLS successfully without bypass. Basic health is not full workflow acceptance.

### Update 2026-09-11 02:23
- Decisions: Accept first API-VM activation after successful deployment and live checks; keep media rollout and backup resumption separate.
- Implementation: User activate-vm recap ok=67 changed=1 failed=0; installed-operator/storage checks, API health and export-service authentication passed. Fresh SSH confirms API v0.2.23 healthy, FasnachtsPage v0.1.37 running, writer healthy, oldap-app v0.2.4 retained and GraphDB uptime unchanged. Public API /health returns ok/v0.2.23; backup timer remains inactive.
- Open: Deploy mediahelper/ingest/export workers v0.2.11, verify cross-service and ordinary-user archive workflows, resume backup timer after acceptance. SALSAH-2 remains excluded from deployment.
- Risks/Assumptions: HTTP availability and service login are not complete archive/export/browser acceptance. Media services remain stopped per prior confirmation.

### Update 2026-09-11 02:19
- Decisions: Provide an explicit first-activation Make target that retains private writer/Vault inputs and avoids full-stack/dependency startup.
- Implementation: Added activate-vm sharing preparation inputs; activate phase requires coordination/recovery and bootstrap=false, skips Docker provisioning, checks stopped writers and installed operator, then starts only API/oldap-app/FasnachtsPage with dependencies=false and no orphan removal. Reuses API health/export authentication checks. Fourteen tests, Ansible syntax and Make dry-run pass; actual activation preconditions passed read-only on production (changed=0).
- Open: User executes activate-vm with reviewed pins; inspect health/auth, deploy mediahelper/workers, perform acceptance and resume backup timer.
- Risks/Assumptions: No applications started in this turn. Activation is maintenance-only and rejects a retry with running writers; diagnose partial startup first. Production-specific operator check uses the verified VM config image ID and installed root-only configuration.

### Update 2026-09-11 02:16
- Decisions: Accept production recovery operator installation after successful read-only target checks.
- Implementation: User installer output verifies inventory, operator TLS/durable storage, Docker access, stopped writers, running GraphDB and no gate/recovery barrier; recoveryExecuted=false. Removed exactly the seven expected temporary user-owned install files and empty staging directory on VM. Protected root installation and local private master material retained.
- Open: Coordinated application/media activation with current writer settings and pinned releases; public/API/ordinary-user acceptance, then backup timer resumption.
- Risks/Assumptions: Root verification evidenced by user-supplied installer output. No production recovery drill, database restart or service activation performed. Reinstallation requires restaging the protected bundle.

### Update 2026-09-11 02:14
- Decisions: Install the tested standalone operator without initiating recovery or restarting GraphDB.
- Implementation: Transferred reviewed image to production. Resolved Desktop manifest-ID versus classic-store config-ID difference using export manifest and exact Config/RootFS/OS/architecture comparison; production immutable config ID 7319daf2…16dac. Docker CLI/daemon handshake 29.8.0/29.6.2 passed. Added guarded installer and read-only checker, four checker tests plus two recovery deployment tests pass; shell syntax checked. Private checksummed 0700/0600 bundle staged in VM user home with only operator credential config/public CA, no CA/server keys.
- Open: User sudo installation and target read-only verification; remove staging credential copies after success; coordinated application/media activation and acceptance.
- Risks/Assumptions: Image loaded but operator not invoked; root configuration not yet installed. No gate mutation, database restart or service activation. Installation may leave installed files if final checks fail; differing existing credentials are never overwritten.

### Update 2026-09-11 02:10
- Decisions: Accept production archive migration after independent explicit SELECT verification.
- Implementation: User-run migration reports all checks true, 363 resources/478 changes and two Shared additions. Independent live queries match exact final ACL plan, resource scope, existing roles/memberships/admin grants; verify both archive roles for four reviewed users and recovery role only for rosenth, including hasDefaultDataPermission annotations. Both new properties optional; defaultArchiveUnit maxCount=1, references unbounded. Private verification report saved in BACKUP. Fresh Docker/timer check: writer healthy, API stopped, timer/service inactive, migration container removed.
- Open: Install and verify production recovery operator, coordinated application/media activation and acceptance, then resume backup timer.
- Risks/Assumptions: No additional writes during verification. Initial verification query used resource permission predicate for user membership; corrected to hasDefaultDataPermission, final checks pass. Media metadata/protected graph preservation is evidenced by migration transaction checks; no whole-host rollback or public UI acceptance claimed.

### Update 2026-09-11 02:05
- Decisions: Use a reviewed one-off production migration with exact-plan/release checks, resumable model/role phases and atomic resource ACL update under the durable gate.
- Implementation: Added migration/check/runner modules and operator documentation in FasnachtsPage docs/production-rollout; isolated restore/migrate/retry harness in oldap-setup tests. Final production-backup rehearsal passes all 478 changes/363 resources, two Shared additions, memberships, preserved media metadata and protected model/list graphs; exact second run adds no properties. Four review-drift tests and four planner tests pass; Python/shell syntax checked. Fixture cleanup verified. Credential-free checksummed bundle staged in API VM user home; normal API-image user can read/import it with networking disabled.
- Open: User executes sudo migration runner using existing protected Compose credentials; then live-state verification, recovery operator installation and coordinated activation. Production graph data unchanged in this turn; outage remains active.
- Risks/Assumptions: Initial isolated trials exposed container import/QName/project-IRI comparison issues, corrected before successful full retry. Role/model phases commit separately; uncertain failure requires inspection/recovery, never automatic gate reset. Private evidence in BACKUP/production-migration-rehearsal.json. No media/CaptureApp/frontend runtime changes or Git commits.

### Update 2026-09-11 01:49
- Decisions: Accept successful production preparation and revoke first-bootstrap permission in private deployment inputs.
- Implementation: User play recap: ok=61 changed=15 failed=0. All three writer image storage probes passed, stack startup skipped, final stopped-writer guard passed. Fresh SSH confirms archive-writer healthy, API Exited (0), GraphDB continuously running and backup timer/service inactive. Set external oldap_writer_bootstrap=false; existing owner/AOF guards retained.
- Open: Minimal model/role/ACL migration, separate operator installation, coordinated application/media activation and acceptance. No normal deploy yet.
- Risks/Assumptions: Production maintenance remains active. Prepared configuration is installed but old frontends still running; archive API is not released. Redis provisioning is complete, not application migration.

### Update 2026-09-11 01:46
- Decisions: Fix actual Ansible template escaping before retrying preparation; prior plain-Jinja regression coverage was insufficient.
- Implementation: Replaced escaped nested string with unescaped Docker template assembled in a YAML block scalar. Added real Ansible subprocess regression with fake Docker argv validation, accepting idle infrastructure and rejecting active API. Read-only production include-task run passed (changed=0); ten deployment tests and playbook syntax pass.
- Open: Retry make prepare-vm with reviewed version pins, inspect successful provisioning, disable bootstrap, migrate model/roles/ACLs and activate.
- Risks/Assumptions: User's failed deployment stopped in the first read-only guard (changed=0). Production services remain in maintenance; no provisioning performed by this fix.

### Update 2026-09-11 01:44
- Decisions: Enable reviewed private production writer inputs for first provisioning during active maintenance; preserve oldap-app v0.2.4.
- Implementation: Verified TLS hostname/chain, encrypted Vault marker, private file permissions and operator inventory digest. Locally enabled coordination, compatible-release, recovery and first-bootstrap flags in external deployment-vars.yml. Nine deployment tests and Ansible syntax check pass. Prepared make prepare-vm invocation with explicit release pins.
- Open: User executes Ansible with Vault/become passwords; verify resulting writer health and stopped clients, then disable bootstrap permission. Model/role/ACL migration and operator installation remain pending.
- Risks/Assumptions: No server provisioning executed in this step. Recovery configuration may be installed before its role exists, but API remains stopped. Bootstrap is restricted by the existing provisioning-marker/AOF guards.

### Update 2026-09-11 01:43
- Decisions: Capture final pre-migration database snapshot after coordinated application shutdown.
- Implementation: User stopped API and backup timer; fresh read confirms backup timer/service inactive and only frontends/Caddy/cache/GraphDB running on API VM. User output confirms no per-user cron files. Final full backup with system data stored privately as BACKUP/oldap-production-pre-migration-2026-09-11_01-42-41.tar; archive readable, success marker/system components verified, SHA-256/report retained.
- Open: Writer configuration preparation, minimal model/role/permission migration, coordinated activation and acceptance. Resume media helper/workers, API and oldap-backup.timer only at the coordinated step.
- Risks/Assumptions: Production outage active; no model/data edits yet. Manual/external GraphDB clients are not fenced. Earlier snapshot restore tested; final snapshot archive-validated only. Media services remain stopped per user report.

### Update 2026-09-11 01:41
- Decisions: Preserve retained import evidence and export files after media services stopped.
- Implementation: Downloaded oldap-media-records-6aDCbSM8.tar.gz into private local BACKUP; 10 entries/6 regular files, 23,066 bytes; fully readable, both required directories present, server/local SHA-256 match. Checksum and report retained alongside archive.
- Open: API/timer maintenance and remaining writer checks, final GraphDB backup, migration/activation.
- Risks/Assumptions: Media writers remain stopped per prior user confirmation; API still live. This filesystem backup does not replace the final GraphDB job-state snapshot.

### Update 2026-09-11 01:40
- Decisions: Begin coordinated media-writer maintenance after backup preparation.
- Implementation: User stopped oldap-ingest-worker, oldap-export-worker and oldap-mediahelper on media VM; all report Exited (0). Caddy/imageserver remain running. Pre-stop GraphDB sample showed two IMPORTED jobs and three DELETED exports. Use Docker --timeout instead of deprecated --time in subsequent commands.
- Open: Back up retained import records/export directory, pause API backup timer and remaining writers, final quiescent GraphDB backup, migration/activation. API still running; global maintenance is not yet established.
- Risks/Assumptions: Media service stop verified from user-supplied output, not a fresh privileged query. No forced kill reported. Keep stopped services down until coordinated restart.

### Update 2026-09-11 01:37
- Decisions: Preserve media VM configuration before coordinated maintenance.
- Implementation: Downloaded user-created oldap-media-config-8jRnAiR8.tar.gz to local BACKUP with mode 0600. All 30 archive entries readable; required Compose/Caddy and four service env files present; Caddy configuration/state included. Server/local SHA-256 match; report and checksum stored privately beside archive. User confirms separate media copy on university computer.
- Open: Maintenance/drain of writers, retained import records/job-state coverage, migration and coordinated activation. Media copy freshness/restore not verified; root cron on API VM still unchecked.
- Risks/Assumptions: No service changes. Configuration archive excludes media and import records; no sensitive values printed. Server copy retained.

### Update 2026-09-11 01:30
- Decisions: Inspect media backup coverage and schedulers before pausing writers.
- Implementation: Read-only inspection of both VMs: API/app data directories currently contain no regular files; archived directory structure locally with checksum. Media root is 18 GiB; latest visible manual archive is 2026-08-11. No rosenth crontab on either VM; visible system timers include API oldap-backup at 03:15, no media backup timer. Existing media runbook documents external daily university backup; requested actual scope/success/restore evidence from user.
- Open: External backup confirmation, privileged cron/container/job inspection on media VM, protected media configuration backup, maintenance/migration/start.
- Risks/Assumptions: No service changes. Absence of a VM timer does not disprove hypervisor-level backup. Root/other-user schedules not yet inspected. API data copy was online and empty at inspection, not a fenced snapshot.

### Update 2026-09-11 01:28
- Decisions: Preserve production configuration before maintenance; user performed sudo archive creation.
- Implementation: Downloaded oldap-config-eIiJInLI.tar.gz into private local BACKUP files (0600); read all archive members, verified required Compose/env/Caddy/backup files and GraphDB/Caddy/harvester directories. Local/server SHA-256 match; 66 entries, 240,908 bytes. Checksums and verification report saved alongside archive.
- Open: Media/upload backup coverage, complete scheduler/external-writer inventory and controlled maintenance/migration/start.
- Risks/Assumptions: No service changes. Configuration archive is not a full host/media backup; server copy retained, sensitive contents never printed.

### Update 2026-09-11 01:24
- Decisions: Validate actual backup restoration before production maintenance.
- Implementation: Restored full 01:22 production backup with system data into network-isolated GraphDB 11.3.0, no host ports; queried 14 named graphs/40,782 explicit triples, matched read-only production sample, restarted and rechecked. Disposable container/volume removed; private evidence saved beside backup.
- Open: Protected deployment configuration/media backup, scheduler/writer maintenance, migration and activation acceptance.
- Risks/Assumptions: Production unchanged. Counts verify structural completeness, not bytewise RDF equivalence, user login or application/media behaviour. Restore used local test license.

### Update 2026-09-11 01:17
- Decisions: Separate existing-host configuration preparation from application startup during production migration.
- Implementation: Added guarded prepare phase/Make target loading both private input sets; Docker provisioning and normal startup/HTTP checks skipped; service display now read-only. Compose-label checks before/after preparation reject active writers. Added sequence/limits documentation and two regression tests; nine deployment tests and Ansible syntax check pass.
- Open: Production backup/restore verification, maintenance, private flag review, migration execution, operator installation and coordinated activation/acceptance.
- Risks/Assumptions: No production changes. Checks require external schedulers/writers and manual restarts to remain quiescent; preparation is not an atomic fence. Failed preparation can leave changed configuration. oldap-app retained at v0.2.4 in documented command.

### Update 2026-09-11 01:10
- Decisions: Verify encrypted private input and rehearse actual Docker operator fencing before production installation.
- Implementation: Vault header/mode verified without decryption. Added isolated GraphDB/TLS Redis probe and container client; real open transaction rolls back, committed marker survives, writer removed, barrier enforced, evidence/finish retry and subsequent acquisition pass. 24 recovery tests plus six subtests pass; Black/diff checks pass. All owned fixture resources removed.
- Open: Controlled Ansible preparation/migration/start boundary, production installation and target backup/restore/acceptance. Evidence/limits in operator/rehearsal-2026-09-11.json.
- Risks/Assumptions: Initial unlicensed fixture was rejected and cleaned; successful run mounted existing local test license read-only. No production state/credentials used, no VM reboot or public HTTP/UI acceptance claimed.

### Update 2026-09-11 01:01
- Decisions: Prepare private production TLS/ACL inputs outside Git and a separate socket-authorized operator container; leave actual deployment disabled.
- Implementation: Added no-overwrite private generator, pinned operator Dockerfile and hostname/image/config-guarded launcher. Generated private material locally, validated chain/SAN, permissions, distinct credentials and library inventory digest. Built amd64 operator; CLI/help/Docker handshake, shell syntax and seven writer deployment/recovery tests pass.
- Open: User Vault encryption, full isolated operator fencing rehearsal, phased deployment, production installation and migration. Operator image ID and limits recorded in operator/README.md.
- Risks/Assumptions: No production changes or secrets in Git. Socket authority is exclusive to manual operator. One-year leaf certificate requires renewal; private CA stays off server. No publication or commit.

### Update 2026-09-10 12:10
- Decisions: Complete WR-04 local operational acceptance; enable only the explicitly authorized rosenth operator. Production remains a separate target-specific rollout.
- Implementation: Added native service entry points, startup refusal tests and real isolated GraphDB/native writer fault/restore probe. Production inventory and templates remain unchanged in WR-04. Acceptance: 50 recovery/native, 19 deployment, 49 authentication/Capture transport and 8 frontend tests pass; 10 native and 15 pinned Redis checks pass. Both live/fixture UI flows and builds pass; FP typecheck baseline remains 23 errors/37 warnings, SALSAH is clean.
- Open: Production multi-host/SSH partition, whole-host reboot and independent-storage restore acceptance; native Capture acceptance retains the user's local waiver.
- Risks/Assumptions: Native services must remain foreground and within the reviewed inventory; unmanaged direct writers are maintenance-only. Persistent controller/gate state never expires. No commit, push or production deployment.

### Update 2026-09-10 01:05
- Decisions: Separate normal writer, recovery API and offline operator Redis ACL identities; operational evidence is read-only to the API.
- Implementation: Added optional recovery credentials/role/inventory digest validation across members, API-only secret injection and restricted ACL selectors for Lua key checks. Added deployment tests and detailed offline Docker/SSH maintenance procedure; extended pinned runtime probe for evidence-denial/audited retry.
- Open: Explicit reviewed inventory, compatible rollout and WR-04 target rehearsal/native MacBook control are required before enabling recovery. Operator secrets/configuration remain outside application containers.
- Risks/Assumptions: 16 deployment/auth tests, syntax check and all 15 pinned Redis runtime checks pass; backend suite adds 51 checks. No real inventory, remote deployment, application RDF or running recovery changed. Existing WR-01 and ontology changes preserved.

### Update 2026-09-10 00:40
- Decisions: Complete WR-01 deployment implementation with explicit one-owner/member topology; keep existing environments disabled until coordinated rollout. Use TLS even internally and reject empty-state recreation after provisioning.
- Implementation: oldap-setup adds guarded AOF bootstrap, pinned Redis service/ACL/health, private Docker forwarding firewall, shared policy/endpoint/GraphDB configuration and image preflight for API/tools/harvesters. Deployment contract markers reject accidental disablement/retargeting. Documented raw/model migration bypasses and operator procedure. Evidence: FasnachtsPage/docs/wr-01.
- Open: WR-02 verified recovery/privilege/audit. Full Linux VM reboot and target cross-VM routing remain WR-04/rollout acceptance; no production enablement or release publication.
- Risks/Assumptions: 14 tests, Ansible syntax, generated Compose idempotence, actual TLS/ACL/two-process/persistent restart/cache isolation and Linux namespace firewall checks pass. All owned fixtures removed; application services/data and CaptureApp unchanged.

### Update 2026-09-07 20:36
- Decisions: Keep the Shared initialization asset identical to oldaplib for AS-01; do not deploy or reload live ontology graphs in this step.
- Implementation: Synchronized files/shared.trig to Shared 0.7.0 with only optional folder archive-default/media-reference relationships; updated stable context.
- Open: Coordinate loading with later backend lifecycle/permission changes and accepted rollout.
- Risks/Assumptions: Byte-for-byte comparison with oldaplib passes; only additive ontology terms and version/modified metadata changed. No playbook, environment, role or running-service change.

### Update 2026-08-17 23:14
- Decisions: Treat a running API container as insufficient deployment evidence; the ZIP export service identity must authenticate successfully before a rollout completes.
- Implementation: Added a public API health wait and a secret-safe post-deploy login probe for the Vault-backed export service account, with regression coverage and operational documentation.
- Open: Confirm the production `exporter` account is active and its password matches the Vault, then perform the coordinated production rollout and authenticated export smoke tests.
- Risks/Assumptions: The login probe issues short-lived tokens but does not retain or expose them; home TLS validation remains disabled only for its private Caddy CA, while production certificate validation stays enabled.

### Update 2026-08-17 00:34
- Decisions: Pin the default coordinated deployment to the ZIP-export-capable API and FasnachtsPage releases while retaining Makefile-derived overrides for normal deployments.
- Implementation: Updated `oldap-deploy.yml` defaults to oldap-api `v0.2.20` and FasnachtsPage `v0.1.33`.
- Open: Publish the matching Docker images and deploy the API/frontend and media stacks to home.org.
- Risks/Assumptions: Both release tags contain the previously verified ZIP-export feature commits.

### Update 2026-08-16 23:44
- Decisions: Keep ZIP-export size, retention, and quota policy in non-secret Ansible variables; reserve Vault exclusively for credentials and signing keys.
- Implementation: Rendered seven bounded Phase-3 operating variables into the API container, added deployment preflight ranges and defaults, and extended deployment regression coverage. Nine focused tests and Ansible syntax-check pass.
- Open: Choose any environment-specific overrides after representative load measurement, then deploy and verify SMTP-backed export notification.
- Risks/Assumptions: Pilot defaults are 50 GB, 24 hours, 60 days, 3/20 active jobs and 100/500 GB retained bytes; no live host was mutated.

### Update 2026-08-15 00:20
- Decisions: Wire ZIP-export trust and mail settings through the existing Vault-backed deployment boundary without populating tracked secrets. Require service/download keys to differ from all seven existing JWT purposes and use the canonical FasnachtsPage/media URLs in production.
- Implementation: Added export-service/download secrets, dedicated OLDAP service credentials, media export URL, export mail backend, production preflight, Compose/template rendering, example placeholders, inventory defaults, and deployment regression coverage.
- Open: Populate the four new Vault values, ensure the export service identity exists, publish compatible API/frontend images, and perform the coordinated deployed smoke test.
- Risks/Assumptions: Production continues to use the network-trusted SMTP relay. No real secret or host configuration was changed by this repository edit.

### Update 2026-08-09 23:35
- Decisions: Separate browser-facing media ingest/delivery from API-to-media report retrieval; keep verified HTTPS for both production routes and use home-only internal HTTP instead of distributing Caddy's private CA.
- Implementation: Added `oldap_media_internal_url` to both inventories, Ansible preflight/rendering, Compose, deployment regression tests, and operational/project documentation. Home resolves internally to `http://media.home.org`; production is pinned to `https://media.oldap.org`; the direct-playbook API fallback is v0.2.15.
- Open: Publish and deploy the API release containing `OLDAP_MEDIA_INTERNAL_URL` support, then refresh the existing READY import report on the home test system.
- Risks/Assumptions: HTTP is restricted to server-to-server traffic between the trusted home test VMs. Browser upload capabilities and persisted public media delivery URLs remain HTTPS; production preflight rejects any noncanonical internal media URL.

### Update 2026-08-08 23:16
- Decisions: Extend the existing deployment boundary with the three purpose-specific ZIP-import keys and a dedicated import identity; keep import links on FasnachtsPage and direct binary/report traffic on the media host.
- Implementation: Wired all import secrets, credentials, URLs, and mail backend through Vault-backed Ansible rendering and Docker Compose; strengthened preflight to require seven distinct keys; pinned direct-playbook defaults to API v0.2.13 and FasnachtsPage v0.1.28; added production inventory contracts, examples, tests, and documentation.
- Open: Add the five new Vault variables locally, verify them through Ansible preflight, and deploy only after GraphDB backup plus the explicit ontology migration plan.
- Risks/Assumptions: `make copy-trigs` updates deployment source files but does not mutate an existing GraphDB repository; the import OLDAP identity must exist and have its intended project-neutral permissions before cutover.

### Update 2026-08-04 15:13
- Decisions: Keep the unauthenticated, network-trusted UniBasel SMTP relay settings outside Vault and scope them to production; retain console delivery for home/default deployments.
- Implementation: Pointed production reset links to `https://fasnacht.digital`, configured `smtp.unibas.ch:25` with STARTTLS and the verified sender, rendered and forwarded all API mail variables, added a production preflight assertion, regression coverage, and synchronized deployment documentation.
- Open: Run `make deploy-vm`, request a fresh password-reset message, verify inbox delivery and link host, and complete one password change.
- Risks/Assumptions: The UniBasel relay continues to trust the production host by network location and accept `lukas.rosenthaler@unibas.ch`; SMTP acceptance alone does not guarantee inbox placement.

### Update 2026-07-24 00:50
- Decisions: Keep `api.oldap.org` as the FasnachtsPage API and permit the canonical cross-site `fasnacht.digital` frontend to use cookie-backed refresh without changing DNS or frontend API routing.
- Implementation: Added a production-only `Secure=true`, `SameSite=None` refresh-cookie override, a deployment preflight assertion, inventory regression coverage, and synchronized operational/project documentation; home and local environments retain `SameSite=Lax`.
- Open: Deploy production manually, sign in again, and verify that the login response sets `SameSite=None` and that a reload sends `oldap_refresh` to `/admin/auth/refresh` in every supported browser.
- Risks/Assumptions: Browsers or privacy modes that fully block third-party cookies can still reject this cross-site session despite `SameSite=None`; exact credentialed CORS and API Origin checks remain required.

### Update 2026-07-23 17:53
- Decisions: Treat the first split-token production rollout as a coordinated API, browser-client, and media-stack maintenance window; prevent direct playbook use from falling back to a pre-auth API image.
- Implementation: Raised the playbook fallback to `oldap-api:v0.2.10`, added `fasnacht.digital` to production API CORS, blocked production clients older than refresh-capable `oldap-app:v0.2.4`, documented joint cutover/rollback gates, and added focused deployment regression checks.
- Open: Release a refresh-capable `oldap-app` image and validate the encrypted Vault plus live end-to-end login, refresh, upload, asset, and IIIF flows during deployment.
- Risks/Assumptions: The legacy and split-token stacks have an unavoidable brief incompatibility window; the same access/media keys must reach both deployment hosts.

### Update 2026-07-17 23:08
- Decisions: Work around the current Ansible/sudo-rs password-prompt incompatibility only on the Ubuntu 26.04 home VM rather than changing its system-wide sudo alternative or weakening sudo authentication.
- Implementation: Set `ansible_become_exe=/usr/bin/sudo.ws` in `oldap_home` and documented why the host-specific override is required; production continues using Ansible's default Become executable.
- Open: Re-run `make deploy-home`; remove the override after the control-node Ansible release supports sudo-rs reliably.
- Risks/Assumptions: Ubuntu's supported classic sudo executable exists at `/usr/bin/sudo.ws`, as provided alongside sudo-rs on Ubuntu 26.04.

### Update 2026-07-17 22:58
- Decisions: Replace the retired Rosy deployment identity with a home-VM environment that mirrors production under `*.home.org`, while leaving `deploy-vm` and `oldap_prod` unchanged.
- Implementation: Renamed the local Make targets and inventory group to `deploy-home`, `soft-reset-home`, and `oldap_home`; connected through `api.home.org`; updated local Caddy routes and OLDAP public URLs for API, app, GraphDB, Fasnacht, and the separately deployed `media.home.org`; retained existing `/srv/storage` paths.
- Open: Deploy the separate local media-server stack and ensure clients trust Caddy's internal CA for local HTTPS.
- Risks/Assumptions: Local DNS maps `api.home.org`, `app.home.org`, `graphdb.home.org`, and `fasnacht.home.org` to this VM and will map `media.home.org` to the separate media deployment; the SSH user remains `rosenth`.

### Update 2026-07-16 22:59
- Decisions: Use the single protected OLDAP Vault file as the default authentication source for test and production deployments while retaining command-line overrides.
- Implementation: Pointed the Makefile at `$HOME/ProgDev/OLDAP/auth/auth.vault.yml`, enabled `--ask-vault-pass` by default, quoted the extra-vars file argument, improved the missing-file error, and synchronized deployment documentation.
- Open: Run the desired `make deploy-rosy` or `make deploy-vm` target and enter the Vault and sudo passwords when prompted.
- Risks/Assumptions: The shared Vault file exists on the Ansible control machine and contains all required, mutually distinct purpose-specific JWT keys plus valid OLDAP service credentials.

### Update 2026-07-15 17:56
- Decisions: Treat media capabilities as a fourth independent JWT purpose and share only the corresponding access/media keys with the media deployment through ignored vars or Vault.
- Implementation: Added media secret and TTL rendering to the API service, pairwise preflight validation across access/refresh/media/reset keys, example secret inventory, and operational documentation for matching the media-server configuration without committing values.
- Open: Populate `oldap_media_jwt_secret` with a new value and provide the same access/media pair to the separate `oldap-mediaserver` deployment vars before rollout.
- Risks/Assumptions: The two deployment repositories do not synchronize secrets automatically; operators must deliberately source both from the same protected secret store.

### Update 2026-07-15 17:34
- Decisions: Complete authentication work package 5 with Ansible-supplied out-of-tree secrets, exact inventory origins, Flask-owned credentialed CORS, and deployment-time failure for incomplete configuration.
- Implementation: Replaced retired `OLDAP_JWT_SECRET` wiring with distinct access/refresh/password-reset keys, token/cookie settings, auth service credentials, and password-reset configuration across inventory, environment template, and Compose. Added ignored/example secret vars, preflight assertions, root-only `.env` rendering, resolved Compose validation, Make integration, and operational documentation; removed Caddy wildcard preflight handling and tracked legacy secret literals.
- Open: Populate `auth-secrets.yml` or an external Vault file with newly generated keys and service credentials before the first deployment; production SMTP remains console-backed until mail variables are deliberately configured.
- Risks/Assumptions: Existing committed legacy JWT values remain visible in Git history and must be treated as compromised; production authenticated browser origins are `app.oldap.org` and `fasnacht.oldap.org`, not the cross-site public `fasnacht.digital` domain.

### Update 2026-06-28 17:05
- Decisions: Use the harvester package version, not the Git release tag, for the Docker image tag propagated into production deployment.
- Implementation: Changed `HARVESTERS_VERSION` in the deployment Makefile from `git describe --tags --abbrev=0` to `poetry version -s`, matching `oldap-harvesters` Docker tags such as `0.1.1`.
- Open: Re-run `make deploy-vm` so `/opt/oldap/compose/.env` receives the corrected `OLDAP_HARVESTERS_TAG`.
- Risks/Assumptions: Assumes `oldap-harvesters` continues publishing Docker images without a leading `v`, while other OLDAP images keep their existing tag conventions.

### Update 2026-06-27 16:00
- Decisions: Keep `oldap-harvesters` aligned with `oldap-tools` for OLDAP library cache access inside the Compose network.
- Implementation: Added `redis` as a dependency of the harvester job and passed `OLDAP_REDIS_URL=redis://redis:6379` so `oldaplib` does not fall back to `localhost:6379` inside the container.
- Open: Re-render/deploy `/opt/oldap/compose` on the VM so the updated service definition and `.env` are both present before the next production run.
- Risks/Assumptions: Assumes the shared Compose `redis` service is the intended cache backend for harvester-side `oldaplib` reads, matching `oldap-api` and `oldap-tools`.

### Update 2026-06-16 23:56
- Decisions: Deploy `oldap-harvesters` as a no-restart Docker Compose job in both `tools` and `harvesters` profiles so it remains analogous to `oldap-tools` while allowing targeted harvester runs.
- Implementation: Added the Compose service, harvester image tag/env paths, Ansible host directories/config rendering/optional Vault-backed secret writes, `templates/harvesters.toml.j2`, Makefile tag propagation, group defaults, and README/context documentation.
- Open: Provide `oldap_harvesters_europeana_api_key` and `oldap_harvesters_oldap_password` via Ansible Vault or create `/srv/storage/oldap-data/oldap-harvesters/secrets/europeana.key` and `oldap.password` manually before running the job.
- Risks/Assumptions: Assumes the harvester image entrypoint accepts `--config /app/harvesters.toml --write-oldap`, that `user_id = "rosenth"` is the intended default unless overridden, and that a world-writable log directory is acceptable for container UID compatibility.

### Update 2026-05-31 23:20
- Decisions: Treat the production deployment render as still open because Ansible could not reach the server.
- Implementation: Validated the cleaned inventory and production host variables; ran the production deployment command, but SSH to `dhlab-oldap.dhlab.unibas.ch:22` timed out before facts were gathered.
- Open: Re-run `ansible-playbook -i inventory.ini oldap-deploy.yml -e oldap_api_tag=v0.2.4 -e oldap_app_tag=v0.2.2 -e oldap_tools_tag=v0.3.5 -e fasnachts_page_tag=v0.1.18 -l oldap_prod` once the server or network path is reachable.
- Risks/Assumptions: No remote files were changed during the failed deployment attempt.

### Update 2026-05-31 23:18
- Decisions: Keep only underscore-based Ansible inventory groups to avoid invalid group-name warnings and duplicate host definitions.
- Implementation: Removed hyphenated duplicate groups from `inventory.ini`; moved shared GraphDB/Caddy defaults into `[oldap:vars]`; set production `public_upload_url` to `https://media.oldap.org/upload` and aligned `public_iiif_url` with `https://media.oldap.org`; updated Makefile limits to `oldap_test` and `oldap_prod`; added project context files.
- Open: Re-run the production deployment so `/opt/oldap/compose/.env` is rendered with the corrected production media URLs.
- Risks/Assumptions: Assumes `media.oldap.org` is the intended public IIIF/media host for production.
