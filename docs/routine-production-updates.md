# Routine Jena application updates

The shared workflow is implemented in `oldap-jena-update.yml` and
`scripts/update-jena-applications.py`. It supports the installed home overlay
layout and consolidated production layout. Home preview, application update, browser reads and unchanged replay passed on
2026-11-10. Production use and a live rollback rehearsal remain separate steps.
See `home-routine-update-20261110.md`.

## Commands

Run from `OLDAP/oldap-setup`:

```sh
make show-release
make plan-home
make deploy-home
make plan-vm
make deploy-vm
```

Planning reads the installed Compose configuration and prints current/desired
image references. It does not pull images, change installed configuration or
start containers. Ansible transfers its temporary script as usual. Both modes
need the existing SSH/sudo access; no local Vault or server secrets are copied
into Git. Use the normal sudo prompt, or an existing protected Ansible vars file
via `ANSIBLE_BECOME_ARGS`. Do not put a password into Make variables/commands.
Home's sudo implementation is selected by inventory; it is not forced onto
production. Exactly one host must be selected. Ansible `--check` is rejected;
use the explicit plan targets instead.

## Release selection

`RELEASE_FILE` defaults to `releases/current.json`, containing verified published
image digests. It is a partial selection: omitted components retain their current
versions. Currently it selects API/library 1.0.1, tools 1.0.1, FasnachtsPage 0.1.51
and standard/OCR harvesters 0.1.14. App and SALSAH remain at their installed versions.
Update this file only after publication and image acceptance, recording evidence.

A custom file can select just one component:

```json
{"api": "lrosenth/oldap-api@sha256:REPLACE_WITH_VERIFIED_64_HEX_DIGEST"}
```

```sh
make plan-home RELEASE_FILE=/absolute/path/release.json
make deploy-home RELEASE_FILE=/absolute/path/release.json
```

Allowed keys: `api`, `app`, `fasnacht`, `tools`, `salsah`, `harvesters`,
`harvesters_ocr`. API also selects its identity consumer. Only approved repository
names and immutable SHA-256 references are accepted; mutable tags/latest are not.
Absent optional components are reported as `not-installed`; no new service is
provisioned. In particular production currently has no persistent tools service.
`make show-versions` remains repository information, not deployment selection.
Legacy `API_VERSION=...` and related command-line overrides are rejected for these
four targets rather than silently deploying a different release.

## What apply does

1. Acquire installed coordination locks without waiting. The namespace-recovery
   lock is always required. The backup/harvester lock is also required whenever
   its directory, lock, scheduler service or scheduling overlay exists. An
   unscheduled home installation without batch coordination needs only recovery
   locking; no unused dummy lock is created. Missing required or busy locks fail
   before configuration changes. Manual home snapshots remain single-operator
   operations and must not overlap deployment.
2. Resolve all installed Compose profiles, require Jena and its identity service,
   pull selected images and check Python Jena compatibility / tool CLI startup.
   The OCR image additionally imports its isolated CPU runtime without network.
3. Build image-only overrides and verify with real Compose that no other service
   fields change. Changed input files abort preflight. All expanded configuration
   (which contains secrets) stays in process memory and is never printed.
4. Save private rollback files, then atomically select small managed image
   overrides through `.env`. Existing base/overlay contents are retained.
5. Compare actual running image IDs. Replace only changed application consumers,
   with `--no-deps --wait`. API/identity are coupled and identity goes first.
   Verify API/backend readiness and unchanged namespace/Redis container IDs.

Tools and harvester services are never started by apply. Only future manual or
scheduled jobs use the new selections. No source import, migration, initialization,
service provisioning, timer change, signing-key rotation, media-VM deployment,
or infrastructure restart is part of this workflow. Preview compares configured
references; apply resolves actual image IDs, so pinning an already-running image
does not needlessly restart it. Repeating the same selection is a no-op.

Finish active interactive work before an application replacement. Existing locks
coordinate backups, harvesters and recovery; they do not block ordinary API users.
Container/CLI compatibility checks are not a substitute for home functional
acceptance, a live OCR recognition test, or release-specific data tests.

## Files and recovery

Managed files in `/opt/oldap/compose`:

- `routine-images.yml` for installed API/identity/frontends/tools.
- `routine-europeana-images.yml` and `routine-swisscovery-images.yml` for batches.
- `.env`: only `COMPOSE_FILE` and explicit provider Compose selectors change.

Partial releases preserve previously selected component images. Existing
selectors, secrets, policy/model mounts, application settings and schedules
remain authoritative. Existing home batch selectors are derived using the same
rules as the installed launcher, then made explicit. New managed files belong
to the deployed configuration and must be retained in its backups.

Each change has a private `routine-update-<timestamp>` directory containing
previous versions and a manifest identifying originally absent files and changed
consumers. Activation failure restores the written files and the previous
consumers. An unsuccessful rollback reports its directory and requires operator
inspection; do not blindly retry. A concurrent change is never overwritten during
rollback. A killed controller/process may require manual recovery from the same
manifest: hold all installed coordination locks, restore recorded files, remove only files
marked originally absent, then activate the recorded consumers in identity/API
order. Do not restore the database for an image-only rollback.

`oldap-jena-client-update.yml` is a compatibility wrapper around this implementation
for older explicit API/tools image arguments. `oldap-update.yml` is retained only
as the legacy GraphDB/Writer updater. The Make targets no longer call it or the
first-install `oldap-deploy.yml`. Initial provisioning and database/Jena runtime
upgrades remain separate reviewed operations.
