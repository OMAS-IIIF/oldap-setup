# API workers on Docker hosts

## Configuration and deployment boundaries

The API runs one Gunicorn master and multiple workers **inside one Compose
service/container**. Increasing workers does not create Compose replicas or
additional GraphDB/Redis instances. The laptop's native launchd service remains
one threaded process; its recovery implementation is intentionally unchanged.

Ansible host/group variables:

| Variable | Default | Accepted values |
|---|---:|---|
| `oldap_api_workers` | 4 | integers 1–8 |
| `oldap_api_threads` | 2 | integers 1–16 |

Defaults preserve the existing API image configuration. These bounds prevent
accidental extreme settings; they do not infer capacity from CPU count. Values
are rendered as `OLDAP_API_WORKERS` and `OLDAP_API_THREADS` in the protected
Compose `.env`. Compose supplies explicit `GUNICORN_CMD_ARGS` to the API only.
Other settings (bind, timeout and logging) retain the existing values. There is
no preload; each worker initializes its own project context and connection pool.

The eight-vCPU VM is a candidate for a two/four-worker comparison. Local
measurements used **four threads per worker**, whereas the preserved deployment
default has two. Set threads explicitly and keep them constant when comparing.
API and GraphDB compete for CPU/memory when colocated. A pool bound of 32 Redis
connections is per API process, not a deployment-wide connection limit.

`oldap-deploy.yml` validates counts before provisioning. Initial installation of
the worker-aware Compose file is a reviewed configuration deployment using the
normal private inputs. On an existing coordinated host, the established
`prepare` workflow can install configuration while writers remain stopped; it
is broader than changing two settings and requires the usual maintenance review.
Do not use full provisioning merely to tune an already configured installation.

For an **already worker-aware** installation, explicitly quiesce API/tool/
harvester writers and external jobs, then run:

```sh
ansible-playbook -i inventory.ini oldap-api-workers.yml -l oldap_prod \
  -e oldap_api_workers=2 -e oldap_api_threads=4 --ask-become-pass
```

The dedicated playbook:

1. Validates counts and reuses the existing stopped-writer prerequisite.
2. Resolves the installed Compose configuration with the requested values and
   refuses a legacy file which would ignore them, before editing any file.
3. Backs up the installed `.env` with mode 0600, preserving its secrets.
4. Persists only the two worker settings; starts only the API with installed
   images, no pulls, dependency startup or orphan removal; checks readiness.

The prerequisite assumes the existing Compose project naming convention. Keep
external schedulers stopped independently; it is a check, not a writer fence.
Unknown running services are conservatively refused. Resume other writers only
after acceptance. A readiness failure does not automatically roll back: inspect
it in the same maintenance window, then restore the two prior values and rerun
the controlled API start. Never restore an old secrets file blindly if unrelated
configuration changed after the backup.

Routine `oldap-update.yml` releases continue to change only release tags, so
installed worker settings survive image updates. Inventory should also retain
the intended values for future full provisioning. No playbook was run against
a VM as part of implementing this feature.

## API startup and object cache

Deploy an API release containing the worker-safe startup changes before relying
on this workflow. Worker startup populates project prefixes before readiness and
preserves the shared Redis object cache. It requires GraphDB and the anonymous
principal. In a cold Docker stack `depends_on` only orders container startup;
the existing restart policy/readiness checks must allow GraphDB to become ready.

Restart is no longer implicit cache invalidation. If a model/schema rollout or
out-of-band RDF modification needs a full object-cache clear, drain **readers
and writers** and run the API's explicit `clear-object-cache` Flask CLI with the
reviewed runtime environment. That command holds the writer gate and checks
Redis isolation. Normal selective invalidation remains unchanged. Never flush
the writer Redis store. See sibling `oldap-api/doc/performance/README.md` for the
full procedure. The recovery probe does not clear any shared application cache.

## Why Docker recovery already covers multiple workers

The Docker recovery domain controls entire labelled writer containers. It
removes old API containers, checks that they have not reappeared, verifies the
GraphDB process stopped, and starts GraphDB with its existing data volume. All
workers in a removed container are included; it does not rely on a single worker
PID for the shutdown proof. Automatic worker replacement inside a still-running
Gunicorn master does not bypass the shared durable gate or recovery barrier.

Fresh API containers can serve reads/authentication while recovery remains
write-blocked. The reviewed reconciliation and `finish` are still required before
writes resume. Do not introduce an external orchestrator which recreates removed
writer containers during this procedure. Existing explicit inventory, operator
permissions and receipt/outcome reconciliation requirements continue to apply.

## Isolated multi-worker fault rehearsal

The opt-in probe now supports real API worker crash recovery:

```sh
python -m tests.probe_docker_recovery --license /private/test/graphdb.license --workers 2
python -m tests.probe_docker_recovery --license /private/test/graphdb.license --workers 4
```

Run from `oldap-setup` using a Python environment with Jinja2 and PyYAML. Docker,
OpenSSL, the existing `oldap-writer-operator:0.7.18-amd64` dependency image,
GraphDB 11.3.0 image/test license and the configured pinned Redis image are
required. Sibling `oldap-api/oldap_api` and `oldaplib/oldaplib` sources are copied
into a temporary fixture and mounted read-only. The old operator image supplies
Python/dependencies/Docker CLI; **current library source is used for the operator
and current API/library source for Gunicorn**. Both the container working
directory and Gunicorn chdir point at the mounted API source; the fixture refuses
to start if either imported package resolves outside its mounted checkout. This is source-level acceptance,
not acceptance of a newly built release image or a production performance test.

The probe owns UUID-prefixed containers, network and volumes, publishes no host
ports, loads only repository fixture RDF into its new GraphDB, and generates
fresh credentials. It never loads production Vault secrets or connects to the
native GraphDB. The offline operator alone receives the Docker socket; application
containers do not. Cleanup removes only those owned assets, including the fresh
API container started after recovery. `--workers 0` retains the legacy probe.

The test-only `recovery_worker_app.py` wraps the actual `create_app()` and bearer
authentication boundary. Its private fault route uses the real oldaplib writer
gate and Connection transaction methods, inserts a unique uncommitted marker,
and SIGKILLs the serving worker. These routes **must never be shipped or deployed**.
They test transaction/recovery infrastructure, not resource business rules.

The rehearsal checks:

- Gunicorn replaces the killed worker with a new PID.
- Every surviving/replacement worker refuses writer admission before and during
  recovery; a worker restart never releases another process's durable ownership.
- The real operator CLI removes the entire old container and restarts GraphDB.
- Previously committed fixture data survives; the uncommitted marker is absent.
- Every worker in a fresh container remains blocked until evidence and `finish`.
- Evidence and finish retries are idempotent.
- After finish, every fresh worker can obtain the gate, and a real API transaction
  commits a new marker verified directly in GraphDB.

Healthy concurrent writers can legitimately compete for the gate. The final
admission check retries ordinary contention; it requires eventual admission by
every worker, not simultaneous admission by all workers. The global write gate
continues to serialize coordinated writes: worker scaling primarily benefits
reads and does not imply parallel write throughput.

A recovery involving actual data always requires semantic reconciliation; this
fixture's known markers make that check deterministic. It does not cover every
business mutation or every distributed-host failure. Repeat it against the
release image and selected production GraphDB version before deployment.

## Acceptance recorded on 2026-09-30

Both source-verified `--workers 2` and `--workers 4` runs completed successfully,
including real worker SIGKILL/replacement, admission checks for all workers,
container fencing, actual GraphDB restart, marker preservation/rollback, fresh
API startup behind the barrier, idempotent reconciliation/finish and a verified
post-recovery API commit. The existing Docker recovery library logic required
no changes. All 34 setup unit/configuration tests and syntax checks for the
deployment and worker-maintenance playbooks passed.

[Machine-readable acceptance evidence](api-workers-acceptance-2026-09-30.json)
records results, source hashes and limits. Preliminary runs exposed two test
issues: normal gate contention needed retries, and the image working directory
could select bundled API code. Final accepted runs use explicit working
directories and runtime source-path assertions. Application fixture mounts
contain only source code and the CA certificate; operator credentials and
Docker control remain outside the application containers.

No VM was contacted or deployed. The laptop's native API/GraphDB and existing
media containers were left running; the probe cleans up only its generated
containers, network and data volumes. Repeat acceptance against the built release
image before rollout, then measure two/four workers on the actual VM.


## Deployed VM read acceptance — 2026-09-30

After the user's deployment, the running API was verified as v0.2.29 with
oldaplib 0.7.23 and the existing four-worker/two-thread Gunicorn settings on the
eight-vCPU VM. No maintenance playbook, worker change, restart, cache flush or
recovery fault test was executed. The benchmark ran from a private temporary
host directory, which was removed after retrieving its results.

The exact reference-catalog replay and a supplemental catalog with complete
25/100-resource metadata batches produce 2,409 successful timed reads with
stable normalized content. In the complete-batch workload, 16 active anonymous
readers achieve 16.13 requests/s, 232 ms median and 649 ms p95. API CPU averages
2.13 cores versus 0.33 for GraphDB. Explicit named-graph fingerprints remain
identical at 50,396 bindings; all API/GraphDB/cache containers and service PIDs
remain unchanged. Public HTTPS health and representative read routes also pass.

See sibling `oldap-api/doc/performance/2026-09-30-vm.md` for the report, aggregate
JSON/CSV, private artifact location, reproduction instructions and limitations.
The laptop catalog yields only 15/60 visible summary resources on the VM, so its
metrics are kept separate from verified full 25/100 batches. This is a new VM
baseline, not proof of a deployment speedup or a worker-count A/B result. Warm,
short, anonymous read acceptance does not replace an isolated release-image
write/recovery rehearsal or representative HMB-scale testing.


## Released optimization verified — 2026-10-01

API 0.2.30 / oldaplib 0.7.24 is verified on the existing four-worker/two-thread
VM by its actual serializer source hash. Replaying the previous full-batch
catalog completes 1,132 timed reads; all 17 reference contents and the explicit
50,396-binding RDF fingerprint match. At 16 active readers, median latency
improves 232→167 ms, p95 649→591 ms, throughput 16.13→17.03 requests/s and API
CPU 2.13→1.78 cores. The measurement does not require changing workers.

The initial attempt was excluded after a process-list guard failure: transient
container helpers were counted alongside service processes. The benchmark now
filters Gunicorn/Java/Redis commands and retains actual PID-change protection;
19 offline read-tool checks and the complete rerun pass. No application fault,
worker restart or data change was observed. Container/service PIDs remain stable,
public HTTPS reads pass and temporary measurement files on the VM are removed.

See sibling `oldap-api/doc/performance/2026-10-01-vm-serializer.md` and its JSON/CSV
for exact results, the incomplete first attempt and limitations. Keep 4/2;
follow up with Project/model-copy profiling rather than a worker maintenance
change based on this bounded workload alone.


## Project identity release accepted — 2026-10-01

The user-deployed API 0.2.31 / oldaplib 0.7.25 matches the locally tested Project
and PropertyClass source hashes. The existing four-worker/two-thread deployment
passes 1,152 timed reads, all 17 baseline contents and public HTTPS read checks.
Resources improve 10–13%, summaries 4–10%; at 16 readers, median/p95 changes
167/591→143/559 ms and API CPU 1.78→1.57 cores. Throughput changes only slightly,
17.03→17.40 requests/s. Search/fresh-model gains are not demonstrated.

RDF fingerprints (50,396 bindings), container identities and service PIDs remain
unchanged. No deployment, restart, worker change, cache clear, recovery fault or
data write was performed by the measurement. Temporary VM files were removed.
Keep 4/2; this is bounded warm-read acceptance, not sustained capacity or HMB
sizing. See sibling `oldap-api/doc/performance/2026-10-01-vm-project-identity.md`
and its JSON/CSV for evidence and limitations.
