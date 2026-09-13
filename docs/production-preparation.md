# Production preparation before archive migration

`make prepare-vm` provisions configuration and the dedicated writer Redis on an
existing Docker host. It deliberately leaves API/tools/harvesters stopped and
GraphDB running. It does not migrate ontology, roles or data and is not a rollout
completion command. Ordinary `deploy-vm` behaviour remains unchanged.

## Current status

The isolated Docker/GraphDB recovery rehearsal passed; see
`../operator/rehearsal-2026-09-11.json`. A full production backup including system data was restored into isolated GraphDB
11.3.0 on 2026-09-11. All 14 named-graph counts (40,782 explicit triples) match
a subsequent read-only production sample and remain stable after restart. The
fixture and its data volume were removed. Private evidence is alongside the backup
in `../BACKUP/oldap-production-full-2026-09-11_01-22-32.tar.restore-check.json`.
This verifies database restoration, not application login/media acceptance or a
complete host rollback. Production installation, migration and public HTTP/UI
acceptance remain pending. Private deployment flags were enabled locally during coordinated maintenance on
2026-09-11; first provisioning is awaiting the operator-run Ansible command.
Turn first-bootstrap permission off after successful provisioning.

## Required sequence (operator-assisted; do not run ahead)

1. Verify a fresh production GraphDB backup and a usable restore procedure.
   Also retain the current Compose files, environment, service/image inventory,
   and relevant media/configuration backups in protected storage. Record the
   exact versions for rollback. Do not put secrets in Git.
2. Identify and pause schedules, external direct GraphDB writers and media
   ingest/export workers. Stop API, tools, harvesters and any init jobs on the
   API VM. Keep Docker and GraphDB running. This must cover the entire maintenance
   period, including model/permission migration. The playbook's checks are not
   a distributed maintenance fence and cannot stop a concurrent manual restart.
3. Review the version selection (`make show-versions`) and private
   `auth/writer-production/deployment-vars.yml`. For this first installation,
   coordination/compatible-release flags and recovery are explicitly enabled
   only after review; `oldap_writer_bootstrap` is permitted only for the new,
   never-provisioned store. Keep both authentication and writer Vault files.
   The new archive policy must remain unused by normal applications until
   model/roles/data are ready. Never substitute an empty Redis for lost state.
4. From `oldap-setup`, run the following **only when steps 1–3 are completed**:

   ```sh
   make prepare-vm APP_VERSION=v0.2.4
   ```

   The explicit app version retains the currently deployed oldap-app release;
   its newer release is outside this archive rollout. The target loads both
   Vault files and private deployment variables and asks for Vault/sudo passwords.
   Different Vault passwords require suitable `ANSIBLE_VAULT_ARGS` identities.
   Generated disabled inputs intentionally cause preparation to fail closed.
5. Preparation verifies stopped Compose writers before and after configuration,
   skips Docker installation/start, starts only writer Redis, and performs
   read-only storage probes from the participating images. It does not restart
   GraphDB or start normal applications. If it fails, keep maintenance in place;
   configuration may already have changed. Inspect the error before retrying.
6. Apply and revalidate the reviewed minimal model additions, role memberships
   and exact permission migration while writers remain stopped. Preserve existing
   production taxonomy definitions and data. The production migration execution
   procedure is a separate pending step; the prepared permission plan is not
   evidence that migration has run.
7. Install/validate the separate recovery operator, then explicitly start the
   reviewed release with the **same private writer and authentication inputs**.
   Do not use a bare `make deploy-vm`: it does not load the writer inputs and
   guards reject disabling an already provisioned store. The coordinated start
   command and acceptance checks are provided after migration verification.
   Disable first-bootstrap permission after provisioning. Resume schedules and
   media workers only after API/archive/export acceptance.

The Compose guard includes one-off/profile containers by project/service labels
and rejects unidentified service names. It does not discover processes outside
that Compose project. SALSAH-2 is not deployed in this rollout.

## Active maintenance checkpoint — 2026-09-11 01:42 CEST

API and mediahelper/ingest/export services are stopped. The API VM backup timer
and service are inactive; no tools/harvesters are running. Frontends, Caddy,
GraphDB, cache Redis and the media imageserver remain running. Do not resume
writers or schedules before the coordinated activation step. Final full backup:
`../BACKUP/oldap-production-pre-migration-2026-09-11_01-42-41.tar` (private,
archive/success marker verified). User confirms a separate university-computer
media copy; its freshness and restoreability were not independently verified.
No production model/data migration has run at this checkpoint.

## Writer provisioning completed — 2026-09-11

Production prepare finished with `ok=61 changed=15 failed=0`; each participating
image passed the writer storage check. The writer container is healthy, normal
API is stopped and GraphDB has not restarted. First-bootstrap permission has
been reset to false in private deployment-vars.yml. Model/role/permission
migration and operator installation remain pending; keep maintenance active.

## Archive migration completed — 2026-09-11 02:09 CEST

The reviewed production runner completed all model/role/ACL checks. Independent
explicit SELECT verification confirms 363 resource ACLs, the 478 planned changes,
reviewed role memberships/default annotations and two optional Shared properties.
Existing role memberships and admin permissions are preserved. API/media writers
and backup timer remain stopped; Redis writer is healthy. Next: separate recovery
operator installation, then coordinated activation and acceptance.

## First application activation

After the completed migration and operator checks, run on the control laptop:

```sh
make activate-vm API_VERSION=v0.2.23 APP_VERSION=v0.2.4 \
  TOOLS_VERSION=v0.3.12 HARVESTERS_VERSION=0.1.3 FASNACHTS_VERSION=v0.1.37
```

This target loads the same two Vault files and private writer variables as
prepare-vm, requires bootstrap=false/recovery=true and stopped application writers,
skips Docker host provisioning, repeats storage and installed-operator checks,
then starts only API/oldap-app/FasnachtsPage with dependencies=false. GraphDB/init
jobs, tools/harvesters, media services and the backup timer are not started by the
application activation task. API health and export-service authentication are
checked afterwards. This is the first activation boundary, not an unrestricted
redeploy target: after a partial start, inspect state before retrying because the
stopped-writer precondition will correctly reject a running API.

The ordinary deploy mode remains unchanged. All successful checks before first
activation are recorded in CODEX_LOG; public/media acceptance follows separately.

## API VM activated — 2026-09-11 02:22 CEST

activate-vm completed with ok=67 changed=1 failed=0. API v0.2.23 is healthy,
FasnachtsPage v0.1.37 is running, oldap-app remains v0.2.4, and GraphDB uptime is
unchanged. Public health and export-service authentication passed. Media workers
and backup timer remain paused pending media deployment and workflow acceptance.

## Coordinated media upgrade command

From the sibling oldap-mediaserver repository, use:

```sh
make deploy-production IMAGESERVER_TAG=v0.2.1 MEDIAHELPER_TAG=v0.2.11 \
  ANSIBLE_ARGS='-e mobile_media_enabled=false'
```

Effective host configuration already enables both ZIP workers. The explicit
mobile override preserves the pre-rollout service set; host_vars currently enables
the separate mobile worker, so later deployments without this override require
separate coordination. This command upgrades/restarts helper and both ZIP workers,
validates public helper version and IIIF authorization, and may reload Caddy.
The API backup timer remains paused until cross-service acceptance is complete.

## Media VM deployed — 2026-09-11 02:27 CEST

Media deployment completed with ok=41 changed=8 failed=0. Helper and both ZIP
workers use v0.2.11; image server remains v0.2.1. The mobile worker exists only in
created state and is not running. Public helper health/version and unauthenticated
IIIF 401 checks pass. Next: ordinary-user archive/image/export acceptance and
resumption of oldap-backup.timer; do not treat health checks as full acceptance.
