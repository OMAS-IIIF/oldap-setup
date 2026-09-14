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
