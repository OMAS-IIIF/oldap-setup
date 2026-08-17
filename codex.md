# OLDAP Setup Context

## Purpose
This repository deploys the OLDAP stack with Ansible and Docker Compose. It prepares host directories, installs Docker, copies GraphDB initialization data, renders Caddy, harvester, and Compose environment files, and starts the OLDAP API, app, tools, harvesters, Fasnacht page, GraphDB, Redis, and Caddy services.

## Repository State
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
