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

## API authentication secrets

The API requires four independent JWT signing keys and an OLDAP service
account for refresh and global logout. These values must never be committed.
The normal deployment reads the encrypted, shared Vault file at
`$HOME/ProgDev/OLDAP/auth/auth.vault.yml` and prompts for its Vault password.
This same protected file can also supply the matching access and media keys to
the `oldap-mediaserver` deployment. To create a new equivalent file, start from
the documented variable set:

```bash
ansible-vault create "$HOME/ProgDev/OLDAP/auth/auth.vault.yml"
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
```

Store the four generated values under `oldap_access_jwt_secret`,
`oldap_refresh_jwt_secret`, `oldap_media_jwt_secret`, and
`oldap_password_reset_jwt_secret`. The media key signs short-lived asset
capabilities and must be copied to the media deployment; it must not equal the
access key used to verify upload Bearer credentials. Configure
`oldap_auth_admin_user` and `oldap_auth_admin_password` for an active OLDAP
service account. Password reset uses the same account by default; optional
separate reset credentials are documented in the example.

`make deploy-rosy` and `make deploy-vm` automatically pass the shared Vault
file and use `--ask-vault-pass`. To override either default, use:

```bash
make deploy-vm \
  AUTH_SECRETS_FILE=/secure/path/oldap-auth.vault.yml \
  ANSIBLE_VAULT_ARGS='--vault-id production@prompt'
```

The playbook rejects missing, short, or reused signing keys before changing the
host. It renders `/opt/oldap/compose/.env` as root-only mode `0600`, validates
the final Compose configuration, and only then recreates containers.

The API receives all four keys. The media deployment receives the same
`oldap_media_jwt_secret` for asset/IIIF capability validation and the same
`oldap_access_jwt_secret` for upload authentication. Its Cantaloupe container
receives only the media key; only the Flask media helper receives both.

The browser-facing applications and API are on different origins. Exact
allowed origins are therefore set per inventory host and Flask handles both
preflight and credentialed CORS responses. Caddy must not add wildcard CORS
headers. Production refresh cookies remain `Secure`, `HttpOnly`, and
`SameSite=Lax`; authenticated administration should use `app.oldap.org` or
`fasnacht.oldap.org`, which are same-site with `api.oldap.org`.

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
