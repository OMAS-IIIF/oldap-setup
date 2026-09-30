# SALSAH deployment and trusted frontend mail routing

This guide describes how to add SALSAH to an existing, running OLDAP installation,
how to publish and deploy later SALSAH releases, and how to configure email links
for several frontends. SALSAH shares the existing API, GraphDB, Redis, writer policy
and media services. Project/data transfer is a separate operator action; the SALSAH
installation does not import a project dump, migrate data or initialize a database.

## Repositories, machines and paths

Run the `make` commands in this guide on the local development/control machine.
Ansible connects to the selected server over SSH. Each command block starts with
an explicit repository directory; adapt `/Users/rosenth/ProgDev/OLDAP` if the
repositories are checked out elsewhere.

| Repository | Responsibility | Local directory |
| --- | --- | --- |
| `salsah-2` | Frontend source, Docker image and image publication | `/Users/rosenth/ProgDev/OLDAP/salsah-2` |
| `oldap-api` | API code, trusted email routing and API image publication | `/Users/rosenth/ProgDev/OLDAP/oldap-api` |
| `oldap-setup` | Main-stack Ansible configuration, Caddy and SALSAH deployment targets | `/Users/rosenth/ProgDev/OLDAP/oldap-setup` |
| `oldap-mediaserver` | Media-stack configuration and deployment, including allowed browser origins | `/Users/rosenth/ProgDev/OLDAP/oldap-mediaserver` |

`oldap-setup/inventory.ini` selects these main-stack environments:

| Environment | Ansible group | SSH target | SALSAH frontend | Browser API | Browser media |
| --- | --- | --- | --- | --- | --- |
| Production | `oldap_prod` | `dhlab-oldap.dhlab.unibas.ch` | `https://salsah.org` | `https://api.salsah.org` | `https://media.oldap.org` |
| Home | `oldap_home` | `api.home.org` | `https://salsah.home.org` | `https://api.home.org` | `https://media.home.org` |

On either main-stack server, Docker Compose configuration lives in
`/opt/oldap/compose`. This is a **server directory**, not a local repository.
`api.salsah.org` routes to the existing `oldap-api` container; it does not create a
second API or database. The production media stack is deployed separately by
`oldap-mediaserver` to its own inventory host.

## Before the first installation

- Have Docker/Buildx available locally for image publication and authenticate to
  the Docker registry with an account allowed to publish `lrosenth/salsah-2` and
  `lrosenth/oldap-api`.
- Have Ansible and the existing Docker collection available on the control machine,
  working SSH access and the target host's sudo credentials. Installation and
  update targets prompt for the sudo password.
- Confirm that the existing OLDAP API and Caddy are running. The production routine
  API update also requires the already installed writer overlay.
- Have the existing authentication Vault available when deploying the media stack
  or using the full Home deployment. The dedicated SALSAH install/update targets
  retain installed secrets and do not require a local Vault file.
- Verify production DNS for `salsah.org`, `www.salsah.org` and `api.salsah.org`,
  including any AAAA records, and public reachability on ports 80/443. A wildcard
  record alone does not establish the apex `salsah.org` record. Home needs
  `salsah.home.org` and browser trust in the Home Caddy certificate authority.
- Compare the server's installed Caddyfile with
  `oldap-setup/templates/Caddyfile.j2` if there have been manual server changes.
  The installation renders that template and does not merge host-local additions.

The version numbers below are examples, not a statement that an image has already
been published. Use a new immutable release tag for each changed image.

## First installation: ordered procedure

### 1. Publish the compatible API release from `oldap-api`

The API release must contain `oldap_api.frontend_links`. Prepare a reviewed release
commit/tag using the normal `oldap-api` release process. The Makefile's
`bump-patch-level` target changes the version, commits/tags through the configured
bump tool, and pushes Git refs; it is not a read-only version check.

After the release tag is ready, build and publish its image:

```sh
cd /Users/rosenth/ProgDev/OLDAP/oldap-api
make show-version
make docker-build
```

`oldap-api` derives `VERSION` from the most recent Git tag. Its `docker-build`
target publishes linux/amd64 and linux/arm64 images with the version tag and
`latest`. Production deployment uses the explicit version tag.

### 2. Deploy the API release from `oldap-setup`

Review the application versions selected by the local sibling repositories:

```sh
cd /Users/rosenth/ProgDev/OLDAP/oldap-setup
make show-versions
```

Then use the existing combined production update:

```sh
cd /Users/rosenth/ProgDev/OLDAP/oldap-setup
make deploy-vm
```

This updates the existing application set, not only the API. To keep other
components pinned, pass their intended versions explicitly using `API_VERSION`,
`APP_VERSION`, `TOOLS_VERSION`, `HARVESTERS_VERSION` and `FASNACHTS_VERSION`.
Choose those values from the reviewed deployment versions, not blindly from the
current local checkout. See [routine production updates](routine-production-updates.md).
Before SALSAH is installed, the combined production target skips SALSAH.

For Home, the existing `make deploy-home` in `oldap-setup` installs the API through
full provisioning. It has broader effects and requires the local Vault; it is not
the production routine-update workflow.

Without `OLDAP_FRONTENDS_FILE`, the new API retains the existing email destinations.
The SALSAH installation checks that the compatible API module is present before
activating the registry.

### 3. Publish the SALSAH image from `salsah-2`

```sh
cd /Users/rosenth/ProgDev/OLDAP/salsah-2
make show-version
make docker-build VERSION=v0.0.1
```

Like FasnachtsPage, `docker-build` builds **and publishes** linux/amd64 and
linux/arm64 images. The example publishes `lrosenth/salsah-2:v0.0.1`.
`VERSION` changes the image tag; it does not update `package.json`. Keep the package
version and release tag consistent and never overwrite a published release tag.

For a local native image without publication, use `make docker-build-local` in
`salsah-2`. SALSAH's container receives `ORIGIN`, `PUBLIC_API_URL` and
`PUBLIC_MEDIA_URL` from Compose at runtime; no local `.env` file belongs in the image.

### 4. Review email configuration in `oldap-setup`

Defaults are in `oldap-setup/group_vars/all.yml`. Environment overrides belong in
`oldap-setup/group_vars/oldap_prod.yml` for production or a corresponding
`oldap-setup/group_vars/oldap_home.yml` for Home.

Review `oldap_frontends`, `salsah_origin`, `salsah_api_url` and `salsah_media_url`.
The default registry maps existing browser origins to the canonical Fasnacht
frontend and SALSAH to its own origin. The detailed registry contract and an example
are below. An environment-specific `oldap_frontends` mapping should include all
required entries: do not assume a partial mapping is merged with the defaults.

### 5. Apply media CORS configuration from `oldap-mediaserver`

The media configuration includes `https://salsah.org` for production and
`https://salsah.home.org` for Home alongside the existing origins. These changes
must be deployed separately for browser uploads and protected media access.

Before invoking the media deployment, preserve the production feature selection.
`oldap-mediaserver/ansible/host_vars/dhlab-iii.dhlab.unibas.ch.yml` currently sets
`mobile_media_enabled: true`. The last documented production rollout in
`oldap-mediaserver/CODEX_LOG.md` (2026-09-11) explicitly overrode this to `false`:
the separate mobile worker was not activated. A plain `make deploy-production`
uses the saved `true` setting and requires the additional, coordinated mobile
credentials. Adding SALSAH browser CORS does not require mobile-media activation.

If mobile media remains intentionally disabled on production, retain that setting:

```sh
cd /Users/rosenth/ProgDev/OLDAP/oldap-mediaserver
make show-versions
make deploy-production ANSIBLE_ARGS='-e mobile_media_enabled=false'
```

If mobile media has since been activated, do not disable it merely to pass
preflight. Use the normal `make deploy-production` with the correctly provisioned
Vault and API-side mobile configuration. Confirm the current operational state
rather than treating the historical rollout entry as live server evidence.

For Home, run `make deploy-test` in `oldap-mediaserver`, retaining its intended
feature selection. Both targets use the normal media deployment workflow, prompt
for Vault/sudo credentials, and can recreate media services. Review or explicitly
pin `IMAGESERVER_TAG` and `MEDIAHELPER_TAG` to avoid an unintended media version
update. Neither `oldap-setup` deployment nor a SALSAH image update deploys the
media host.

If `Validate purpose-specific mediahelper token secrets` fails, the failure can
mean a missing, too-short or reused key. With mobile media enabled, the required
set includes `oldap_mobile_media_service_jwt_secret` in addition to the existing
seven access/media/import/export keys. The `no_log` setting intentionally hides
secret-bearing assertion details; do not turn it off or paste decrypted Vault
contents into troubleshooting output. Do not regenerate existing shared keys to
fix this error: their consumers must agree on the values. A recap with `changed=0`
at this preflight means this failed invocation has not applied configuration or
restarted services. Python interpreter discovery warnings are unrelated to this
assertion failure.

### 6. Install SALSAH from `oldap-setup`

For production:

```sh
cd /Users/rosenth/ProgDev/OLDAP/oldap-setup
make install-salsah-vm SALSAH_VERSION=v0.0.1
```

For Home:

```sh
cd /Users/rosenth/ProgDev/OLDAP/oldap-setup
make install-salsah-home SALSAH_VERSION=v0.0.1
```

The installation playbook performs these operations on the selected server:

1. Checks the running API for the compatible mail-routing module.
2. Reads installed configuration and backs up `.env` and `Caddyfile` under
   `/opt/oldap/compose`, with a `.before-salsah-<timestamp>` suffix.
3. Installs `salsah-compose.yml` and renders `frontends.json` from the trusted
   Ansible configuration.
4. Validates the registry, pulls the SALSAH image, and validates the candidate
   Compose and Caddy configurations before persisting the new selection.
5. Appends the SALSAH overlay to the existing Compose selector, sets SALSAH runtime
   values and adds the SALSAH browser origin, retaining installed secrets and other
   application tags.
6. Recreates only `oldap-api` and `salsah-2`, waits for container readiness, checks
   API health and reloads Caddy.

The API restart briefly affects existing applications. Schedule this initial
configuration change accordingly. The installation does not initialize databases,
change writer policy or timers, start dependencies, or replace the installed base
`docker-compose.yml`. Existing GraphDB/Redis and FasnachtsPage containers are not
recreated by this target.

Caddy validation/reload uses stdin to avoid stale single-file bind mounts after
atomic file replacement; see the [Caddy CLI documentation](https://caddyserver.com/docs/command-line#caddy-reload).

## Later releases and configuration changes

For a frontend-only change, publish a new image from `salsah-2`, then run the
matching dedicated update from `oldap-setup`:

```sh
cd /Users/rosenth/ProgDev/OLDAP/salsah-2
make docker-build VERSION=v0.0.2

cd /Users/rosenth/ProgDev/OLDAP/oldap-setup
make deploy-salsah-vm SALSAH_VERSION=v0.0.2
```

| Target, run in `oldap-setup` | Effect |
| --- | --- |
| `make deploy-salsah-vm SALSAH_VERSION=v0.0.2` | Update only installed SALSAH in production; no API restart |
| `make deploy-salsah-home SALSAH_VERSION=v0.0.2` | Update only installed SALSAH on Home |
| `make deploy-vm SALSAH_VERSION=v0.0.2` | Update the existing production application set and SALSAH when installed |
| `make deploy-home SALSAH_VERSION=v0.0.2` | Full Home provisioning, preserving an installed SALSAH feature selection |

Dedicated and combined routine updates share `oldap-setup/tasks/update-salsah.yml`.
They pull before persisting the tag, save the previous environment and wait for
SALSAH container health. A dedicated update fails if SALSAH has not been installed.
New full-provisioning hosts remain opt-in through `salsah_enabled: true`, after
compatible images and configuration are available.

Routine production and dedicated SALSAH updates do **not** distribute changed
Caddy routes or the email registry. To apply changes to `oldap_frontends` on an
existing SALSAH installation, review the full mapping and rerun the appropriate
`install-salsah-*` target in `oldap-setup`, explicitly retaining the desired SALSAH
tag. That configuration run recreates the API and SALSAH again. Adding another
frontend may also require API/media CORS and proxy changes; a registry entry alone
does not deploy that frontend.

## Email registry: configuring additional frontends

`oldap-setup/templates/frontends.json.j2` serializes `oldap_frontends` into
`/opt/oldap/compose/frontends.json` on the server. The overlay mounts it read-only
at `/run/oldap-frontends.json` inside the API and sets `OLDAP_FRONTENDS_FILE`.

An entry in the Ansible mapping looks like this:

```yaml
oldap_frontends:
  salsah:
    origin: https://salsah.org
    display_name: SALSAH
    routes:
      password_reset: /password-reset
      import_status: /imports/{import_id}
      export_status: /exports/{export_id}
```

This excerpt shows one entry only; retain the Fasnacht and other required entries
in the complete deployed mapping.

- `salsah` is a stable identifier persisted internally on new import/export jobs.
- `origin` is the canonical, server-approved destination. Production destinations
  require HTTPS and cannot include a path, query, credentials or fragment.
- `display_name` supplies the application name in email content.
- `routes` contains all three local absolute paths. Only the documented
  `{import_id}` and `{export_id}` placeholders are allowed. The API appends the
  password-reset token itself; never configure a token placeholder or external URL.
- Optional `origins` lists exact browser origins that select the canonical target.
  For example, an entry can accept both a legacy alias and the canonical domain.
  Without `origins`, only `origin` selects the entry. Entries must not overlap.

The API selects the entry from the browser's Origin header. Clients submit neither
a mail URL nor a new JSON field. Origin is routing metadata, not authentication:
a non-browser client can forge it, but can only select server-approved destinations.
The registry grants no project permissions; existing authentication and job-owner
checks remain authoritative.

When the registry is enabled, unknown browser origins fail before creating jobs or
reset tokens. Requests without Origin and legacy jobs retain the existing
`OLDAP_PUBLIC_APP_URL` / `OLDAP_PASSWORD_RESET_FRONTEND_URL` fallback destinations.
A stored ID missing from the registry fails closed at delivery. Retain entries while
jobs may still send/retry mail, and avoid reassigning an existing ID to a different
application. Public request/response schemas and project RDF schemas are unchanged.

## Acceptance after installation

From the control machine, check the public production endpoints:

```sh
curl --fail https://salsah.org/health
curl --fail https://api.salsah.org/health
```

SALSAH should return `status: ok`; API health should also report `status: ok`.
A responding health endpoint is not a substitute for the following browser checks:

1. Open SALSAH and verify that `www.salsah.org` redirects to `salsah.org`.
2. Confirm FasnachtsPage and `oldap-app` still load and authenticate.
3. In SALSAH, test login, page reload/session restoration, token refresh and logout,
   including Safari. Verify the intended project is available.
4. Open a protected IIIF image and perform a small authorized upload.
5. Request a password reset for a controlled account. Confirm the real email links
   to SALSAH and that the complete reset flow succeeds.
6. Create a small ZIP import and export from SALSAH. Confirm each email opens the
   correct SALSAH job, including after login, and foreign users cannot access it.
7. Verify a Fasnacht notification still opens FasnachtsPage. Include an existing
   pre-registry job when available to exercise legacy fallback.

For Home, use the Home URLs from the environment table and trust the Home CA;
do not disable certificate verification as a substitute for configuring that trust.

## Rollback and failed installation

### Frontend-only release rollback

Deploy the previous published SALSAH version from `oldap-setup`:

```sh
cd /Users/rosenth/ProgDev/OLDAP/oldap-setup
make deploy-salsah-vm SALSAH_VERSION=v0.0.1
```

Use `deploy-salsah-home` for Home. This rollback changes only the frontend and
requires that the previous image remains compatible with the running API.

### First-installation failure

The installation saves configuration copies; it does not perform an automatic
transactional rollback. Identify the last completed task before deciding what to
restore. A failure before service recreation may leave only configuration changes;
a later failure may leave the new API configuration or SALSAH running.

On the affected server, work in `/opt/oldap/compose` with the required sudo rights:

1. Identify the matching `.env.before-salsah-<timestamp>` and
   `Caddyfile.before-salsah-<timestamp>` backups from the failed installation.
   Keep secret-bearing environment files private.
2. If abandoning the first installation, stop the SALSAH service while its overlay
   is still selected. Restore the matching `.env` and `Caddyfile` backups.
3. Validate the restored Compose configuration, then recreate only `oldap-api`
   with `docker compose up -d --no-deps --force-recreate oldap-api`.
4. Validate and reload the restored Caddyfile through stdin, as the installation
   playbook does. Check API health and the existing frontends again.

Do not use `docker compose down` for this rollback: that stops the shared stack.
For a repeated configuration run, the installer does not back up an existing
`frontends.json` or `salsah-compose.yml`; preserve those separately before changing
an established registry/overlay and restore them if that change must be reversed.

Avoid downgrading the API to a version without frontend-routing support while
routed jobs are active. Keeping the JSON registry alone is insufficient: old API
code cannot preserve the new internal frontend ID when rewriting jobs. Prefer
rolling back only SALSAH while retaining the compatible API and registry.
