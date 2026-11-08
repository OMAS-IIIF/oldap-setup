# OLDAP Setup Context

- Two-host pre-opening rollback accepted (2026-11-08): partial configuration and private Jena outage cases pass on the existing home pair with all fourteen source services. Production/home wrappers share `tasks/production-private-rollback.yml`. Both archives are validated first; target-only Compose selectors are quarantined; original containers are force-recreated from pinned images to avoid stale network IDs. Media health gates reopening. Original home roots/images and all thirteen API baseline fields are restored; maintenance released. Full safety snapshots remain separate from config-only rollback fixtures. See docs/home-production-rollback-rehearsal.md and its results JSON. Final model/all-project fulltext, immutable production bundles, nine private checks and production backup/harvester wiring remain open.


- Fresh production checkpoint (2026-11-08): coordinated snapshot 20261108-rehearsal-02 is verified locally and on the office Mac; original production GraphDB/API/media and schedules are restored. Source API baseline passes with single-word fulltext probes; legacy multiword behavior differs from approved Jena AND semantics. Isolated six-service source restore, Jena conversion/activation, backend outage and recreated GraphDB rollback now pass; eight live home containers unchanged and clone stopped. The later full two-host runner/partial-installation rehearsal also passes; final model/operational gates remain open. See docs/production-rehearsal-results.json. First real home nighttime compaction completed, shrinking reported storage from 38.7 GB to 314 MB.

- Production execution preparation (2026-11-07 late): new source checkpoint/resume and private-target/opening entry points are documented in docs/production-cutover-runner.md. All work is local; no production pause. Original-container recovery is failure-tested; candidate activation is gated on an isolated end-to-end rollback rehearsal. Final reviewed bundles and post-replacement rollback remain mandatory work. Durable opening intent fences simple GraphDB rollback; old timers remain paused after opening until Jena backup acceptance.

- Production harvest correction (2026-11-07 evening): launcher explicitly preserves profiled Compose default command lists; manual arguments still replace them. Twelve network-isolated runtime combinations plus existing scheduling tests pass; production launcher updated and both real CLI help checks pass. Three test notifications arrived, confirmed by owner; historical queue failure remains unexplained, no mail permissions changed. OCR image/config/secrets/model supplement verified locally and on office Mac, closing batch-retention gap. Identical launcher is also deployed on home; both Jena provider help checks pass. See docs/production-harvest-failure-20261101.md and retention results. No full import run.

- Production rollback preparation (2026-11-07): source-specific cutover/abort/rollback plan is in docs/jena-production-cutover.md. Exact production images and online private configuration are retained separately from data snapshots; eight API, three batch and three media images pass cross-engine load/re-export verification. Docker legacy OCI-index incompatibility is handled with a separate verified import copy, preserving originals. See docs/jena-production-retention-results.json for receiver verification. All 14 source containers unchanged. Coordinated fresh data/media capture, executable cutover adaptation and isolated rollback rehearsal remain open.

- Home maintenance accepted (2026-11-07): published API/Tools a30230d5b695 and Java service b112fc4d are active. Isolated real writes/workers pass 31 checks; live checks pass 27. Data disk is 350 GiB, with about 122 GiB available after the verified stopped-source API snapshot. Growth-triggered native compaction may start only 01:00–03:00 Europe/Zurich; first real overnight duration/reclamation remains to be observed. Coordinated stop waits for active compaction; fallback to an old service is blocked by pending intent. See docs/jena-maintenance-service-results.json and release operations. Production rollback/mail gates remain open.

- Release retention (2026-11-07): accepted home API/media, Tools and standard/OCR harvester image archives plus deployed Jena bundle are retained on Studio under OLDAP_BACKUP/releases/home-accepted-20261107. Hash checks and development-Docker load/ID checks pass. New maintenance candidate and production rollback set remain separate. User declines home email; retain/test production SUCCESS/FAILURE emails to lukas.rosenthaler@unibas.ch. See docs/jena-image-retention-results.json and release operations.

- Night maintenance (2026-11-07): compaction admission now requires a configured local-time window (default 01:00–03:00 Europe/Zurich); all seven policy keys are required. An admitted run finishes safely even after window end. Enabled on home; coordinate backups and measure the first live nighttime runtime.

- TDB growth maintenance (2026-11-07): Growth-triggered compaction configuration is optional and requires a bundle containing JenaCompaction. Candidate validation and template tests cover the four policy settings. Local API/service acceptance is recorded in docs/jena-compaction-acceptance.json; no live activation yet. See sibling oldaplib/docs/migration/jena-compaction.md for capacity, maintenance responses and recovery.

- TDB growth analysis (2026-11-07): reproduced on exact service JAR. 1,000 empty commits add ~152 MiB and 2,000 receipt triples; aborts still add ~56 MiB, pure reads add zero. Stopped clone has 205,955 receipt / 66,271 other triples; all 272,226 quads rebuilt and individually verified in ~113.5 MiB allocated versus ~30.5 GiB original TDB. Read-only eligibility prechecks with transactional reselection are recommended for import/export/mobile job polling; replay guards stay intact. No application change or live compaction. See `docs/tdb-growth-analysis.md`.

- Release/operations preparation (2026-11-07): eight application repositories clean; setup work pending checkpoint. Source inventory and operational gate documented in `docs/jena-release-operations.md`. New snapshot manifests record UTC completion after recovery/hashing; explicit receiver health checks cover age, archive metadata/hash and free capacity. No scheduler/alerts installed. Home connectivity restored after disabling university VPN; 14 running images match the accepted snapshot, Jena JAR hashes match and Studio archive hashes pass. Old media transfer archives retained on /data after checksum verification, relieving system disk from 93% to 47% used. Empty job polling creates persistent transaction receipts and is the next measured growth lead. Runtime image retention, TDB growth and fresh-source rollback remain open.

- Fresh-source preflight (2026-11-07): production sudo verified separately; native RDF-star conversion and offline import pass. A complete source snapshot must include the separate archive-writer coordinator and `/opt/oldap/.env`. Production mobile v0.2.17 lacks graceful SIGTERM support; registry currently empty, but legacy shutdown requires a new check after ingress closure. Gate 3 remains open; no production pause or fresh-source rollback performed. See `docs/production-backup-inventory.md`.

- Restored write/worker acceptance (2026-11-06/07): passed on the disposable Borg-restored home dataset. Non-admin editor upload/edit/import/transform/publish/export, reader/public denials, signed new-media delivery and active-import SIGTERM drain/restart pass. Nine clone containers stopped; eight live IDs/start times unchanged; 26 live checks and eight unit tests pass. Worker preparation preserves bounded parser capabilities and adds private export-only Caddy from recorded snapshot configuration/images. Capacity guard remains unchanged; duplicate clone API transport tar retired after Studio rehash. See `docs/home-restore-writes.md`; next is fresh-source cutover/rollback plus TDB growth and operating gates.

- Media pre-copy experiment (2026-11-06): staged full-size backup shows roughly 16m20s outage versus 11m25s for offline tar/compare. Restored the simpler flow as default (`home_media_precopy=false`); staging remains opt-in. Both modes pass failure-injection tests; staged Borg/application restoration now passes with exact recorded image IDs; original services unchanged across restore. TDB index growth is an open production-capacity investigation. See `docs/home-staged-backup.md`. Extra staging space is required. See `docs/home-media-staging.md` and current production gates in `docs/jena-production-final-gates.md`.

- Backup pause reduction (2026-11-06): archive SHA-256 hashing/manifest creation now follow successful service recovery; copying and source comparison remain offline. Snapshot manifests retain allowlisted actual image IDs, repository digests and platforms from both hosts via `scripts/snapshot-images.py`; the existing receiver preserves metadata. Failure-injection tests cover no publication after compare/recovery/hash errors. Measured full run passes: 887s producer, approximately 685s media outage, 187s hashing online; Studio pull/Borg check/extract/hash all pass. Media copy/comparison dominate the remaining outage. See `docs/home-backup-timing.md`.

- Isolated application restore (2026-11-06): real Borg-extracted snapshot opened successfully in six private home API-VM containers; API/permissions/stories/archive/fulltext/signed media match live. All restored services stopped; eight live container identities/start times unchanged. Scripts reject unsafe archives/mounts and audit isolated networking. Retain raw and RDF-aware story digests because list identifiers can serialize as QName or full IRI. Next: shorten snapshot pause, retain immutable image provenance, investigate API serialization consistency. See `docs/home-restore.md` and evidence JSON; production remains untouched.

- Studio Borg policy (2026-11-06): user approved unencrypted home-only repository at `OLDAP_BACKUP/borg`, with manual 7-daily/4-weekly/3-monthly retention for `home-*` archives. Real archive/integrity/extract/hash verification passed: 44.5 GB input uses about 10.6 GB deduplicated storage; creation 123s, extraction 45s plus 19s verification. Retention applied and kept the sole archive; isolated Linux application restore now passes (see `docs/home-restore.md`). Production encryption remains a separate decision; future recovery information belongs in Apple Passwords. No automatic schedule. See `docs/home-borg.md`.

- Home snapshot pull: `oldap-jena-home-backup.yml` can publish private verified archives after successful service recovery (`home_snapshot_publish=true`). `scripts/pull-home-snapshot.py` runs on Studio, verifies the pair and moves it from incoming to snapshots only on success. First real rehearsal accepted 44.5 GB on Studio with matching hashes; producer 20.5 minutes, final pull 3.8 minutes, 26 live checks pass. Whole-file retry avoids costly partial-archive delta matching. Shorten the offline window before routine use; Borg backup-file restore now passes with the approved home 7/4/3 policy; isolated application restore now passes; no schedule yet. See `docs/home-snapshot-pull.md`.

- Studio backup receiver (2026-11-06): `studio.home.org` has Homebrew Borg 1.4.5 and a passing synthetic archive/integrity/extract test. Protected storage is `/Users/rosenth/OLDAP_BACKUP`; DNS works after the user changed Private Relay settings. Dedicated Studio-to-home SSH access is verified using `~/.ssh/oldap_home_backup.conf`; matched snapshots and Borg backup-file restore are verified; isolated application restore now passes; production encryption/key recovery remain pending. No backup schedule installed. See `docs/production-backup-inventory.md`.

- Production backup inventory (2026-11-05): read-only VPN inspection found nightly 03:15 GraphDB and Fasnacht RDF exports under `/srv/storage/oldap-data/backups`, serialized with harvesting. Office Mac `dhlab-da24-002` pulls RDF and live Fasnacht media at 04:00 via rsync, then versions media with Borg (30 daily/12 weekly/24 monthly). Latest RDF hashes match; coordinated snapshots, operational-state coverage and restore verification remain open. Preserve that pull model for complete Jena backup sets and use home only for restore rehearsal. See `docs/production-backup-inventory.md`; no production backup changes yet.

- Mobile drain (2026-11-05): home maintenance now defaults to SIGTERM, preflights worker support and waits without a forced-kill deadline. API ingress closes only after mobile completion. Shared quiescence covers backup/memory/console/recovery and legacy identity maintenance. Home has the tested drain-capable media image a7b5d97ba17b; legacy SIGINT remains explicit and requires an unused registry. See sibling `oldap-mediaserver/docs/mobile-worker-shutdown.md` for exact image/evidence.

- Automatic Jena recovery (2026-11-05): home has a systemd timer running `scripts/jena-recovery.py`, comparing actual Linux namespace identities and reconnecting identity before API after backend restart. Persistent maintenance locking prevents deployment races; partial repairs retain ownership, with bounded retries and journal diagnostics. Final restart/SIGKILL checks recover in about 12/19 seconds with unchanged API results. See `docs/jena-recovery.md` for pause/resume, scope, fallback and acceptance; mobile draining and production restore/capacity acceptance remain open.

- Jena memory budget (2026-11-05): home runs a 10 GiB total cgroup limit, 6 GiB heap, 512 MiB direct buffers and no container swap. Candidate preparation uses the same defaults with host/native reserve checks. `oldap-jena-memory-update.yml` preserves configuration rollback and coordinated namespace restart; `scripts/check-jena-memory.py` samples cgroup counters. 375 read requests pass without slowdown or response changes; short sampling shows no OOM/restarts. See `docs/jena-memory.md` and evidence. Automatic crash recovery and write-heavy/long-term capacity acceptance remain open.

- Git checkpoint (2026-11-05): reviewed source revisions, verification scope and remaining production gates are recorded in `docs/jena-git-checkpoint.md`. Checkpoint commits are local; publication, merges and deployment are separate.
- Official Fuseki administration: the unmodified Apache 6.2.0 UI and native query/update/upload protocols run inside the existing Jena JVM over its protected, managed-text dataset. Independent Caddy credentials and a private transport key protect port 8040. `oldap-fuseki-admin-install.yml` coordinates snapshot, namespace restart and rollback on home. The custom Python reader is superseded. See `docs/jena-console.md`.

- Home apps accepted (2026-11-04): oldap-app, SALSAH, Fasnacht and mediahelper/three workers now use isolated digest-pinned Jena images. Normal DNS/TLS/browser, 28 live API/media checks and packaged HE-AAC conversion pass; seven stable registry tags unchanged. SIPI-2 and backend infrastructure retained. See `docs/jena-apps-home.md` and results JSON for provenance and rollback.

- Home application rollout: `scripts/prepare-jena-app-images.py` freezes allowlisted sources with fingerprints. `oldap-jena-web-update.yml` replaces only oldap-app/Fasnacht using digest-pinned candidates with rollback; SALSAH installs additively on Jena. Media uses its own guarded image-only playbook. See `docs/jena-apps-home.md` for source, activation and rollback workflow.

- SALSAH Jena compatibility (2026-11-04): first-install topology validation accepts the existing Jena/archive-policy stack and preserves it when adding SALSAH. The alternate api.salsah.org proxy blocks internal Jena callback paths. Thirteen deployment tests and syntax validation pass; no SALSAH deployment performed. See sibling salsah-2/docs/jena-compatibility.md.

- Jena harvesters: batch-only image overrides and backend-aware launchers preserve the installed Jena/policy stack and existing scheduling/Swisscovery locks. `oldap-jena-harvesters-install.yml` accepts explicit published standard/OCR digests, validates imports and installs configuration without starting jobs. RC2 candidates are published and installed on home; bounded real import/replay, public API and native OCR acceptance pass. See `docs/jena-harvesters.md` and sibling harvester `docs/jena-home-results.json`. Production activation remains pending.

- Publication policy (2026-11-04): home now includes the reviewed Fasnacht publication definition (ArchiveMediaEditor publishers; per-resource UPDATE remains required). `oldap-jena-archive-enable.yml` validates a staged candidate before installing, backs up the old policy and force-recreates the API to refresh the bind mount. Existing publisher capability and a two-resource preview pass without publication. BMG-Archivist account lacks the editor role; user chose to keep membership unchanged, matching production. See `docs/jena-publication-policy-results.json`.

- Active-Jena home snapshots: `oldap-jena-home-backup.yml` provides offline two-host snapshots with byte comparison, hashes and ordered namespace-consumer recreation. It is home-only, single-operator and distinct from GraphDB first-cutover freeze. Legacy mobile SIGINT shutdown is admitted only for an empty registry; production requires proper mobile draining and off-host restore. See README workflow.

- RC publication (2026-11-04): exact 1.0 RC API/Tools images published; protected tags unchanged; native isolated home transport passes. Home update and verified offline two-host backup are complete; 27 public checks and 48 reads at concurrency 16 pass. See `docs/jena-1.0rc1-home-results.json`. Preexisting HTTP 502 recovered by restarting old API/identity clients after Jena had restarted into a new network namespace; Kernel journal confirms global OOM killed Java (about 14 GiB anonymous RSS); memory bounds, automatic coordinated recovery and mobile worker SIGTERM draining remain open. See `docs/jena-1.0rc1-publication-results.json`.

- Local 1.0 RC images (2026-11-04): API/Tools AMD64 and ARM64 candidates `jena-1.0.0-rc1-4d3c5ef8e1e1` built from clean commits and pass packaged transport acceptance. Exact image IDs and installed dependency inventories are in `docs/jena-1.0rc1-images-results.json`; local bundle location and remaining native home/publication gates are in `docs/jena-1.0rc1-preparation.md`. No publication or deployment.

- Coordinated 1.0 candidate (2026-11-03): core packages and OLDAP service wrapper now use 1.0.0rc1. API/tools depend on >=1.0.0rc1,<2.0.0 instead of a sibling path/0.x constraint. Poetry-generated portable locks use the exact candidate library wheel hash; library lock is now tracked. Existing development venvs were not reinstalled. Clean installed-wheel tests and rebuilt Java service pass. See ../oldap-setup/docs/jena-1.0rc1-preparation.md and results JSON. No publication, tag, merge or deployment; older dated version statements below describe historical checkpoints.

## OLDAP 1.0 merge preparation

Setup acceptance and limitations are recorded in `docs/jena-merge-readiness.md`.
First cutover requires a GraphDB source and no prior target-opening marker;
rollback now refuses source restart if target enumeration/stop/removal fails.
The actual rescue commands pass local fake-Docker failure injection. No remote
services were accessed during this review. Production restore, writer/media and
final 1.0 artifact acceptance remain separate from the local checkpoint.

See `docs/jena-1.0-merge-plan.md` and `docs/jena-merge-inventory.json` for fetched
refs, dirty source inventory, PR drafts, dependency gates and publication boundaries.
Library/API/Tools have local checkpoints; setup is now reviewed/checkpointed too.
The subsequent library HTTP-pooling fix and API evidence still need their final
local checkpoint before packaging. Initial inventory counts are historical. Library main is 0.4.27 and the GraphDB baseline is refactor/ontology
0.7.29. Proposed core release is 1.0.0; independent media/frontend components keep
their versions. No merge, version bump, tag, push or deployment performed.

- Home RC4 (2026-11-03): API uses library BEGIN-only admission retry (five attempts, 750 ms total backoff, fresh journaled IDs); uncertain admission and UPDATE/COMMIT never replay. Installed-image contention checks pass on both architectures and isolated native home, including replacement. Public checks and existing import states preserved; see sibling setup docs/jena-begin-retry-rc4-home-results.json. Worker leases and public signatures unchanged.

- Jena worker routes (2026-11-03): Caddy blocks only the private Jena namespace; established export/import/mobile internal routes retain their service JWT guards. Bounded home proxy/client update playbooks preserve data, namespace owner and policy overlays. Network acceptance uses the independent identity sidecar, including coordinated replacement and bridge isolation; see README.md.

- Home archive structure enabled (2026-11-03): user-authorized Fasnacht structure-only policy is mounted read-only through setup archive-policy-compose.yml; established editor roles/grant-on-creation rules retained, publication remains disabled. Live model validation and admin/anonymous capabilities pass; no data/role changes. Setup oldap-jena-archive-enable.yml retains the original environment and preserves the Jena namespace. Real structure editing remains manual acceptance; production unchanged.

- Home media access-key repair (2026-11-03): initial API access-key rotation had left mediahelper's verifier stale, causing upload HTTP 401. Setup now synchronizes only existing media access-verification consumers from the active API and recreates changed containers. Home repair and non-mutating valid/invalid upload-auth checks pass; real image-upload workflow remains user acceptance. Keep API, private identity verifier and mediahelper aligned for future key rotations/full provisioning. See setup docs/jena-media-access-results.json.

- Home concurrency repair (2026-11-03): public archive bursts exposed callback worker starvation, not a Jena crash. The private identity verifier now runs independently on loopback port 8001, reusing the pinned API blueprint/codec through setup scripts/jena_identity.py. API/tools data contracts and images are unchanged. Namespace lifecycle includes the identity consumer. Home browser archive and stories pass; 48 requests at concurrency 16 all return 200 with equivalent complete RDF results. See setup docs/jena-concurrency-semantic-results.json and the coordinated identity-install playbook. Sequential cutover checks alone were insufficient; parallel/browser acceptance is required.

- Home activation (2026-11-03): home.org now serves the pinned Jena API with the persistent 8 GiB-heap backend. GraphDB is stopped; source storage and two-host backups are retained. All 30 story responses match the frozen GraphDB baseline; existing login, fulltext AND search and signed IIIF/image delivery pass. Approved account correction retains DATA_PERMISSIONS; four orphan membership annotations remain inactive. Target has 65,376 application quads and 16 users. See the central cutover guide and setup docs/jena-home-results.json. Production is unchanged. Next: production-specific writer/harvester/media release acceptance, off-host backup/restore and coordinated routine-update automation. Earlier dated entries below describe historical stages, not the current home deployment.

- Jena image release (2026-11-02): API `jena-0.2.37-rc1-c1cb0919375a` and tools `jena-0.3.22-rc1-c1cb0919375a` published for AMD64/ARM64 with exact source-matched library wheel; stable/latest untouched. Legacy migration-checkout publication targets are disabled. Deployment requires reviewed digests. Installed-image transport passes locally and published API passes on native home.org; full app/source migration and activation remain open. See docs/jena-images-results.json and the setup README. Source snapshots capture uncommitted changes; no Git/PyPI publication.

- Jena migration (2026-11-02): this is the dedicated `migration/jena` checkout; inherited local main working changes are retained, original setup unchanged. `jena-compose.yml` shares the backend network namespace with direct clients, retains API DNS and writer coordination, and publishes no backend port. Both local ARM and home.org x86_64 transport/recreation acceptance pass. `oldap-jena-prepare.yml` stages a fresh candidate only; legacy provision/reset refuse selected Jena. See README.md for the production migration path and docs/jena-network-results.json for bounded evidence. Next: matched release images, full source/identity migration and coordinated activation/update workflow; no running application switched.

- Optional VM-only weekly harvesting: `make install-harvest-schedule-vm` installs a Sunday 05:00 Europe/Zurich systemd timer, sequential Europeana/Swisscovery runs and per-source mail via the existing host mail transport. A shared in-container/host flock serializes both with the unchanged manual backup script via a systemd drop-in. Routine deploy maintains installed scheduling without re-enabling paused timers; only controls/templates/logging change, not harvester images or data. See `docs/harvest-schedule.md`. Activation requires the operator sudo installation.

- Swisscovery CPU OCR uses an explicit `swisscovery-compose.yml` override of the installed harvester service, launched by `scripts/run-swisscovery.sh` (not the normal COMPOSE_FILE). `make install-swisscovery-vm` copies approved remote config/model inputs and preflights the version-matched `-ocr` image; routine `make deploy-vm` maintains/checks it thereafter. Shared persistent Linux flock serializes complete runs (exit 75 on overlap), with 2 CPU / 5 GiB limits. Swisscovery installation alone creates no scheduler; weekly scheduling is a separate opt-in workflow above. See `docs/swisscovery.md`; deployed standard/OCR 0.1.13 images and Swisscovery launcher were observed on the VM on 2026-10-26.

- Added optional SALSAH Compose overlay, explicit first-install targets, shared frontend-only update tasks and conditional combined updates. Existing hosts remain opt-in. See docs/salsah-deployment.md.

- Production publication accepted 2026-09-15: 285 Europeana records imported and confirmed visible. Private `auth/writer-production/archive-policy.json` now includes the reviewed publication block and remains the source referenced by deployment-vars.yml. Routine updates preserve it; full provisioning distributes it. See docs/publication-activation-status.md. Bootstrap generation is not a replacement for this established policy.

- Routine production application updates now use `make deploy-vm` / `oldap-update.yml`: retain installed server secrets/Writer configuration, pull explicit images, preflight all writer images, persist only version tags, update API/frontends without dependencies. No Docker provisioning, data migration, infrastructure restart or timer changes. Local Vault inputs are only needed for configuration/provisioning workflows. See `docs/routine-production-updates.md`.

- `make activate-vm` is the explicit first-start boundary after migration/operator acceptance. It loads the same private inputs as prepare-vm, requires stopped writers and bootstrap=false, and starts only API plus frontends without dependency/init/harvester startup. Public/media acceptance and backup timer resumption remain separate.

- Production archive migration now has an isolated final-backup rehearsal in `tests/probe_archive_migration.py` and a reviewed executor in sibling FasnachtsPage `docs/production-rollout/`. Migration plus exact retry passed; writer Redis is provisioned, application writers/timer remain stopped, production graph migration and independent live verification are complete; recovery operator installation and read-only checks are complete; coordinated activation remains pending.

- `make prepare-vm` / `oldap_deploy_phase=prepare` now provide an existing-host preparation boundary: require stopped Compose writers, skip Docker provisioning and stack startup, provision/probe writer Redis only. External writers still require coordinated maintenance. See `docs/production-preparation.md`; migration and activation are separate pending steps.

- Production writer preparation now has `scripts/prepare-production-writer.py`, a separate pinned amd64 operator image and guarded manual launcher in `operator/README.md`. Private material is outside Git; Vault encryption and isolated runtime rehearsal are complete; production installation and coordinated migration remain pending.

- WR-04: The MacBook now uses private launchd API/GraphDB/writer-Redis services via `scripts/native-services.py`; native Redis rejects missing/corrupt AOF and uses separate ACL identities. Production remains the reviewed opt-in Docker/SSH topology. See `docs/writer-recovery.md` and FasnachtsPage `docs/wr-04/README.md`.

- WR-02 adds separately opt-in recovery API/operator ACL identities, API-only credential distribution, reviewed inventory digest and cross-member validation. `docs/writer-recovery.md` specifies the offline Docker/SSH proof and interrupted-controller procedure. Recovery remains disabled pending real target and native MacBook acceptance; no operator socket is mounted into applications.

- WR-01 (2026-09-10): dedicated writer deployment implemented and locally verified; see `docs/writer-deployment.md`. Existing inventories remain disabled; all participating writers use one owner/TLS endpoint. Missing operational storage requires recovery, not automatic initialization. Next: WR-02 safe recovery and operational authorization; target VM acceptance remains separate.

## Docker API workers
- Latest user deployment accepted (2026-10-01): API 0.2.31 / oldaplib 0.7.25, exact Project/PropertyClass source match, existing 4/2 settings. 1,152 timed reads pass; all 17 contents and RDF fingerprints match. At 16 readers: median/p95 143/559 ms, 17.40 requests/s, API CPU 1.57 cores. No maintenance/configuration/data changes during measurement; see docs/api-workers.md and sibling API VM project-identity report.
- Worker/thread counts are explicit host/group Ansible variables (`oldap_api_workers` 1–8, `oldap_api_threads` 1–16); defaults preserve 4/2. Full provisioning validates/renders them, routine image updates retain installed values. `oldap-api-workers.yml` is the explicit stopped-writer maintenance path for compatible installed Compose files, preserving secrets and starting only API without pulls/dependencies.
- Source-verified isolated Docker recovery with real API 2/4-worker crashes and automatic replacement passed on 2026-09-30. Existing container-level fencing already handles worker processes; no library recovery rewrite was needed. Fresh workers stay blocked until reconciliation/finish, then a real transaction commits. Test-only injection routes never ship. See `docs/api-workers.md` and its JSON evidence.
- Native laptop remains one foreground API process. The user deployed API v0.2.29 / oldaplib 0.7.23 on the eight-vCPU VM. Read acceptance on existing 4-worker/2-thread settings passes 2,409 timed requests; full metadata batches at 16 readers reach 16.13 requests/s and 649 ms p95, with unchanged RDF/container/process fingerprints. See `docs/api-workers.md` and sibling `oldap-api/doc/performance/2026-09-30-vm.md`. Next: API/library CPU profiling. Controlled 2/4-worker comparison and isolated release-image recovery rehearsal remain separate; these reads changed no deployment configuration.

## Purpose
This repository deploys the OLDAP stack with Ansible and Docker Compose. It prepares host directories, installs Docker, copies GraphDB initialization data, renders Caddy, harvester, and Compose environment files, and starts the OLDAP API, app, tools, harvesters, Fasnacht page, GraphDB, Redis, and Caddy services.

## Repository State
- `files/shared.trig` is synchronized with oldaplib Shared 0.7.0 (AS-01): only optional StagingFolder archive-default and media-reference relationships were added. This prepares initialization assets; existing environments have not been reloaded or deployed. Load only during the coordinated archive-workflow rollout after backend authorization and lifecycle support are accepted.
- `inventory.ini` is the source of environment-specific deployment variables.
- `oldap-deploy.yml` is the main deployment playbook for the Docker Compose stack.
- `oldap-playbook.yaml` handles OLDAP reset workflows.
- `docker-compose.yml` defines the runtime services.
- `templates/oldap.env.j2` renders `/opt/oldap/compose/.env` on the target host.
- `templates/harvesters.toml.j2` renders the Europeana/Fasnacht harvester configuration on the target host.
- `templates/Caddyfile.j2` renders the Caddy reverse-proxy configuration.
- API authentication secrets come from ignored `auth-secrets.yml` or an
  external Ansible Vault file. The playbook validates them before deployment,
  renders a root-only Compose environment, and validates the resolved Compose
  model before containers are recreated. Access, refresh, media,
  password-reset, import-upload, import-service, import-record, export-service,
  and export-download signing keys are independent. The media-facing values are shared with
  `oldap-mediaserver` through the protected Vault, never committed.
- `files/` contains ontology and initialization files copied to GraphDB init storage.

## Architecture and Conventions
- Deployment configuration is Ansible-first, with host-specific values in the inventory and shared defaults in group variables or common inventory vars.
- Inventory group names use underscores (`oldap_home`, `oldap_prod`) to avoid Ansible warnings about invalid characters.
- Flask is the single CORS authority for the API. Inventory supplies exact
  browser origins and Caddy must not emit wildcard API CORS headers.
- Production refresh cookies use `Secure=true` and `SameSite=None` because the
  canonical `fasnacht.digital` frontend authenticates against the cross-site
  `api.oldap.org` origin. Same-site home deployments retain the shared
  `SameSite=Lax` default.
- Production public media URLs currently use `media.oldap.org`; uploads are exposed at `https://media.oldap.org/upload`.
- Production password-reset links target `https://fasnacht.digital` and mail is
  submitted through the network-trusted University of Basel relay at
  `smtp.unibas.ch:25` with STARTTLS and no SMTP credentials. The playbook
  validates this production-only contract before deployment.
- ZIP imports use a public media URL for browser ingest/delivery and an
  independently configurable internal URL for API-to-media report retrieval.
  Production uses verified `https://media.oldap.org` for both; the home API
  uses `http://media.home.org` internally while browsers retain HTTPS. Owner-facing
  production report links use `https://fasnacht.digital`. The
  API receives a dedicated OLDAP import identity plus three purpose-specific
  import JWT keys from the same external Vault used by the media deployment.
- ZIP exports receive a separate OLDAP service identity, distinct service and
  download JWT keys, the canonical media export URL, and an independent
  console/SMTP mode. Owner mail contains only the authenticated FasnachtsPage
  status URL; it never embeds a download capability.
- ZIP-export operating policy is non-secret Ansible configuration. The API
  receives bounded archive size, READY/audit retention, active-job quotas, and
  retained-byte quotas through the rendered Compose environment; the playbook
  rejects unsafe values before deployment. Secrets remain exclusively in the
  Vault-backed variables.
- `oldap-harvesters` is deployed as a no-restart Compose job with both `tools` and `harvesters` profiles. Its configuration, secrets, and logs live under `/srv/storage/oldap-data/oldap-harvesters` by default; secrets are supplied as server-side files and are never committed.
- Keep changes proportional and close to the existing Ansible/Docker Compose structure.

## Operational Notes
- `make deploy-home` deploys to the local VM through `api.home.org`; its public
  service URLs mirror production under `*.home.org`, including the separately
  deployed media service at `media.home.org`. The home inventory uses
  `/usr/bin/sudo.ws` for Ansible Become because Ubuntu 26.04's default
  `sudo-rs` is incompatible with the current control-node prompt handling.
- `make deploy-vm` deploys to production.
- Running a deployment re-renders `/opt/oldap/compose/.env` from `templates/oldap.env.j2` using the selected inventory host variables.
- A normal deployment waits for the public API health endpoint and then logs in
  once with the Vault-backed ZIP export service credentials. This fails the
  rollout immediately when that account is missing, inactive, or has a
  mismatching password instead of leaving the export worker in a retry loop.
- `make deploy-home` and `make deploy-vm` default to the shared encrypted
  `$HOME/ProgDev/OLDAP/auth/auth.vault.yml` and prompt for its Vault password;
  `AUTH_SECRETS_FILE` and `ANSIBLE_VAULT_ARGS` remain overridable.
- The first purpose-specific authentication rollout is a coordinated API,
  browser-client, and media-stack maintenance window. Legacy and split-token
  deployments are not cross-compatible; rollback must restore both API and
  media component versions together. Production preflight requires a
  refresh-capable `oldap-app` release at `v0.2.4` or newer.
- Run the Europeana Fasnacht harvester on the server with `docker compose --profile tools run --rm oldap-harvesters` from `/opt/oldap/compose`.

## Next Steps
- Populate and validate the ZIP import/export keys and dedicated service
  identities in the shared Vault before the coordinated deployment window.
- Deploy and verify SMTP-backed password reset end to end, including inbox
  delivery and one successful password change from the emailed link.
- Keep this context file updated only for strategic workflow, architecture, or convention changes.

- VM follow-up (2026-10-01): deployed API 0.2.30 / oldaplib 0.7.24 passes exact-catalog read acceptance at unchanged 4/2 workers/threads: 1,132 requests, matching content/RDF, 16-reader p95 649→591 ms and API CPU 2.13→1.78 cores. No deployment/worker maintenance was performed by the measurement. Sampler helper-process false positives fixed in sibling API tools; see docs/api-workers.md and the API report. Keep current workers; next candidate is library model/copy CPU.
