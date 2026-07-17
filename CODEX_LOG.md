# CODEX_LOG

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
