# Jena operational supplement — 2026-11-08

Deployment update: use `package-registry-01` / `batch-registry-01` as described in
`production-image-preload.md`; the earlier packages below remain provenance.

This supplement prepares batch launchers and matched snapshots for the accepted
consolidated production core. It does not install production jobs, enable timers,
change mail transport or activate Jena. The core package remains immutable.

## Explicit provider selection

`prepare-production-batches.py` combines the resolved **production** Europeana
and Swisscovery services with the target core's Jena connection/signing/policy
settings. It preserves provider commands, credential/configuration mounts, OCR
resource limits and report paths. It rejects unknown environment keys, mounts
outside the provider root and mutable image references. Legacy coordinator
credentials/mounts are omitted. Both jobs share the Jena namespace and retain
maintenance exclusion; Swisscovery also retains its own nonblocking flock.

The private `batch-01` supplement contains pinned provider overlays, existing
reporter/lock programs and corrected launchers. Merge `selectors.env` into the
installed `.env`; **never replace the core `.env` with it**:

```dotenv
OLDAP_EUROPEANA_COMPOSE_FILE=docker-compose.yml:batch-europeana.yml
OLDAP_SWISSCOVERY_COMPOSE_FILE=docker-compose.yml:batch-swisscovery.yml
```

These literal file lists override legacy filename-based selection. Missing
explicit files fail before starting a job. All paths resolve relative to the
launcher directory. Existing GraphDB and layered home selections remain usable.
`--help` and other explicit arguments replace provider defaults; absent arguments
preserve the resolved command list, including whitespace. No CLI/API signatures
in oldaplib or the harvesters changed.

Install the entire supplement together, including `harvest-schedule-compose.yml`
and `run-locked.py`; preserve `/etc/oldap-harvest.env` and the verified existing
mail reporter. Check actual images, read-only inputs, OCR model, target identity,
provider membership and maintenance lock before enabling any import/timer.

## Shared snapshot producer

`tasks/jena-snapshot.yml` is the single snapshot implementation used by the home
and production wrappers. The production entry point is
`oldap-jena-production-backup.yml`; it refuses GraphDB and requires
`production_backup_approved=true`. Its target root is explicitly the reviewed
`/srv/storage/oldap-jena-production-20261108` release. Review roots when creating
a future release; do not blindly change the directory on an old playbook.

Before stopping services, every running bind mount must be covered by an archive
root. Only SIPI's rebuildable cache is excluded. The updated source lists include
oldap-app state and the entire media deployment directory, including proxy data
and configuration. Frontends and image delivery also stop for the offline copy;
previous snapshots did not claim coverage of those additional directories.

Production additionally includes provider state, operational helper scripts,
systemd unit definitions and harvest mail settings. The play acquires the existing
`/srv/storage/oldap-data/job-locks/maintenance.lock` via an independent systemd
process, then verifies its readiness marker before maintenance. Native compaction
is allowed to finish. Archives are compared offline, services recover in namespace
order, and hashing/publication follows recovery. A copy, comparison, recovery or
hash failure must not publish `ready.json`.

On failure, the production lock intentionally remains held, preventing scheduled
harvest/backup jobs from racing manual recovery. Inspect the failed phase and
restore services first. Only then stop the exact recorded lock unit
`oldap-jena-backup-lock-SNAPSHOT_ID`. Never unlink/recreate the shared lock inode.
Do not assume a stopped Ansible process implies the maintenance lock was released.
A lock-acquisition failure stops before any writer; a snapshot failure can require
operator recovery even if Ansible's `always` recovery was attempted.

The wrapper currently provides a **manual, tested-local producer entry point**.
Its unattended controller/SSH/sudo arrangement, backup SUCCESS/FAILURE mail and
timer replacement remain installation/acceptance work. Do not point the old
GraphDB timer at this playbook without that wiring and its failure-mail test.

## Explicit receiver environment

The existing `pull-home-snapshot.py` filename and default behavior are retained
for deployed Studio compatibility. Production requires both
`--environment production` and an explicit `--ssh-config`. The approved endpoint
pair is fixed locally to `dhlab-oldap.dhlab.unibas.ch` and
`dhlab-iii.dhlab.unibas.ch`; a downloaded manifest cannot select another server.
Wrong host/path/ID/size/hash or a changing ready marker prevents acceptance.
Partial transfers remain in `incoming`; only the final rename publishes the pair.

Use Homebrew Python explicitly on the office Mac (`/opt/homebrew/bin/python3`,
observed 3.14.5). Its default SSH PATH selected Apple's `/usr/bin/python3`, which
requires Xcode license acceptance; no license was accepted. This does not affect
existing Borg: its executable has its own Homebrew Python interpreter. The
supplement was independently verified with `/usr/bin/shasum`.

Example **after production producer publication and SSH policy installation**:

```sh
/opt/homebrew/bin/python3 pull-home-snapshot.py SNAPSHOT_ID \
  --environment production \
  --ssh-config /Users/rosenth/.ssh/oldap_production_backup.conf \
  --root /Users/rosenth/OLDAP_BACKUP/jena
```

The production SSH policy in this example is a prerequisite, not an assertion
that the file has been installed. Keep historical GraphDB backups and the existing
receiver job unchanged until the matched-pair/Borg/notification replacement passes.
Production Borg encryption/key recovery and unattended scheduling remain separate
acceptance gates; home defaults must not silently choose production encryption.

## Evidence and retention

- Eight schedule/launcher tests pass; real network-isolated Compose execution
  passes eighteen backend/provider/argument combinations.
- Both actual accepted provider images pass CLI help and Jena library import with
  networking disabled. Real target Compose resolution verifies target signing,
  Jena keys, image pinning and maintenance mounts without starting jobs.
- Six receiver tests cover interruption, corruption, changed publication and
  explicit production endpoints; two mount tests cover omitted/sibling roots and
  unsupported named state. Actual target definitions cover twelve API and
  eighteen media bind mounts.
- Five shared backup/recovery tests exercise success and injected failures.
  Seventy production tests pass, including lock lifetime and provider boundaries.
- Private archives `candidate-batch.tar` and `candidate-operations.tar` are retained
  with their SHA-256 manifest on the office Mac under
  `OLDAP_BACKUP/releases/production-operations-20261108`; all three files were
  rehashed remotely and compared. These supplements are **not installed**.
- Full updated home snapshot acceptance is recorded separately in the result JSON.

Final production release readiness still requires image preloading, final source
freeze/drift checks, all nine private target checks and operational installation.

## Full-size home acceptance

Snapshot `20261108-operations-acceptance` passes the actual updated producer,
offline source comparison, recovery, ready publication and Studio pull with exact
size/SHA-256 and manifest equality. Restore boundary validation accepts all 208
API and 6,925 media archive members. All fourteen services run; nineteen API
checks pass (30 stories, 100 archive results, 10 word-order-independent AND hits
and the expected signed JPEG). HTTPS health/frontends pass and the native console
still requires authentication. No application data was imported.

Producer elapsed time was about 21m49s, including hashing after recovery; the
measured API ingress interruption was 18m00s. This exceeds the earlier 11m25s
measurement. The added media archive content is only about 60 KiB; no evidence
establishes the reason for the I/O timing difference. Plan production maintenance
with margin rather than promising the earlier best measurement. No new Borg
archive or full application restore was run in this step; prior Borg/application
restore evidence remains separate.
