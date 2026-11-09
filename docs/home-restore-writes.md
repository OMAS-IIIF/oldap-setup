# Restored write and worker acceptance — 2026-11-06

## Scope and outcome

The disposable Borg-restored dataset from `20261106-studio-staged-03` passes
write/worker acceptance. All mutations occurred in `oldap-restore-staged-03` on
the home API VM, below `/srv/storage/oldap-restore-rehearsal-staged-03`.
The live home dataset and production were not modified. See
`home-restore-writes-results.json` for sanitized evidence.

The test used a newly created editor account with ADMIN_CREATE and the existing
ArchiveMediaEditor/BMG-Archivist roles, not an administrator. A separate reader
role and the public account exercised denied access. It demonstrated:

- Create and edit a private staging folder through HTTP; public edits rejected.
- Upload a real PNG; stored checksum matches the original; public upload rejected.
- Upload and validate a ZIP containing PNG and UTF-8 text, confirm, and import both.
- Transform the single staging upload into an archive medium linked to a new
  archive object; publication preview includes both resources. Apply publishes
  both, and retrying the same operation returns the identical receipt.
- Public users cannot read/publish the draft; after publication they can read
  both resources and obtain signed IIIF metadata and an actual JPEG derivative.
- An explicit reader resource grant permits reading but rejects edits and
  publication. The read-only checks also verify the rejected edit did not persist.
- Build a staging-folder ZIP, download it through Caddy's archived export route,
  verify ZIP CRCs and exact original PNG/text bytes. Range delivery matches the
  full ZIP; missing capability plus a spoofed internal path is refused.
- Stop the ingest worker during the actual import claim using SIGTERM. It commits
  the active import, exits 0 without OOM, and restarts. The dataset contains exactly
  two imported resources, unchanged after additional worker polls. Confirming an
  already imported job is refused; the publication receipt stays unchanged.

The active-job observation is explicit: claim at 22:53:36.199 UTC, SIGTERM returned
at 22:53:36.223, IMPORTED logged at 22:53:36.957, normal exit at 22:53:36.987,
restart at 22:53:37.178. This establishes graceful draining, not arbitrary crash
recovery at every possible commit boundary.

Final audit: all nine restored containers are stopped, no OOM/forced-kill exits;
eight exit 0 and Java exits 143 after SIGTERM. Eight live API-VM container IDs,
images and start times remain unchanged. All 26 live home acceptance checks pass.
Eight local restore/worker/restart unit tests pass.

## Findings and corrections

1. The clone initially had only about 38 GiB free on its 246 GiB filesystem.
   ZIP upload correctly refused HTTP 507 under the mandatory 20% free-space rule.
   Rehashed the Borg-extracted API archive on Studio against the accepted manifest,
   then removed only the duplicate clone `incoming/api.tar` (32,821,770,240 bytes).
   The source snapshot, Studio/Borg backups, manifest, media transport and restored
   tree remain intact. About 69 GiB became free; no capacity safeguard was lowered.
   Repeating extraction now requires recopying that API archive from Studio.
2. The initial restore helper omitted `cap_add`. The ingest parser needs CHOWN,
   DAC_OVERRIDE, FOWNER, KILL, SETGID and SETUID while dropping all other capabilities.
   Preserving this bounded set fixes the rehearsal's PermissionError; parser UID
   and network isolation remain in place. The already stored ZIP retried after its
   unchanged five-minute lease expired and reached READY. No job state was edited.
3. The six-service read rehearsal intentionally lacked media Caddy. Export creation
   worked, but `/exports/.../archive` is a Caddy route, not a Flask download route.
   The worker preparation now adds a private export-only Caddy with the exact
   archived export block and image ID. Only listener/upstream identity changes;
   no host port, TLS issuance, external ingress or live media bind is introduced.
   Its image binary requires NET_BIND_SERVICE even for the private port 8080.
4. User `hasRole` permission annotations are defaults for new resources, not upper
   bounds on existing resource ACLs. The initial viewer fixture assumed otherwise;
   it was corrected to use a distinct reader role with explicit DATA_VIEW on the
   test folder. The expected rejected update may return 403 or a masked 404.
   This was a fixture correction, not an application permission change.
5. Probe phases now use a local file lock to prevent concurrent checkpoint writes.
   HTTP transport exceptions omit capability URLs/tokens from diagnostics.

No API, library or media application changes or new images were required.

## Rehearsal tools and order

The existing six-service `compose.json` remains unchanged. The new `workers` phase
of `scripts/prepare-home-restore.py` generates `compose-workers.json` using the
recorded worker/Caddy image IDs. It refuses to overwrite an existing configuration.
All worker mounts are rebased through the same restore boundary checks. Export
storage is read-only in Caddy. Workers retain their normal lease/poll semantics;
mail remains console-only and callback reconciliation disabled.

Before starting workers, inspect **all owners'** import/export job graphs, not
just the logged-in user's `/imports` list. This snapshot contained three IMPORTED,
two INVALID and two DELETED export jobs, with no unfinished work. Terminal cleanup
or notification reconciliation may run in the disposable copy; no external delivery
is possible. Another snapshot with active jobs requires an explicit bounded plan.

Run the write probe **inside the clone API container**, never the live `oldap-api`:

```sh
ssh rosenth@api.home.org \
  'docker exec -i -e RESTORE_WRITE_PHASE=fixture oldap-restore-staged-03-oldap-api-1 python -' \
  < scripts/check-home-restore-writes.py
```

Run phases sequentially: `fixture`, `zip`, `validate`; start
`scripts/restart-home-restore-ingest.py` on the API VM before `confirm`; then
`imported`, `inventory`, `export`, `exported`, `publication`, `permissions`, `final`.
The restart observer is deliberately pinned to this clone project and sends no
forced kill. Its observation and drain waits are bounded. Keep the worker observer
separate from the sequential API probe phases.

The fixture uses the restored BMG staging area. If a later snapshot changes that
identity, adapt the fixture from a verified read first. Credentials/checkpoints are
private inside `/tmp/oldap-restore-write-state.json`; never print that file.
Only `/tmp/oldap-restore-write-results.json` is sanitized for collection. Keep
fixtures in this disposable clone; do not merge its dataset back into live home.

Run `check-home-restore-isolation.py --workers --root ... --project ...` against
all nine containers. It verifies mounts, no published ports, private bridge with
no host address, memory caps, mail/reconciliation controls, worker API targets,
parser capabilities and blocked connections to live home/internet.

After collecting results, stop the workers and export proxy first, then the six
base services. Retain the stopped clone for inspection. Verify source container
IDs/start times, clone exit/OOM states, and normal live home acceptance.

## Limits

This is a bounded write/recovery acceptance, not a large-media load test or a
complete browser regression. Mobile resumable-upload workers, harvesting and
arbitrary SIGKILL-at-commit scenarios are not covered by this probe. DNS/TLS and
external proxy behavior use their earlier home acceptance; this test covers private
HTTP transport. Fresh-source cutover/rollback, TDB growth/capacity investigation,
release freezing and production backup operations remain separate gates.
