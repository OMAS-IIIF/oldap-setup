# Two-host production rollback rehearsal on the existing home VMs

## Result — 2026-11-08

Passed on both existing home hosts with all fourteen source services. Production
was not changed. The partial-installation case restored 50 API and 12 media
configuration files byte-for-byte and quarantined both injected target selectors.
The private four-service Jena candidate passed status/login, then its native
backend was stopped and port 3031 confirmed unreachable. The shared production
rollback recovered GraphDB, both coordinators, API, frontends and media services.
Both source comparisons matched all thirteen comparable baseline fields.

The first runs identified and corrected missing media `.env` assumptions,
stale target selectors, and retained container network IDs. A test-specific
logical-network collision was also corrected. The final private outage and
rollback ran without manual retry. Source recreation now explicitly uses
`--force-recreate --no-start --pull never`; this retains persistent data while
rebuilding network references and checking exact original image identities.

Normal home Jena roots were then restored. All fourteen active home image IDs
match the retained inventory; readiness, released maintenance and all thirteen
API comparison fields pass. HTTPS returns 200 for API, Fasnacht, OLDAP App and
SALSAH; unauthenticated Fuseki returns 401. The 56 production workflow tests pass.
The Python test environment must include PyYAML (the installed Ansible Python
environment was used). No production schedules or mail were exercised here.

See `home-production-rollback-results.json`. Private detailed evidence is retained
under `~/Library/Application Support/OLDAP-Jena/releases/home-two-host-rehearsal-20261108`.
The independent fresh home safety snapshot is
`20261108-before-two-host-rehearsal`; it passed offline archive comparison and
hash verification. Source/candidate datasets and retired rehearsal roots remain
available; no cleanup was mixed into recovery.

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
5. Run `oldap-home-production-rehearsal-freeze.yml` with a distinct
   `rehearsal_phase` (`partial`, `private`, then `finish`). It drains both hosts,
   checks the legacy mobile registry before SIGINT, verifies idle coordinators
   with the production read-only client, and requires clean stops.
6. Case A: introduce a malformed Compose file after recording installation intent.
   Run `oldap-home-production-rollback-rehearsal.yml`. Both production and home
   wrappers include `tasks/production-private-rollback.yml`; the recovery steps
   themselves are identical. Recheck source API/media results.
7. Freeze again. Case B: replace API/Redis with the already accepted private Jena
   candidate, sharing neither source database nor source operational storage.
   Under project `compose`, give its isolated network a distinct logical key
   (`private_rehearsal`), not just a different physical network name. Reusing
   `default` makes Compose reconcile the retained source containers against the
   wrong network. Keep the source `default` network and its containers intact.
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
The media source requires its separate service environment files, not a global
`.env`. Target-only Compose inputs (including `.env` or `compose.yaml`) are moved
to a private sibling quarantine before source extraction. Redis state is excluded
from both extraction and quarantine. Same-filesystem data renames avoid copying
large datasets during the outage; cross-filesystem configuration uses `cp -a`.
