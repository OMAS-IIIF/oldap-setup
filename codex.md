# OLDAP Setup Context

## Purpose
This repository deploys the OLDAP stack with Ansible and Docker Compose. It prepares host directories, installs Docker, copies GraphDB initialization data, renders Caddy and Compose environment files, and starts the OLDAP API, app, tools, Fasnacht page, GraphDB, Redis, and Caddy services.

## Repository State
- `inventory.ini` is the source of environment-specific deployment variables.
- `oldap-deploy.yml` is the main deployment playbook for the Docker Compose stack.
- `oldap-playbook.yaml` handles OLDAP reset workflows.
- `docker-compose.yml` defines the runtime services.
- `templates/oldap.env.j2` renders `/opt/oldap/compose/.env` on the target host.
- `templates/Caddyfile.j2` renders the Caddy reverse-proxy configuration.
- `files/` contains ontology and initialization files copied to GraphDB init storage.

## Architecture and Conventions
- Deployment configuration is Ansible-first, with host-specific values in the inventory and shared defaults in group variables or common inventory vars.
- Inventory group names use underscores (`oldap_test`, `oldap_prod`) to avoid Ansible warnings about invalid characters.
- Production public media URLs currently use `media.oldap.org`; uploads are exposed at `https://media.oldap.org/upload`.
- Keep changes proportional and close to the existing Ansible/Docker Compose structure.

## Operational Notes
- `make deploy-rosy` deploys to the test host.
- `make deploy-vm` deploys to production.
- Running a deployment re-renders `/opt/oldap/compose/.env` from `templates/oldap.env.j2` using the selected inventory host variables.

## Next Steps
- Verify production deployment after inventory changes by checking the rendered `/opt/oldap/compose/.env` on `dhlab-oldap`.
- Keep this context file updated only for strategic workflow, architecture, or convention changes.
