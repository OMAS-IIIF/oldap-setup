# Deployment of the OLDAP framework

This repository deploys the OLDAP stack with Ansible and Docker Compose. The
main playbook installs Docker, prepares persistent host directories, copies
GraphDB initialization data, renders Caddy and Compose configuration, and brings
up the stack under `/opt/oldap/compose`.

## Main files

- `inventory.ini` contains host-specific deployment variables.
- `oldap-deploy.yml` is the main Ansible playbook for the Docker Compose stack.
- `templates/oldap.env.j2` renders `/opt/oldap/compose/.env` for Docker Compose.
- `templates/harvesters.toml.j2` renders the production harvester configuration.
- `docker-compose.yml` defines GraphDB, Redis, OLDAP API/app/tools/harvesters,
  Fasnacht page, and Caddy.

## Deploying

Use the Makefile targets so image tags are passed consistently from the sibling
repositories:

```bash
make show-versions
make deploy-rosy
make deploy-vm
```

`deploy-rosy` targets the `oldap_test` inventory group. `deploy-vm` targets
`oldap_prod`.

To override only the harvester image during a manual deployment:

```bash
ansible-playbook -i inventory.ini oldap-deploy.yml \
  -e oldap_harvesters_tag=v0.1.0 \
  -l oldap_prod \
  --ask-become-pass
```

## Harvester deployment

`oldap-harvesters` is deployed as a no-restart Docker Compose job, analogous to
`oldap-tools`. It belongs to both the `tools` and `harvesters` profiles: `tools`
keeps it aligned with the existing operational job profile, while `harvesters`
allows targeted runs without enabling unrelated tool jobs.

The service uses:

- Image: `lrosenth/oldap-harvesters:${OLDAP_HARVESTERS_TAG:-latest}`
- Config mount: `${OLDAP_HARVESTERS_CONFIG}` to `/app/harvesters.toml:ro`
- Secret mount: `${OLDAP_HARVESTERS_SECRETS}` to
  `/run/secrets/oldap-harvesters:ro`
- Log mount: `${OLDAP_HARVESTERS_LOGS}` to `/var/log/oldap-harvesters`
- Command: `--config /app/harvesters.toml --write-oldap`

On the server, the default paths are:

```text
/srv/storage/oldap-data/oldap-harvesters/harvesters.toml
/srv/storage/oldap-data/oldap-harvesters/secrets/europeana.key
/srv/storage/oldap-data/oldap-harvesters/secrets/oldap.password
/srv/storage/oldap-data/oldap-harvesters/logs/europeana.log
```

The rendered TOML uses `server = "http://graphdb:7200"` because the harvester
runs inside the Compose network. Do not use `localhost` in the container
configuration.

## Harvester secrets

No harvester secrets are stored in Git. The playbook writes secret files only
when Ansible variables are defined, so existing server-side secrets are not
overwritten by a normal deployment.

With Ansible Vault, define these variables in encrypted inventory or group vars:

```yaml
oldap_harvesters_europeana_api_key: "..."
oldap_harvesters_oldap_password: "..."
```

Without Ansible Vault, create the files manually on the server:

```bash
sudo install -d -m 0700 -o root -g root /srv/storage/oldap-data/oldap-harvesters/secrets
sudo install -d -m 0777 -o root -g root /srv/storage/oldap-data/oldap-harvesters/logs

sudo sh -c 'printf "%s\n" "EUROPEANA_API_KEY_HERE" > /srv/storage/oldap-data/oldap-harvesters/secrets/europeana.key'
sudo sh -c 'printf "%s\n" "OLDAP_PASSWORD_HERE" > /srv/storage/oldap-data/oldap-harvesters/secrets/oldap.password'

sudo chmod 0600 /srv/storage/oldap-data/oldap-harvesters/secrets/europeana.key
sudo chmod 0600 /srv/storage/oldap-data/oldap-harvesters/secrets/oldap.password
sudo chown root:root /srv/storage/oldap-data/oldap-harvesters/secrets/europeana.key
sudo chown root:root /srv/storage/oldap-data/oldap-harvesters/secrets/oldap.password
```

## Running the harvester

After deployment and secret setup, start one production harvest run on the
server:

```bash
cd /opt/oldap/compose

docker compose --profile tools run --rm oldap-harvesters
```

For a targeted profile run:

```bash
cd /opt/oldap/compose

docker compose --profile harvesters run --rm oldap-harvesters
```

Check the log file:

```bash
sudo tail -f /srv/storage/oldap-data/oldap-harvesters/logs/europeana.log
```
