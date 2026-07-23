# CODEX_LOG

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
