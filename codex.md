# OLDAP Setup Context

- Production publication accepted 2026-09-15: 285 Europeana records imported and confirmed visible. Private `auth/writer-production/archive-policy.json` now includes the reviewed publication block and remains the source referenced by deployment-vars.yml. Routine updates preserve it; full provisioning distributes it. See docs/publication-activation-status.md. Bootstrap generation is not a replacement for this established policy.

- Routine production application updates now use `make deploy-vm` / `oldap-update.yml`: retain installed server secrets/Writer configuration, pull explicit images, preflight all writer images, persist only version tags, update API/frontends without dependencies. No Docker provisioning, data migration, infrastructure restart or timer changes. Local Vault inputs are only needed for configuration/provisioning workflows. See `docs/routine-production-updates.md`.

- `make activate-vm` is the explicit first-start boundary after migration/operator acceptance. It loads the same private inputs as prepare-vm, requires stopped writers and bootstrap=false, and starts only API plus frontends without dependency/init/harvester startup. Public/media acceptance and backup timer resumption remain separate.

- Production archive migration now has an isolated final-backup rehearsal in `tests/probe_archive_migration.py` and a reviewed executor in sibling FasnachtsPage `docs/production-rollout/`. Migration plus exact retry passed; writer Redis is provisioned, application writers/timer remain stopped, production graph migration and independent live verification are complete; recovery operator installation and read-only checks are complete; coordinated activation remains pending.

- `make prepare-vm` / `oldap_deploy_phase=prepare` now provide an existing-host preparation boundary: require stopped Compose writers, skip Docker provisioning and stack startup, provision/probe writer Redis only. External writers still require coordinated maintenance. See `docs/production-preparation.md`; migration and activation are separate pending steps.

- Production writer preparation now has `scripts/prepare-production-writer.py`, a separate pinned amd64 operator image and guarded manual launcher in `operator/README.md`. Private material is outside Git; Vault encryption and isolated runtime rehearsal are complete; production installation and coordinated migration remain pending.

- WR-04: The MacBook now uses private launchd API/GraphDB/writer-Redis services via `scripts/native-services.py`; native Redis rejects missing/corrupt AOF and uses separate ACL identities. Production remains the reviewed opt-in Docker/SSH topology. See `docs/writer-recovery.md` and FasnachtsPage `docs/wr-04/README.md`.

- WR-02 adds separately opt-in recovery API/operator ACL identities, API-only credential distribution, reviewed inventory digest and cross-member validation. `docs/writer-recovery.md` specifies the offline Docker/SSH proof and interrupted-controller procedure. Recovery remains disabled pending real target and native MacBook acceptance; no operator socket is mounted into applications.

- WR-01 (2026-09-10): dedicated writer deployment implemented and locally verified; see `docs/writer-deployment.md`. Existing inventories remain disabled; all participating writers use one owner/TLS endpoint. Missing operational storage requires recovery, not automatic initialization. Next: WR-02 safe recovery and operational authorization; target VM acceptance remains separate.

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
