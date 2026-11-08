# Two-host production rollback rehearsal on the existing home VMs

## Safety boundary and current scope

The owner authorized temporary use of api.home.org and media.home.org on
2026-11-08. This is an outage test, separate from the successful six-service
isolated test. It does not authorize a production cutover.

Start with a fresh verified `oldap-jena-home-backup.yml` snapshot. Keep its
manifest and both archives. `prepare-home-production-rehearsal.py` additionally
captures image-pinned home Compose configuration and preserves original home
roots by same-filesystem renames. Source installation copies go into new paths;
a durable path journal supports recovery even if a copy is interrupted. The
original home native dataset outside those roots remains untouched.

Use only roots named `oldap-cutover-home-rehearsal-*` under `/srv/storage` (API)
and `/data` (media). The helper refuses non-home hostnames and non-root execution.
The test uses production data and source images at their original container names
and paths. URL/origin transport settings are adapted to home, internal API/media
traffic uses HTTP, Caddy has fresh local certificate state, mail is console-only,
and backup/harvest timers are not started. RDF identifiers and service subjects
are not rewritten. The existing home recovery controller stays paused.

The rollback archives for this test contain **configuration only**. Complete
original production snapshots and the new home snapshots remain separate. This
exercises configuration/container rollback against untouched source data, not a
full disaster restore or recovery of post-opening target writes. A rehearsal-only
systemd maintenance unit exercises release ordering; real production file-lock
contention has separate tests.

## Execution sequence

1. Prepare each source tree and private home recovery inputs with the helper's
   `prepare` action; verify image identity before interrupting home again.
2. Capture the normal home API baseline after the safety snapshot recovers.
3. Run `oldap-home-production-rehearsal-start.yml` with `snapshot_id`,
   `home_safety_snapshot`, `home_production_rehearsal_approved=true` and protected
   home become variables. This drains home, retains its roots, installs cloned
   source state, creates all fourteen source containers and uses the real shared
   source-resume tasks. The helper never starts services itself.
4. Accept the source API, permissions, search and signed media. Record actual
   source identities and fixture archive/config hashes in the private checkpoint.
5. Run `oldap-home-production-rehearsal-freeze.yml`. It drains both hosts,
   checks the legacy mobile registry before SIGINT, and requires clean stops.
6. Case A: introduce a malformed Compose file after recording installation intent.
   Run `oldap-home-production-rollback-rehearsal.yml`. Both production and home
   wrappers include `tasks/production-private-rollback.yml`; the recovery steps
   themselves are identical. Recheck source API/media results.
7. Freeze again. Case B: replace API/Redis with the already accepted private Jena
   candidate, sharing neither source database nor source operational storage.
   Confirm private API/native readiness, then execute the same rollback and
   repeat source comparisons. Public target ingress/media must stay stopped.
8. Freeze the restored source once more and run
   `oldap-home-production-rehearsal-finish.yml`. This requires both hosts stopped,
   restores journaled home roots, checks retained image identities, and resumes
   Jena in namespace dependency order. Compare the final home API with step 2.

Do not use plain Compose commands in the temporary `/opt/.../compose` directories:
the retained resolved JSON selects the reviewed home-specific transport settings.
Use `--pull never` and the explicit pinned checkpoint configuration.

On a partial failure, keep services stopped and inspect the path journal. Never
extract a snapshot over a running database. The finish helper refuses a second
path restoration; after paths are restored, retry only container creation/start
as needed. Retain rehearsal datasets until the final home acceptance is recorded.

## Prepared hardening

Both rollback inputs are validated before any candidate drain/config restore.
Media HTTP health and image-server connectivity are required before media ingress
and timer release. Local tests cover checksum/traversal/duplicate rejection,
non-mutating preflight, failed media readiness, and interrupted home path copying.
Actual two-host results will be recorded separately after execution.
