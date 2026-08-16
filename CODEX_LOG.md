# CODEX_LOG

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
