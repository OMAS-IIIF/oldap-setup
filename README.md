# Deployment of the OLDAP framework

Restored write/worker acceptance: [runbook and results](docs/home-restore-writes.md).

Home application candidate rollout and rollback: [runbook](docs/jena-apps-home.md).

Jena harvester candidates and batch installation: [runbook](docs/jena-harvesters.md).

Official Apache Fuseki administration: [deployment and access](docs/jena-console.md).

## Publishing Jena candidate images

The migration checkout disables the old API/tools Makefile publication targets.
They previously pushed normal tags (API also `latest`) or published tools on
PyPI. Use `scripts/jena-images.py` from this setup checkout instead. The original
GraphDB checkouts are unchanged.

```sh
# Use a NEW bundle directory outside Git. This Python environment has poetry-core.
../oldap-api/.venv/bin/python scripts/jena-images.py prepare --rc 1 --bundle /absolute/new-bundle
../oldap-api/.venv/bin/python scripts/jena-images.py build --bundle /absolute/new-bundle
../oldap-api/.venv/bin/python scripts/jena-images.py accept --bundle /absolute/new-bundle \
  --service-release /absolute/built-jena-service
../oldap-api/.venv/bin/python scripts/jena-images.py publish --bundle /absolute/new-bundle
```

Preparation copies only package source/resources and packaging metadata, excluding
repository-root configuration, credentials, tests and virtual environments. It
builds local API/tools/library wheels; nothing is uploaded to PyPI. Staged package
versions receive `+jena.rcN.FINGERPRINT`, and both clients require that exact
library version. Working-tree versions remain unchanged. Git HEAD, dirty state,
per-file source hashes and wheel/context hashes are retained because the current
migration includes uncommitted work; HEAD alone does not identify the release.

Tags have the form `lrosenth/oldap-api:jena-0.2.37-rc1-FINGERPRINT`, plus
`-amd64`/`-arm64` architecture tags. Only these repositories/tag shapes are allowed.
The content fingerprint supplements the RC number. Use a new RC for a changed
release; never reuse an existing published tag. Base Python is pinned by digest;
resolved dependency versions are retained inside `/opt/oldap-release/dependencies.txt`.
Dependency resolution occurs at build time: rebuilding is not a substitute for
promoting an already tested image digest.

Build loads both architectures locally, checks installed package versions,
`pip check`, and tools CLI startup. Acceptance tests each installed API image
against real Jena, using the real identity blueprint/codec, without source mounts.
It verifies transactions, persisted data after container recreation and bridge
isolation. This is not full API/account/migration or harvester acceptance.
Tools' existing direct commands remain GraphDB-specific; use the implemented
API transport for Jena operations rather than assuming an environment variable
converts every legacy CLI command. Harvester images are a separate release gate.

Publish requires acceptance matching the built image IDs. It verifies bundle
hashes, refuses existing tags and registry errors, pushes exactly the tested
architecture images and creates the multiarch index from their digests. It does
not rebuild or write any stable/latest tag. Before/after digest snapshots check
`latest` and the current normal version tags. Registry tags are mutable and this
check is not an atomic registry lock: use one publisher per bundle. If publishing
partially fails, retain the manifest and inspect uploaded digests; do not blindly
retry/overwrite tags. Retire that RC and prepare a new one if necessary.

`published.json` records the selected multiarch digest and architecture digests.
Candidate preparation requires those exact digests and renders
`OLDAP_JENA_API_IMAGE`/`OLDAP_JENA_TOOLS_IMAGE`; the overlay refuses missing image
selections instead of falling back to `latest` or normal release tags. No image publication activates a deployment. Authentication uses
the existing Docker credential helper; no registry secrets enter build contexts.

### Published candidate — 2026-11-02

- API: `lrosenth/oldap-api:jena-0.2.37-rc1-c1cb0919375a`
- Tools: `lrosenth/oldap-tools:jena-0.3.22-rc1-c1cb0919375a`
- API deployment: `lrosenth/oldap-api@sha256:e452566c33ed12f98a0e49f7af09e12afd1490c1174f727f4b5116fe74a01628`
- Tools deployment: `lrosenth/oldap-tools@sha256:da6a7ccc60eebe4b38090d56dcf0dce2830297e1c4644c220022c18fb4474a33`

Both indexes contain Linux AMD64 and ARM64 images. Normal version tags and
`latest` retain their previous digests (including absence where no latest exists).
Packaged transport acceptance passes locally for both architectures and on
native x86_64 home.org by the published digest. Home activation is now complete;
see the acceptance evidence and workflow below.
API UID/GID 100/101 and tools root behavior are retained for existing bind mounts.
Keep the release bundle/source snapshots outside Git for provenance and recovery;
no source commit/push was performed in this step. See
[release evidence](docs/jena-images-results.json) for checks, provenance and limits.
Full application initialization, real identities/data and coordinated activation
remain subsequent gates; these are migration release candidates.

## Jena migration branch: private container deployment

The `migration/jena` checkout under `OLDAP-Jena/oldap-setup` is based on the
existing local main checkout, including its uncommitted harvesting changes.
Those inherited changes remain uncommitted here; the original checkout is
untouched. Ignored credentials were not copied. Do not deploy ordinary GraphDB
release images as if they already contained the migration code.

### Network and lifecycle

`jena-compose.yml` is an explicit LAST overlay after the normal Compose file
and, where installed, `writer-compose.yml` and frontend overlays. It is not
selected by default. Compose must support `!reset`; validate with the target
Docker Compose before activation.

Jena owns the network namespace. API, tools and harvesters join it via
`network_mode: service:oldap-jena`. Jena still binds only loopback on port 3031;
its identity callback uses `http://127.0.0.1:8001/internal/jena/identity`.
The independent `oldap-jena-identity` container runs only the installed identity
blueprint, using `scripts/jena_identity.py` as its WSGI entry point. It has its
own worker pool and only access-token/callback secrets, no database credentials.
Using the public API pool for callbacks creates a capacity cycle: public requests
wait for Jena while Jena waits for a free API worker. The archive page's parallel
initial load exposed this; simply increasing worker counts does not remove it.
Start the verifier before public API readiness and recreate it with every Jena
namespace replacement. Rotate its access signing key together with the API's.
The owner has the network alias `oldap-api`, so existing Caddy/frontend URLs
continue to work. No Jena port is published. The Caddy template refuses
`/internal/jena/*` on both home and production API routes. Existing
`/internal/export-claims`, `/internal/exports`, import and mobile-worker routes
must still reach their purpose-specific service authentication; a broad
`/internal/*` block breaks background processing. Other bridge containers
can still reach API port 8000; the callback independently requires its secret.

Only the GraphDB dependency is removed: writer Redis health dependencies,
policy mounts and coordinator settings survive the merge. GraphDB/init are
behind the explicit `graphdb-legacy` profile; existing source containers are
not deleted by applying an overlay. Do not run `down` or remove source volumes
on a combined source/target deployment. Media workers continue using the API;
do not share the private backend namespace with the media VM.

**A backend container replacement requires coordinated consumer replacement.**
After fencing ALL writers (including external jobs/media workers and timers),
stop and remove API/tools/harvester containers before stopping/removing Jena.
Create Jena normally against the preserved dataset, then recreate API and
verify identity, read, write, permissions and receipt recovery before reopening
writers. Recreate any additional installed direct backend consumers as well.
An API-only restart does not require replacing Jena. Never use `--init` on
normal restart; never delete transaction reservations/receipts as cache.

The existing GraphDB full-provision/reset workflows now refuse an installed
`:jena-compose.yml` selection. The routine GraphDB updater already rejects
unknown overlay selections. The coordinated Jena activation/update playbook
is still a separate readiness gate; do not bypass these guards.

### Candidate preparation (no activation)

`oldap-jena-prepare.yml` stages a NEW candidate directory, built release, private
service configuration and candidate environment. It verifies the copied Jena
jar/dependency/recovery-tool hashes against the reviewed build metadata. It
does not start containers, initialize data, install a runtime on the host,
replace the installed `.env`, or change the public API. It refuses an existing
candidate root; inspect an interrupted attempt rather than blindly retrying.
Prepared files target UID/GID 1000; verify that ownership for another host.

The operator input file (outside Git, preferably Vault encrypted) supplies
`oldap_jena_release_source` (local output of oldaplib's service builder),
`oldap_jena_api_image` and `oldap_jena_tools_image` (the tested `repository@sha256:...`
references from `published.json`), and four
distinct URL-safe random keys of 43–128 characters:
`oldap_jena_service_key`, `oldap_jena_bootstrap_key`,
`oldap_jena_fulltext_key`, `oldap_jena_identity_key`.
Optional `oldap_jena_root` must match `/srv/storage/oldap-jena-NAME`.
The runtime is a digest-pinned multi-architecture Java 25 image; the default
heap is 8192 MiB. These are deployment inputs, not production sizing evidence.

```sh
ansible-playbook -i inventory.ini oldap-jena-prepare.yml \
  -e @/absolute/private/jena-candidate.yml --ask-vault-pass \
  -l oldap_home --ask-become-pass
```

The candidate `config/jena.env` contains ONLY Jena settings. It must never
replace the complete application `.env`. Activation must merge reviewed
settings while preserving existing authentication, media and writer policy,
using a matched migration API/tools/harvester release set. No such merge or
remote preparation has been performed by the network acceptance test.

### Reproducible connection acceptance

```sh
python3 scripts/check-jena-network.py --release /absolute/built-jena-release
../oldap-api/.venv/bin/python -m unittest tests.test_jena_deployment -v
```

The first command uses the actual overlay with a fresh Docker project and
temporary dataset, the real API identity blueprint and OLDAP token codec.
Sibling migration source packages are mounted read-only into the existing
API runtime image; this is a test fixture, not a releasable API image. It
checks transactions, invalid credentials, API DNS, backend bridge isolation
and coordinated namespace replacement. It publishes no host ports and removes
its own containers afterward. On Linux run as UID 1000 with Docker access.
Run on both the development machine and the x86_64 target VM. The second command
checks the base/writer overlay merge and parses both actual Caddy configurations.
These tests do not certify full API startup, accounts, worker recovery or load.

### Whole-source home rehearsal and activation

**Accepted 2026-11-03:** home.org now runs the pinned Jena API and persistent
backend; GraphDB is stopped with its data retained. See
[home acceptance evidence](docs/jena-home-results.json) and the
[central cutover record](../oldaplib/docs/migration/graphdb-to-jena-cutover.md).
All 30 story responses match the frozen source; existing login, fulltext AND
search and signed IIIF/JPEG delivery pass. Users must log in again following
access/refresh key rotation. Production is unchanged.

Final backups are `/srv/storage/oldap-jena-backup-20261103` on api.home.org and
`/data/oldap-jena-backup-20261103` on media.home.org. Earlier 20261102 copies
remain. These are same-host copies; off-host recovery acceptance is still needed
for production. Rehearsal containers/network have been removed; do not rerun
initial activation against the active dataset.

The current home-only sequence retains the production-like source, migrates a
complete RDF snapshot and switches only after private API acceptance:

```bash
ansible-playbook -i inventory.ini oldap-jena-prepare.yml -l oldap_home -e @/private/jena-vars.json --ask-become-pass
ansible-playbook -i inventory.ini oldap-jena-rehearse.yml -l oldap_home -e @/private/jena-vars.json --ask-become-pass
# Run scripts/check-jena-account-parity.py on the API host; review every difference.
# Apply reviewed domain/account corrections and configure managed fulltext.
ansible-playbook -i inventory.ini oldap-jena-freeze.yml -l oldap_home -e @/private/jena-vars.json --ask-become-pass
ansible-playbook -i inventory.ini oldap-jena-activate.yml -l oldap_home -e @/private/jena-vars.json --ask-become-pass
```

Private inputs extend preparation variables with `oldap_jena_snapshot` (local
converted TriG), `oldap_jena_snapshot_sha256`, and
`oldap_jena_expected_source_sha256` (original whole GraphDB export). Set
`oldap_jena_accept_candidate: true` only after reviewing target acceptance.
Paths must be new; a failed import is retained unmarked, never blindly retried.

First-cutover guards are deliberately conservative: freeze requires the active
source API to select GraphDB, and activation refuses an existing `target-opened.txt`
marker. Never delete that marker to rerun activation; target writes may exist.
Before reopening traffic, automatic rollback inventories existing target containers
and stops/removes them in client-before-backend order. Missing containers are
harmless, but an inventory, stop or removal error halts rollback before restarting
GraphDB. Resolve the failed shutdown explicitly; do not run both writable backends.

The source export must use `application/x-trigstar`, `infer=false`, all graphs.
Run the native `ConvertLegacyRdfStar.java` first, retain its report and original
bytes, and resolve account/ontology differences separately. The packaged
`JenaInitialImport input.trig SHA256 /new/absolute/dataset` creates the service
marker only after verifying persisted RDF. It accepts at most 64 MiB converted
input; the legacy converter's existing 16 MiB input bound is unchanged.

Rehearsal uses an isolated Compose project `oldap-jena-review`, private Redis,
separate files and localhost:18000. The API has real source accounts, so use SSH
access and never publish this rehearsal port. No background media workers run
against that copied dataset. It uses the exact reviewed base Compose file;
rehearsal-only overrides must not hide missing application environment settings.
Deployment tests cover namespace, private callback routing and storage separation.

Freeze targets only the inventoried home hosts. It stops API ingress and media
writers, requires empty source coordination DB 1, compares the final RDF export
with the reviewed source, and archives GraphDB/API/Redis/config and media files
on their respective VMs. A failed freeze restarts the original services. These
are same-host recovery copies; independent off-host backup remains a production
requirement. Source import jobs were terminal and source media operation folders
empty at the current inventory; repeat that audit before future cutovers.

Activation keeps source GraphDB stopped and its storage intact. It merges only
Jena inputs, selects separate Redis storage, rotates access/refresh signing keys
(users log in again), and installs the private callback proxy block. Candidate
API is stopped before its namespace owner. Failed private startup restores the
original environment/proxy/base Compose and services. This rollback ran successfully
on the first attempt when the legacy base lacked an explicit staging Redis URL.
The corrected base sets that URL for API/tools/harvesters; a new full freeze and
backup preceded successful activation. Once ingress/media workers reopen, rollback
requires reconciling target writes; the playbook does not claim automatic rollback
of accepted application work. The source backup manifest records this boundary.

The overlay sets Redis AOF `appendfsync=always` and `noeviction`, satisfying the
library's durable mutation coordination guard when DB 1 is shared with the cache
server. Existing deployments using a dedicated writer service retain that service
and require their own reviewed activation inventory; the current home playbooks
must not be applied unchanged to those or to production.

### Repairing an already activated home callback topology

`oldap-jena-identity-install.yml` installs the independent verifier into the
existing Jena deployment without data migration, key rotation or image changes.
Run with the accepted private candidate variables and sudo access. It retains
pre-repair configuration, starts/verifies the callback first, stops media writers
and ingress, drains API clients, then recreates the namespace owner and both
consumers. Ingress reopens only after health checks pass. A failure after draining
requires operator diagnosis/resume; never rerun first import or restore GraphDB
to repair this topology. Existing Jena writes remain authoritative.

Run `scripts/check-jena-concurrency.py` on the API host after activation/update:
it compares complete sequential responses with 48 requests at concurrency 16,
covering archive metadata, selector lists, taxonomy, user and story reads. Also
run `scripts/check-jena-home.py` and verify the actual archive page in a browser.
Sequential endpoint probes alone did not detect the worker capacity cycle.

### Media access verification after key rotation

The API, private identity verifier and mediahelper must use the same access
signing key, issuer and audience. Image delivery uses a separate media key, so
working IIIF delivery does not prove upload access-token compatibility.

`tasks/jena-home-media-access.yml` reads only active API verification settings,
identifies existing key-bearing environment files in the inventoried home media
stack and updates them with private backups. It never adds access-key privileges
to worker files that lacked them. First activation runs it before reopening, then
uses `docker compose up` to recreate changed consumers: `docker start/restart`
alone retains the old environment. The standalone `oldap-jena-media-access.yml`
repairs an already activated home deployment without rotating API credentials.
Do not use this home-specific inventory unchanged in production. Keep protected
provisioning inputs coherent with the active keys before future full provisioning.

The 2026-11-03 repair updated only `mediahelper-access.env`; runtime values now
match the API. [Acceptance evidence](docs/jena-media-access-results.json) includes
a fresh API token reaching upload form validation (no project/file, hence no
write) and missing/invalid-token rejection. A real upload/conversion/storage test
remains distinct from this non-mutating authentication check.

### Archive structure and publication policy on home

Enabled at the user's request on 2026-11-03. The previous disabled message was
correct: no `OLDAP_ARCHIVE_POLICY_FILE` was installed on home. The reviewed
`files/jena-home-archive-policy.json` enables Fasnacht's existing structure and
media editor roles and grant-on-creation rules. On 2026-11-04 it also gained the
reviewed publication block from FasnachtsPage/docs/permissions/fasnacht-publication-policy.json:
ArchiveMediaEditor publishers, ArchiveObject/CarnivalEvent roots and related
ArchiveMediaObject media, explicit public read grants and a 100-resource limit.
It does not assign roles to users or bypass per-resource UPDATE checks.

`oldap-jena-archive-enable.yml` validates the policy against live Jena roles,
models and properties on a staged candidate before replacing the active file,
retains the previous policy and `.env.before-archive-policy`,
and installs `archive-policy-compose.yml`. The overlay mounts the server-owned
policy read-only into API/tools/harvester configuration; only the API is force-recreated
to refresh the single-file bind mount after atomic replacement.
The selected stack is now `docker-compose.yml:jena-compose.yml:archive-policy-compose.yml`.
Retain this selection and policy on subsequent deployment/backup. Existing
GraphDB rollback is not part of this workflow. Production needs its own review.

[Capability evidence](docs/jena-archive-policy-results.json) verifies enabled
structure/create access for administrators and denial for anonymous users,
plus the requesting user's existing structure-editor role. This is model and
authorization acceptance, not an actual archive-data mutation test.

### Path from home.org rehearsal to production

1. Retain the synchronized GraphDB baseline and inventory (versions, data,
   accounts/roles, media, operations, writer Redis, policies and timers).
2. Rehearse a coordinated source backup/restore and retain unchanged GraphDB
   exports/checksums. The native Jena backup tool cannot back up GraphDB storage.
3. Build/pin migration releases for API/lib, tools and all direct writers;
   verify mediahelper's reviewed authorization fixes. Prepare the candidate.
4. Initialize ONLY a new Jena dataset; migrate source RDF-star to RDF 1.2 and
   canonical relationships using the retained migration reports. Migrate real
   identities/roles and configuration; rebuild the managed fulltext index.
5. Use isolated object caches and explicitly reconcile writer generation/state.
   Preserve receipts and operations; never reuse source coordination blindly.
6. Complete full API/media/permission/read/write/recovery comparisons on home.org.
   Automate coordinated activation and routine update in this repository, using
   the existing inventory/Vault/writer workflow. Do not activate production first.
7. For production repeat the accepted process with final writer freeze, consistent
   export, verified backups, reviewed settings and endpoint switch. Reopen writers
   only after acceptance. Before target writes, rollback can restore the unchanged
   source and matched application configuration. After target writes, rollback
   requires explicit data reconciliation; switching the URL alone loses changes.

The detailed migration source of truth remains
`../oldaplib/docs/migration/graphdb-to-jena-cutover.md`. Record every deployment
acceptance and exact release there. Preparation, migration, activation and
routine updates are distinct steps. Home source migration/activation is accepted;
production-specific gates and coordinated routine updates remain open. The home
mobile worker needed forced shutdown after 90 seconds with empty operation
folders; graceful shutdown needs correction before production. Existing
mediahelper delivery passes, but its reviewed authorization fixes still require
a matched release and broader acceptance.

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

## Dedicated archive writer coordination

WR-01 deployment and recovery prerequisites are documented in
[docs/writer-deployment.md](docs/writer-deployment.md). The feature is explicitly
disabled in existing inventory until coordinated rollout. Owner and consumer VMs
share one TLS-protected persistent Redis store; the ordinary cache is unchanged.

## SALSAH frontend

SALSAH has a separate immutable Docker image and an opt-in Compose overlay. See
[the SALSAH deployment guide](docs/salsah-deployment.md) for initial installation,
trusted multi-frontend email configuration, rollout order and rollback.
`make deploy-salsah-vm` / `make deploy-salsah-home` update only SALSAH;
combined deployments include it after installation. Existing deployments without
SALSAH retain their current services and legacy email destinations.

## Docker API worker configuration

Worker/thread counts are now explicit Ansible settings, with defaults preserving
the existing 4-worker/2-thread runtime. The dedicated `oldap-api-workers.yml`
maintenance playbook changes only those settings on compatible installations.
See [API workers, cache maintenance and isolated crash recovery](docs/api-workers.md)
for prerequisites, rollback and two/four-worker rehearsal commands.

### Updating active home clients after a service-authentication fix

`oldap-jena-proxy-update.yml` repairs the existing home Caddy matcher and recreates
only Caddy after validating its new bind-mounted file. Atomic file replacement
requires recreation: reloading inside the old container reads its old inode.
Only `/internal/jena` and `/internal/jena/*` are proxy-blocked. Export, import and
mobile worker routes must reach their existing purpose-specific JWT guards.

`oldap-jena-client-update.yml` accepts explicit immutable API/tools digests for
an already active home Jena installation. It preserves the installed environment
and policy overlays, pulls images, then recreates identity verification and API
without restarting the Jena namespace owner, Redis or media workers. It neither
imports data nor starts tools. Use the normal prepare/build/accept/publish release
workflow before this update; never reuse a stable or existing RC tag.

API-owned worker service connections must issue internal access tokens with Jena;
GraphDB retains tokenless service connections. Worker signing credentials and
public API signatures do not change. Acceptance must include a real queued export
reaching READY with a valid ZIP, beyond unauthenticated route and public read checks.
The disposable network acceptance now uses the separate identity process on 8001,
checks its bridge isolation, and removes both consumers before replacing Jena.

## Preparing the OLDAP 1.0 merge

See [the coordinated merge and release plan](docs/jena-1.0-merge-plan.md) for
branch evidence, version/dependency work, PR drafts and remaining release gates.


### Offline home Jena snapshot before a client update

For opt-in publication and a verified external pull to Studio, see
[the home snapshot pull runbook](docs/home-snapshot-pull.md). For local Borg
versioning, retention and backup-file restoration on Studio, see
[the home Borg runbook](docs/home-borg.md). The successful isolated application
restore and its limits are documented in [the home restore runbook](docs/home-restore.md).

`oldap-jena-home-backup.yml` snapshots the already active home Jena system;
`oldap-jena-freeze.yml` remains the first-cutover GraphDB workflow. The snapshot
playbook deliberately fixes the two home hosts, inventoried containers and paths.
Run with one operator and no external/direct writers. It refuses unexpected
running containers and existing snapshot directories. It stops media ingress and
writers, API ingress/clients, then Jena and Redis; it preserves application files,
media operation registries, configuration, dataset and coordination state in
private per-host tar archives. Archive comparison occurs while sources remain
stopped, followed by SHA-256 and a completion manifest on the API host. A partial
snapshot without that manifest must not be used as a completed backup.

```sh
ansible-playbook -i inventory.ini oldap-jena-home-backup.yml \
  -e snapshot_id=UNIQUE_IDENTIFIER \
  -e @/absolute/private/home-become.json
```

The legacy home mobile worker ignores SIGTERM as PID 1. For that installed
version only, `-e mobile_stop_signal=SIGINT` can stop an unused worker: admission
requires every mobile registry table to be empty after helper/ingress shutdown.
Do not use this for active mobile work. Deploy proper worker signal/drain handling
before general production backups. Exit 137 aborts snapshot acceptance.

The `always` recovery starts storage, waits for Jena, then force-recreates the
identity/API consumers in its new network namespace before reopening ingress and
workers. Recovery failure leaves ingress closed; inspect before manual recovery.
Tests execute these actual recovery tasks with a fake Docker CLI and injected
storage/readiness/identity/API failures. This is same-host recovery evidence,
not an off-host restore rehearsal. Normal automatic Jena restarts still need
coordinated consumer recovery; this snapshot workflow alone does not solve that.

### Jena memory budget

The Jena container now has separate heap/direct-buffer budgets and a hard total memory limit. See [the memory runbook](docs/jena-memory.md) for sizing, the guarded home rollout, rollback and load evidence. Use `oldap-jena-memory-update.yml` for an existing home deployment; candidate preparation writes all three settings.

### Automatic Jena namespace recovery

Home can install `oldap-jena-recovery-install.yml` to reconnect API/identity clients after a backend crash. The host timer compares real namespace identities and cooperates with planned maintenance. See [the recovery runbook](docs/jena-recovery.md) for bounded retries, pause/resume, diagnostics, disabling the feature and the explicit home fault test.

Current Jena release/operating gate: [release operations](docs/jena-release-operations.md),
including explicit snapshot health checks and remaining production acceptance.
