# Production execution preparation

Status: **two-host pre-opening rollback rehearsed on home, 2026-11-08**.
The shared rollback tasks pass partial-configuration and private-native-outage
cases; normal home is restored. See `home-production-rollback-rehearsal.md`.
This does not approve production activation or replace final candidate/private
acceptance. Keep the historical home-only guards.
See [cutover and rollback plan](jena-production-cutover.md) for source mounts,
retained images, migration rules and the recovery boundary.

## Entry points and boundaries

| Entry point | Result | Recovery boundary |
| --- | --- | --- |
| `oldap-production-source-snapshot.yml` | Drain, export asserted RDF, stop all containers, archive/compare both hosts, resume GraphDB by default | Original containers/configuration remain installed |
| Same play with `retain_source_stopped=true` | Hold the matching source stopped under the maintenance lock | Use source-resume only before replacing configuration |
| `oldap-production-source-resume.yml` | Reopen an unchanged held source after readiness checks | Refuses changed container IDs/images, installation intent or target opening intent |
| `oldap-production-target-private.yml` | Install reviewed bundles; start only new Redis/Jena/identity/API | Requires completed rollback rehearsal; no automatic recovery if configuration installation fails |
| `oldap-production-target-open.yml` | Record durable write intent, then open target services | No automatic return to the old snapshot after intent, even if opening fails |

Use one operator and exclude independent deployment, direct console writes,
recovery automation and scheduled starts throughout the window. The shared
maintenance lock serializes backup/harvesting; it does not fence arbitrary root
commands or all external writers. Coordinate the office pull explicitly.

## First execution: source checkpoint for rehearsal

This step interrupts production and therefore belongs to an agreed maintenance
window, not to tonight's preparation. Preflight fresh capacity, actual mounts,
container/image drift, mobile registry and pending jobs before proceeding.

Create a protected operator variable file outside Git containing a new
`snapshot_id` and the three acknowledgements `production_write_pause_approved`,
`external_writers_excluded`, `office_pull_coordinated`. Set them true only after
the conditions actually hold. Leave `retain_source_stopped` false for rehearsal.

```sh
ansible-playbook -i inventory.ini oldap-production-source-snapshot.yml \
  -e @/Users/rosenth/.config/oldap/production-become.json \
  -e @/absolute/private/cutover-variables.json
```

The source checkpoints are `/srv/storage/oldap-cutover-ID` on API and
`/data/oldap-cutover-ID` on media. They contain separate `api.tar`/`media.tar`,
asserted `source.trig`, sanitized source identities/timer state and a completion
manifest. Environment export inputs remain private. Failed captures do not
publish a completion manifest. Hashes are computed only after stopped-file
comparison and, in rehearsal mode, successful source recovery.

The RDF export checks HTTP/content type/nonempty bytes, **not RDF syntax or graph
semantics**. Conversion, parser validation and graph/domain comparison remain
mandatory before acceptance. Copy both completed archives, RDF and evidence to
the office receiver and verify their hashes there. The manifest alone is not an
off-host backup. Do not edit/reuse partial checkpoint directories.

For the final migration, use a **new** checkpoint and `retain_source_stopped=true`.
To abort before installing target configuration:

```sh
ansible-playbook -i inventory.ini oldap-production-source-resume.yml \
  -e @/Users/rosenth/.config/oldap/production-become.json \
  -e snapshot_id=ACTUAL_HELD_ID
```

This is not a rollback after candidate replacement. `target-installing.json`
blocks that shortcut even if the old container IDs have not changed yet.

## Private candidate contract

Prepare/import a fresh target root `/srv/storage/oldap-jena-production-ID` using
reviewed release inputs and the documented RDF migration. Preserve the complete
source state. Copy required API operational state into isolated target storage;
never mount source API/Redis/GraphDB state writable in the candidate.

Before private activation, prepare **complete reviewed** `candidate-api.tar` and
`candidate-media.tar` in the respective checkpoint directories. The archives are
relative to each Compose directory and must include `.env`, `docker-compose.yml`
and all selected overlay/configuration inputs. Do not archive `.` or Redis data.
Only ordinary files/directories are allowed; no links, traversal, writable group/
world permissions or special permission bits. Environment files are private;
preserve usable directory/file modes for container bind mounts. Existing target
path symlinks are rejected. Review external bind inputs separately: the archive
checksum alone does not cover files outside the Compose directory.

Pin every started image by immutable digest or local image ID. Preload images;
all Compose activation uses `--pull never`. Writable API, Redis and Jena mounts
must be strictly below `TARGET_ROOT/data`, including after symlink resolution.
The validator rejects missing persistence and source/named-volume paths. Jena
has no published port; API and identity share its namespace. Media remains
stopped. Native runtime memory, keys, policy, models, fulltext configuration and
external bind checks remain part of the reviewed release/rehearsal.

Only after the isolated rollback rehearsal passes, add `target_root`,
`candidate_api_sha256`, `candidate_media_sha256`, `private_install_approved=true`
and `production_cutover_rehearsed=true` to the private variables and run:

```sh
ansible-playbook -i inventory.ini oldap-production-target-private.yml \
  -e @/Users/rosenth/.config/oldap/production-become.json \
  -e @/absolute/private/cutover-variables.json
```

An installation intent is saved before changing either host. Failures leave
public ingress closed; do not invoke source-resume, remove the marker or start
old workers against candidate configuration. Use the separately rehearsed
original-config/image recovery below. Partial installation can affect both
hosts, even before any container replacement.

## Required rehearsal before activation is enabled

Using isolated copies of the paired snapshot, exercise the following with exact
retained source images and matching private configuration:

1. Recover the GraphDB source and verify the API comparison fixtures plus media
   authentication. Use isolated networks/paths; no production timers or email.
2. Import/convert the RDF into the separate Jena root and activate the reviewed
   candidate. Keep media writes/tests on cloned storage. Validate all migration
   rules and representative read/write/permission/fulltext/concurrency behavior.
3. Inject failure after API configuration installation and after private API
   activation. Stop candidate clients/identity/Jena, including native maintenance.
   Restore the matching original configuration and explicitly pinned source
   images with pulling disabled. Recreate containers against the unchanged
   source mounts, or restore the entire matched checkpoint into fresh paths if
   any source operational/media state was touched. Never extract a full archive
   over a running datastore or mix state from different checkpoints.
4. Prove GraphDB, both coordinators, API and media readiness and compare the same
   source fixtures before opening ingress/restoring original schedules. Record
   exact commands, hashes and outcomes as the production rollback procedure.

**Step 3 now has a guarded pre-opening runner, `oldap-production-rollback-private.yml`.**
It requires `production_rollback_approved=true` and a held root-owned checkpoint;
it restores original Compose inputs and pinned containers against untouched source
state. Both wrappers use the same tasks. The full fourteen-service home source
passed partial-configuration and private-native-outage recovery on November 8;
see [two-host evidence](home-production-rollback-rehearsal.md). Explicit
container recreation prevents stale network references; target-only Compose
inputs are quarantined. The earlier six-service clone migration/outage/rollback
is documented in [its separate evidence](production-rehearsal-20261108.md).
A Boolean acknowledgement is not test evidence.

## Private acceptance and public opening

Write `private-acceptance.json` in the API checkpoint only from reviewed test
results. Required fields: `status: passed`, the exact `snapshot_id`,
`source_sha256` matching the frozen RDF artifact, `checks` containing all nine
names below, and `images.api` / `images.media` mapping every target container name
to its exact installed image ID. Preserve detailed evidence alongside the report.

Required checks: `data`, `permissions`, `relationships`, `fulltext`, `media-auth`,
`concurrency`, `native-console`, `harvester-backend`, `backup-readiness`.
The play validates completeness and image identity; it does not perform those
application tests or validate their scientific/data-model conclusions itself.

After acceptance, set `production_open_approved=true` and run the opening play
with the same two protected variable files. It fsyncs `target-opened.json` and
its directory **before** starting any ingress or media worker. The marker binds
the acceptance report checksum. A partial/failed opening still prohibits simple
GraphDB rollback: preserve new writes and follow a reconciliation plan.

Old source backup/harvest timers remain paused, and the cutover maintenance lock
remains held. After public acceptance install/verify the **Jena** backup and
harvester wiring, receiver checks and production SUCCESS/FAILURE email path;
then explicitly release the cutover lock and enable the approved schedules.
Never resume the old GraphDB backup job against Jena.

## Original November 7 preparation validation (historical)

- 31 production preparation/retention tests pass, including lifecycle,
  archive/mount, lock contention and durable write-boundary checks.
- Actual Ansible source-resume tasks executed with fake Docker/systemctl:
  identity/storage/repository failures keep ingress and timers closed.
- Ansible syntax checks for all four production entry points.
- No SSH, production pause, target deployment, database import or email was
  performed for this preparation. Real two-host drain/restore remains a gate.
