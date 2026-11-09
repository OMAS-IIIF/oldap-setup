# Home application candidates

This rollout includes oldap-app, SALSAH, FasnachtsPage and mediahelper plus its
three existing workers. Core API/Jena, identity, Redis, SIPI and data stay on their
installed versions. The API is recreated only to load additive SALSAH CORS/mail
configuration; the Jena namespace owner is not restarted.

## Source and image selection

`python3 scripts/prepare-jena-app-images.py <new-private-bundle-directory>` freezes
allowlisted files from sibling migration checkouts, including reviewed uncommitted
changes. `sources.json` records file hashes, source commits and candidate tags.
Build the recorded Dockerfile with `docker buildx build --platform linux/amd64`,
label `org.oldap.source.sha256` with the full fingerprint, and validate runtime
behavior before pushing only the new `jena-…-amd64` tags. Existing tags are never
reused. Record the registry digest and deploy `tag@sha256:…`.

The 2026-11-04 bundle is in the operator's Application Support directory at
`OLDAP-Jena/releases/20261104-apps-rc1`; build/push logs and source manifests stay
there. Sanitized deployment evidence is recorded separately in this directory.

## Activation

Run `oldap-jena-web-update.yml` with inventory limit `oldap_home` and explicit
`jena_app_tag` / `jena_fasnacht_tag` (tag plus digest). It backs up `.env`, pulls
before activation, recreates only the two services and restores the previous
selection if readiness fails.

Run `oldap-salsah-install.yml` with the same home limit and `salsah_tag` (tag plus
digest). Existing `.env`, Caddyfile and any registry/overlay are backed up before
replacement. It validates registry, Compose and proxy configuration before
activation. DNS `salsah.home.org` must point to the API VM, 192.168.1.230.

Media uses sibling `oldap-mediaserver/ansible/update-jena-home.yml`, inventory
`ansible/inventory.ini`, limit `media.home.org`, and `jena_mediahelper_image` as
full digest-pinned image reference. It copies installed Compose configuration,
changes only four helper image selections, validates and stops the workers, then
activates with automatic old-selection recovery on failure. An unused mobile
registry is mandatory for the legacy worker's SIGINT stop. Production still
requires a proper mobile drain workflow.

Supply administrator credentials using the existing private Ansible extra-vars
file, never in command-line literals or repository files.

## Rollback

For the two frontends restore their `.env.before-jena-web-*` selection and run
`docker compose up -d --no-deps --wait oldap-app fasnachts-page`. For SALSAH,
restore `.env.before-salsah-*` and `Caddyfile.before-salsah-*` (plus preexisting
registry/overlay if applicable), recreate only oldap-api, reload the restored
proxy through stdin, and remove only the SALSAH container. Restore the exact
pre-rollout backup rather than an arbitrary older configuration.

For media restore `docker-compose.yml.before-jena-*` and recreate the same four
services after a safe stop. No RDF rollback is required: this rollout does not
migrate or replace persisted data. Keep ordinary production/cutover backups.

## Accepted home activation — 2026-11-04

All four candidates are now published and installed with registry digests. Exact
references, source fingerprints and container identities are recorded in
[jena-apps-home-results.json](jena-apps-home-results.json). Seven protected
stable/latest registry tags are unchanged. Production was not accessed.

- oldap-app: https://app.home.org
- SALSAH: https://salsah.home.org (DNS corrected to 192.168.1.230)
- Fasnacht: https://fasnacht.home.org
- Mediahelper and ingest/export/mobile workers: https://media.home.org

All three frontend images passed isolated HTTP startup. Chromium checks pass for
oldap-app, SALSAH login, Fasnacht stories and archive, without JavaScript or server
errors. Twenty-eight live checks cover API authentication, upload authorization
before form validation, public story/fulltext reads, signed IIIF, signed original
HEAD, invalid capability denial and private-path isolation. API/media CORS accepts
SALSAH; existing API origins remain present. No roles or RDF/media data were changed.

The media suite passed 384 tests and four subtests (20 skipped). The packaged
AMD64 image passed content-toolchain checks and ZIP acceptance/conversion of a
two-second copy of the actual 1946 film: HE-AAC retained, two thumbnails generated,
original file hash unchanged. Three deployed module hashes match frozen sources.
The deployment checks include the profiled-worker regression: real Compose
resolution must include all four workers/helper services using `--profile '*'`.
The first preflight stopped before shutdown when default resolution omitted the
workers; the corrected run completed without forced termination or rollback.

SIPI-2 remains `lrosenth/sipi-2:0.1.0`. SIPI, both proxies, Jena, identity and Redis
retained their container IDs/start times. Only the API was recreated to load the
additive SALSAH registry/origin configuration; its image stayed unchanged.

Installed configuration backups for this operation:

- API `/opt/oldap/compose/.env.before-salsah-20261104T233923`
- API `/opt/oldap/compose/Caddyfile.before-salsah-20261104T233923`
- Web `/opt/oldap/compose/.env.before-jena-web-20261104T234326`
- Media `/opt/oldap-mediaserver/compose/docker-compose.yml.before-jena-20261104T235426`

Authenticated interactive write/upload acceptance and audible HE-AAC playback
remain manual checks. Existing production gates for Jena memory/recovery,
mobile-worker draining and production migration remain unchanged. Source changes
have not been committed, merged or pushed by this rollout.
