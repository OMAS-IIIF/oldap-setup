# Jena memory budget

The home API VM has approximately 15.1 GiB usable RAM. A previous global host OOM killed Java with about 14 GiB anonymous RSS even though the heap maximum was 8 GiB. That historical peak does not identify which native allocation caused it. The current service also maps TDB/Lucene files: file-backed resident memory and reclaimable cache must not be mistaken for a heap leak.

## Budget

The Compose deployment now defaults to:

| Setting | MiB | Purpose |
| --- | ---: | --- |
| `OLDAP_JENA_HEAP_MB` | 6144 | Maximum Java heap |
| `OLDAP_JENA_DIRECT_MB` | 512 | Maximum NIO direct-buffer allocation |
| `OLDAP_JENA_MEMORY_MB` | 10240 | Hard cgroup budget including heap, native memory and charged file pages |

The swap-inclusive limit equals the memory limit, disabling container swap. About 5 GiB of host memory remains outside this service budget for the OS, API, identity verifier, Redis and frontends. This is a host-specific initial budget, not a universal production sizing rule. Batch harvesters need their own capacity planning; do not assume this reserve covers every simultaneous OCR workload.

`JAVA_TOOL_OPTIONS` adds the direct-buffer bound to the existing immutable launcher. No new Java binary or application image is necessary. The direct-buffer setting is not a limit for all native allocations or all memory-mapped files; the cgroup is the overall protection. Reaching the cgroup cap can still kill Jena, so the load checks must inspect OOM events and headroom. Coordinated automatic namespace recovery remains a separate gate.

Sources: [Docker memory and swap limits](https://docs.docker.com/engine/containers/resource_constraints/), [Compose service memory settings](https://docs.docker.com/reference/compose-file/services/), [Java runtime options](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html). Native memory tracking alone is insufficient for a total bound: [Oracle describes its coverage limits](https://docs.oracle.com/en/java/javase/25/vm/native-memory-tracking.html).

## Home rollout and rollback

Run `oldap-jena-memory-update.yml` with the established inventory and protected become variables. It validates the host reserve, stages and resolves Compose, saves the original environment/Compose privately, and uses the existing coordinated stop/start tasks. These stop media writers before the backend, then reconnect identity/API consumers to the replacement namespace before reopening ingress. The existing legacy mobile SIGINT path requires an unused mobile registry.

On activation failure the playbook restores the saved configuration and recreates the prior backend/consumers. No data format, service JAR, images or API signatures change. The rollback directory is reported at completion. This home-only playbook is not authorization to apply the same budget to production without checking that host's RAM and workload.

## Measurement

Run `scripts/check-jena-memory.py` on the Docker host while `scripts/check-jena-concurrency.py` performs the representative read workload. The memory probe records one-second cgroup counters, anonymous/file/mapped bytes, swap and host available memory, and returns failure if new OOM events occur. The concurrency probe compares complete responses to sequential baselines at 16-way concurrency, including archive metadata, dates, stories and taxonomy. Timing differences across separate rounds include cache and scheduling effects; they are not an engine benchmark.

Acceptance results and limits of coverage are recorded in `jena-memory-results.json`. Read-only loading cannot prove behavior of arbitrary imports, index rebuilds, large future datasets or a long-term soak.

## Accepted home result (2026-11-05)

The rollout completed without rollback. Kernel `memory.max` is 10 GiB and `memory.swap.max` is zero; the Java command uses `-Xmx6144m` and the direct-buffer option is installed. Configuration backup: `/srv/storage/oldap-memory-before-20261105T135940`.

375 requests across six rounds succeeded, including 300 parallel requests at concurrency 16. Common response hashes match before and after. Parallel median times: before 1.1245 / 1.0135 seconds; after 0.971 / 0.8185 / 0.9535 seconds. The additional fulltext round also passes complete-response equality. There is no measured slowdown in this short comparison; cache and scheduling differences prevent attributing a speedup solely to the budget.

The 90-second post-update memory sample peaks at 2.52 GiB, with no new OOM/hard-limit events, no swap and unchanged container lifecycle. Host available memory remains at least 11.41 GiB during that sample. Before the restart, the sample peaks at 9.74 GiB including large file-backed cache. These are **not directly comparable memory savings**: cache residency and ownership of charged file pages change across a container restart. The durable improvement is the enforced total bound and reserved host capacity, not a claimed 75% reduction.

Setup verification: 82 cases, 78 passed and four skipped; both playbooks pass syntax checks. The home activation checks native console readiness before reopening ingress. Automatic failure recovery, mobile draining and production capacity acceptance remain open.
