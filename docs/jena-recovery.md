# Automatic Jena namespace recovery

## Problem and scope

Jena owns the private network namespace used by the API and identity verifier.
Docker's `unless-stopped` policy restarts Jena after a process failure, but already
running consumers can remain attached to its old namespace. Container IDs alone
cannot detect this: a restart can keep the ID while replacing the namespace.
Compose dependency restart propagation applies to explicit Compose operations,
not automatic runtime restarts ([Docker reference](https://docs.docker.com/reference/compose-file/services/#depends_on)).

`scripts/jena-recovery.py` is a small host-side reconciler, installed on home
by `oldap-jena-recovery-install.yml` and on production by
`oldap-jena-production-recovery-install.yml`. Both use the shared tasks in
`tasks/jena-recovery-install.yml`. The production entry point stages its timer
disabled; activation follows operational acceptance. A systemd timer checks ten seconds after the
previous check finishes; it does not overlap a running service. See the
[systemd timer documentation](https://freedesktop.org/software/systemd/man/latest/systemd.timer.html).

## Recovery sequence

1. Acquire the recovery lock and refuse work during marked maintenance.
2. Require a running Jena container with the expected Compose service label and
   a ready backend response.
3. Compare actual `/proc/PID/ns/net` identities for backend and persistent clients.
4. Recreate a mismatched identity verifier first, waiting for its health check.
5. Recreate a mismatched API, wait for its health check, then exercise anonymous
   authentication to verify the database/identity path without exposing tokens.
6. Recheck the owner generation during repairs and leave healthy clients alone.

The reconciler never restarts Jena, never recreates batch harvesters/tools, never
changes images and never replays uncertain application writes. The official
Fuseki listener runs in the Jena process and needs no separate reconnection.
This is targeted namespace recovery, not a general service health supervisor.
Missing/stopped containers are respected unless an interrupted repair explicitly
owns them. Unknown labels and Docker failures fail closed.

## Bounded failure handling

Before recreation, the reconciler atomically saves repair ownership in the
root-only `/var/lib/oldap-jena-recovery/state.json`. This permits recovery after
Compose has stopped or removed a container and failed before replacement. It
also survives an interrupted recovery process. A new backend generation resets
retry budgets but retains ownership of incomplete repairs.

There are at most three attempts per client/backend generation, separated by at
least 30 seconds. Exhaustion is reported as a failing systemd service and in the
journal; it requires operator attention. There is no external alert delivery in
this step. Inspect the cause before resetting the budget:

```sh
sudo journalctl -u oldap-jena-recovery.service
sudo systemctl status oldap-jena-recovery.timer
sudo python3 /usr/local/lib/oldap/jena-recovery.py reset
```

Docker output and container environments are not logged. Persistent state holds
only lifecycle identities, attempt timestamps/counters and completion flags.

## Planned maintenance

The shared `tasks/jena-home-stop.yml` pauses recovery **under the same lock**
before quiescing ingress/writers. It waits for an active repair to finish.
`tasks/jena-home-start.yml` resumes only after successful coordinated service
recovery. The legacy identity-install workflow also brackets its namespace
maintenance. Writer quiescence is shared in `tasks/jena-home-quiesce.yml`.

The pause marker is persistent, including across host reboot. An interrupted
maintenance operation therefore stays paused; finish or repair that operation
before resuming. For manual operations that replace/restart the namespace:

```sh
sudo python3 /usr/local/lib/oldap/jena-recovery.py pause
# Perform coordinated maintenance, reconnect consumers and verify readiness.
sudo python3 /usr/local/lib/oldap/jena-recovery.py resume
```

Pause/resume does not itself stop/start application services. To disable the
feature, pause it first and disable/stop `oldap-jena-recovery.timer`. The existing
coordinated start procedure remains the manual fallback. Do not run arbitrary
Compose replacement operations concurrently without the maintenance pause.

## Acceptance and limitations

`oldap-jena-recovery-check.yml` is explicitly home-only and requires
`allow_home_recovery_faults=true`. It inventories/refuses unknown writers,
closes media ingress and quiesces workers using SIGTERM; API ingress closes only
after the mobile worker has finished. An explicit legacy SIGINT override still
requires an unused mobile registry. The API remains available for draining.
The probe then performs a graceful Jena restart followed by a host-side SIGKILL
of the verified Jena PID. The first clean restart allows previous transactions
to finish; no external writers are admitted during either fault.

Docker must restart the killed process and the timer must reconnect both clients
without calling the reconciler manually. The probe checks actual namespaces,
anonymous API access and stability across another timer interval. On failure the
playbook pauses automation and uses established coordinated manual recovery
before reporting failure. This tests restart recovery with quiesced writers;
it does not claim in-flight write/crash or lease-recovery acceptance.

See `jena-recovery-results.json` for measured recovery times, response parity,
tests and source hashes. Mobile SIGTERM draining, off-host restore and longer
write-heavy capacity acceptance remain production gates. There is still a short
interruption during failure/recovery; this is not zero-downtime failover.

## Home result (2026-11-05)

The final installed source passed both fault checks: graceful restart recovered in
11.612 seconds; process SIGKILL recovered in 18.833 seconds. Both remained stable
through the following timer interval. The timer performed the reconnections; no
manual reconciliation command was used during the fault window. All services
were reopened afterward. The before/after read probes pass all 120 requests,
including 96 parallel requests at concurrency 16, with identical common response
hashes. Setup tests: 95 cases, 91 passed and four skipped; 13 focused tests cover
recovery decisions and partial-failure handling. No production changes.

## Production acceptance — 2026-11-09

Installed the home-tested implementation without changing its recovery algorithm.
Thirteen unit tests and installer syntax checks pass. After the first real Jena
backup and complete office restore verification, the timer was enabled; its
healthy check returned exit 0. No production crash was injected. State in
`/var/lib/oldap-jena-recovery` is ephemeral bookkeeping; do not restore stale
maintenance markers. Backup pauses and resumes recovery around planned stops.
