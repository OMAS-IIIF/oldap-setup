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
  model before containers are recreated. Access, refresh, media, and
  password-reset signing keys are independent; the access and media values must
  be shared with `oldap-mediaserver` through its separate ignored/Vault vars
  file, never by committing either value.
- `files/` contains ontology and initialization files copied to GraphDB init storage.

## Architecture and Conventions
- Deployment configuration is Ansible-first, with host-specific values in the inventory and shared defaults in group variables or common inventory vars.
- Inventory group names use underscores (`oldap_test`, `oldap_prod`) to avoid Ansible warnings about invalid characters.
- Flask is the single CORS authority for the API. Inventory supplies exact
  browser origins and Caddy must not emit wildcard API CORS headers.
- Production public media URLs currently use `media.oldap.org`; uploads are exposed at `https://media.oldap.org/upload`.
- `oldap-harvesters` is deployed as a no-restart Compose job with both `tools` and `harvesters` profiles. Its configuration, secrets, and logs live under `/srv/storage/oldap-data/oldap-harvesters` by default; secrets are supplied as server-side files and are never committed.
- Keep changes proportional and close to the existing Ansible/Docker Compose structure.

## Operational Notes
- `make deploy-rosy` deploys to the test host.
- `make deploy-vm` deploys to production.
- Running a deployment re-renders `/opt/oldap/compose/.env` from `templates/oldap.env.j2` using the selected inventory host variables.
- `make deploy-rosy` and `make deploy-vm` default to the shared encrypted
  `$HOME/ProgDev/OLDAP/auth/auth.vault.yml` and prompt for its Vault password;
  `AUTH_SECRETS_FILE` and `ANSIBLE_VAULT_ARGS` remain overridable.
- Run the Europeana Fasnacht harvester on the server with `docker compose --profile tools run --rm oldap-harvesters` from `/opt/oldap/compose`.

## Next Steps
- Deploy the updated API image and authentication configuration, then continue
  with browser integration from authentication work package 6.
- Keep this context file updated only for strategic workflow, architecture, or convention changes.
