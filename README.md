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
make deploy-home
make deploy-vm
```

`deploy-home` targets the `oldap_home` inventory group and connects to the
local VM through `api.home.org`. `deploy-vm` targets `oldap_prod`.

The home environment mirrors the production host layout under the local
`home.org` DNS zone:

- API: `https://api.home.org`
- App: `https://app.home.org`
- GraphDB: `https://graphdb.home.org`
- Fasnacht page: `https://fasnacht.home.org`
- Media/IIIF: `https://media.home.org`, with uploads below `/upload`

The media URL is configured for the OLDAP applications, but the media server
itself is deployed separately. Persistent OLDAP, GraphDB, Caddy, and harvester
data continue to use the existing `/srv/storage` data disk.

Ubuntu 26.04 uses `sudo-rs` as its default `sudo`. Until the Ansible version on
the control machine includes compatible prompt handling, the `oldap_home`
inventory explicitly uses Ubuntu's supported classic implementation at
`/usr/bin/sudo.ws`. This override is local to the home VM and does not affect
`oldap_prod`.

## API authentication and ZIP-import secrets

The API requires seven independent JWT signing keys and OLDAP service
credentials. Four keys cover access, refresh, media delivery, and password
reset; three further keys isolate ZIP upload, media-to-API import callbacks, and
API-to-media retained-record reads. These values must never be committed.
The normal deployment reads the encrypted, shared Vault file at
`$HOME/ProgDev/OLDAP/auth/auth.vault.yml` and prompts for its Vault password.
This same protected file can also supply the matching access and media keys to
the `oldap-mediaserver` deployment. To create a new equivalent file, start from
the documented variable set:

```bash
ansible-vault create "$HOME/ProgDev/OLDAP/auth/auth.vault.yml"
for purpose in access refresh media password-reset import-upload import-service import-records; do
  openssl rand -hex 32
done
```

Store the seven generated values under `oldap_access_jwt_secret`,
`oldap_refresh_jwt_secret`, `oldap_media_jwt_secret`, and
`oldap_password_reset_jwt_secret`, plus `oldap_import_upload_jwt_secret`,
`oldap_import_service_jwt_secret`, and `oldap_import_records_jwt_secret`. The
media key signs short-lived asset
capabilities and must be copied to the media deployment; it must not equal the
access key used to verify upload Bearer credentials. Configure
`oldap_auth_admin_user` and `oldap_auth_admin_password` for an active OLDAP
service account. Password reset uses the same account by default; optional
separate reset credentials are documented in the example.
Configure `oldap_import_service_user` and `oldap_import_service_password` for
the dedicated OLDAP identity used by ZIP imports. Browser ingest and delivery
use the public `oldap_media_ingest_url`. API-to-media report retrieval uses
`oldap_media_internal_url`, falling back to the public URL when both routes are
the same. Production uses verified `https://media.oldap.org` for both. The home
test deployment keeps browser traffic on `https://media.home.org` but uses
`http://media.home.org` internally because Caddy's private CA is not installed
in the API container. Production import-mail links use
`https://fasnacht.digital`.

`make deploy-home` and `make deploy-vm` automatically pass the shared Vault
file and use `--ask-vault-pass`. To override either default, use:

```bash
make deploy-vm \
  AUTH_SECRETS_FILE=/secure/path/oldap-auth.vault.yml \
  ANSIBLE_VAULT_ARGS='--vault-id production@prompt'
```

The playbook rejects missing, short, or reused signing keys before changing the
host. It renders `/opt/oldap/compose/.env` as root-only mode `0600`, validates
the final Compose configuration, and only then recreates containers.

## Production password-reset mail

Production sends password-reset messages through the University of Basel relay
at `smtp.unibas.ch:25` with STARTTLS. The relay accepts the production host by
network location, so SMTP username and password remain unset and no additional
mail credential belongs in Ansible Vault. The production group variables hold
the non-secret SMTP endpoint, sender, and TLS settings; the environment template
and Docker Compose pass them to `oldap-api`.

The canonical reset page is `https://fasnacht.digital/password-reset`. The
deployment preflight rejects production configuration that falls back to the
console mail backend, points reset links elsewhere, omits the relay or sender,
or disables TLS. SMTP server acceptance was verified independently from inside
the production API container; inbox placement remains an operational check.

The API receives all seven keys. The media deployment receives the matching
`oldap_media_jwt_secret` for asset/IIIF capability validation and the same
access, import-upload, import-service, and import-records keys required at its
bounded trust boundaries. Its Cantaloupe container receives only the media key.

### Coordinated production authentication cutover

The legacy API/media pair and the purpose-specific token pair cannot validate
each other's tokens. Treat the first production rollout as one maintenance
window rather than two independent deployments:

1. Publish and verify the versioned API, browser-client, mediahelper, and
   imageserver images before changing either host.
2. Confirm that the shared Vault contains the same access and media keys used by
   both playbooks, and that the four API keys are distinct.
3. Deploy the OLDAP stack and media stack back-to-back. A short incompatible
   interval is unavoidable, so do not allow administrative uploads during it.
4. Verify API health/version, named-user login and refresh, anonymous access,
   one protected API request, one upload authorization, one protected asset,
   and one IIIF request before reopening the system.

Do not cut over the API while the deployed `oldap-app` image still lacks the
cookie-backed refresh flow. The production playbook blocks `oldap-app` versions
older than `v0.2.4` for this reason. Rollback must restore the previous API and
both previous media component tags together; rolling back only one side
recreates the token-contract mismatch.

The browser-facing applications and API are on different origins. Exact
allowed origins are therefore set per inventory host and Flask handles both
preflight and credentialed CORS responses. Caddy must not add wildcard CORS
headers. The home environment keeps refresh cookies `SameSite=Lax` because its
frontends and API are same-site. Production overrides the cookie to
`Secure`, `HttpOnly`, and `SameSite=None` so the canonical cross-site
`https://fasnacht.digital` frontend can send the `api.oldap.org` refresh cookie.
This flow depends on the browser permitting third-party cookies for the site;
verify the supported production browsers after deployment.

> **Long-term authentication note:** Move the FasnachtsPage API endpoint to
> `https://api.fasnacht.digital` when DNS and domain administration permit it.
> This would make the frontend and API same-site again, allow production to
> return to `SameSite=Lax`, and avoid Safari requiring users to disable
> "Prevent cross-site tracking". Until then, `SameSite=None` is an intentional
> compatibility measure for the cross-site `fasnacht.digital` → `api.oldap.org`
> refresh flow.

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
