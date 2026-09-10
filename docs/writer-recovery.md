# WR-02 operator recovery (not yet activated)

The shared library now understands a persistent recovery barrier. Upgrade **all**
writers and the writer ACL together before enabling recovery; old processes do not
understand the barrier. Native MacBook services are not controlled by this Docker
operator. Rehearse runtime control in WR-04 before enabling it on any actual target.

## Configuration and privileges

Set `oldap_writer_recovery_enabled: true` only for a reviewed compatible rollout.
Supply distinct 64-hex Vault secrets `oldap_writer_recovery_password` (API) and
`oldap_writer_operator_password` (offline operator). Configure the absolute IRI of
an ordinary OLDAP role in `oldap_writer_recovery_role_iri`; the suggested local name
is `WriterRecoveryOperator`. Explicitly selected users receive membership through
oldap-app. No object UPDATE/DELETE permission or ontology addition is necessary:
this is a deployment-wide operational capability, not a resource-edit permission.
No roles or memberships are created by Ansible.

The generated Redis ACL has three identities:

- `writer`: normal gate writes and barrier reads.
- `recovery-api`: gate/barrier/operation journal writes; evidence/controller reads.
- `recovery-operator`: evidence, runtime checkpoint and controller writes; gate,
  barrier and operation journal reads. It cannot release the application gate.

Only the API gets the recovery-service credential. The operator secret never enters
an application container. ACL selectors grant EVAL invocation access to the relevant
key namespace; **inner Redis commands still enforce the narrow command/key rules**.
This is necessary because EVAL classifies its declared keys conservatively as RW.
Actual tests reject forbidden SET both directly and inside Lua. See the official
[Redis EVAL contract](https://redis.io/docs/latest/commands/eval/) and
[ACL selectors](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/).

## Reviewed offline inventory

Create a private JSON file (0600, owned by root or the operator) on a trusted control
host **outside the containers being removed**. Paths/credentials below are examples;
never check actual credentials into Git. Every domain member and direct-writer
service must be represented. Include one-off tools and harvesters, stop schedulers,
and prohibit uncoordinated raw SPARQL maintenance throughout recovery.

```json
{
  "domain": "example-test",
  "nodes": [
    {
      "name": "vm-one", "transport": "ssh", "target": "operator@vm-one",
      "project": "oldap", "writerServices": ["oldap-api", "oldap-tools", "oldap-harvesters"]
    },
    {
      "name": "vm-two", "transport": "ssh", "target": "operator@vm-two",
      "project": "oldap", "writerServices": ["oldap-api", "oldap-tools", "oldap-harvesters"]
    }
  ],
  "databaseNode": "vm-one",
  "databaseService": "graphdb",
  "queryEndpoint": "https://direct-database.example/repositories/oldap",
  "databaseUser": "operator-read-account",
  "databasePassword": "FROM_VAULT",
  "operatorRedisUrl": "rediss://recovery-operator:FROM_VAULT@writer.example:6379/1?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/private/path/ca.crt"
}
```

Use the real Compose project label (do not infer it from container names), the
actual GraphDB owner and a direct query endpoint to that server. No request-queuing
proxy or uncontrolled orchestrator is supported. The control host needs existing
verified SSH host keys, Docker operational permission and trusted TLS routes to
Redis/GraphDB. For a single Linux host, `transport: local` uses that host's explicit
`unix:///var/run/docker.sock`; it does not inherit an unrelated Docker context.
A host-only writer service may require an operator on its private network. Do not
open a public Redis port merely to make recovery reachable.

Calculate `oldap_writer_recovery_inventory_sha256` using
`oldaplib.src.writer_recovery_operator.inventory_digest(protected_json(path))`.
Review the inventory against `oldap_writer_members`, service/one-off writers and
the actual database endpoint **before** installing its digest in the API config.
Every member must have the same digest. The API journal binds this digest; the tool
refuses a different inventory even if someone reuses the same domain name.

## Two-phase recovery

1. The authorized backend `begin` records actor/reason and freezes an exact gate
   revision. The future WR-03 route supplies the UUID operation ID. No writes can
   enter or normally release this barrier. Starting recovery is a global maintenance
   action, not a harmless stale-lock check; it cannot simply be cancelled.
2. Run `python -m oldaplib.src.writer_recovery_operator --config /private/domain.json
   --operation UUID`. It inventories every host first, removes all listed writer
   containers, verifies GraphDB process termination, starts GraphDB, and persists
   the runtime checkpoint. Existing Redis and its operational journal stay running.
   No database data volume or application medium is deleted.
3. Start fresh compatible API containers for authentication/reads. They remain
   write-blocked. Wait for GraphDB readiness, inspect committed operation receipts,
   affected RDF and old request logs. Do not replay uncertain writes or restart job
   consumers yet. Reconcile the unregistered-request window explicitly.
4. Write a private reconciliation JSON with the exact gate revision, operator name,
   `checks` (unique `label`, SELECT/ASK `query`, exact SPARQL JSON `expected`), a
   `transactions` map keyed by every transaction URL in the journal, and an
   `unregisteredRequests` conclusion. Each conclusion needs `outcome` (`committed`,
   `rolled_back`, `no_write` or `mixed_reconciled`), a concrete `explanation` and a
   nonempty list of referenced check labels. Use focused, deterministic queries;
   ORDER BY matters for exact SELECT result comparison. URLs in the transaction map
   are labels only; the tool never follows them. Unknown outcomes cannot be approved.
5. Run the same command with `--report /private/reconciliation.json`. It verifies
   the same database process, runs the reviewed read-only queries, compares actual
   results, and persists immutable evidence through the operator-only ACL identity.
   The tool checks observations; the operator remains responsible for the semantic
   interpretation. A tautological query is not a valid operational investigation.
6. An authorized backend `finish` rechecks current role membership and releases the
   exact gate only when this evidence exists and no controller is active. Its audit
   result, including evidence, remains in Redis after release. Retry/status uses the
   same operation UUID; never automatically replay the uncertain archive mutation.
   Resume ordinary writers and invalidate/recheck any affected resource cache as
   part of post-recovery verification.

## Interrupted controller and durable state

There are no expiring controller leases. A failed or interrupted operator command
retains `oldap-api:staging:recovery:controller`, because a timed-out SSH command can
still be executing on a remote host. No browser action removes it. The host operator
must terminate/reap the old controller and verify completion/termination of its
SSH/Docker commands on **all involved hosts**, preserve the record, then compare
and delete **only that exact controller record** using trusted Redis administration.
Never delete the recovery barrier or mutation key to bypass this investigation.
The controller may then repeat fencing; existing evidence makes exact retries
read-only. An inaccessible host means recovery stays blocked.

The operational journal shares the existing dedicated persistent writer volume;
it adds no third service and contains no media. Preserve its AOF with the gate.
There is no automatic journal expiry/pruning in WR-02. Monitor disk use; a missing
or restored-old volume still needs full controlled reconciliation, not bootstrap.
An acknowledged completion is retained independently of the deleted gate. A lost
WAITAOF/HTTP response is resolved through the same operation's status.

## Acceptance boundary

WR-02 tests real AOF Redis races/restart/ACLs and backend revocation, plus deterministic
runtime-control/reconciliation tests. Full real Docker GraphDB restart, multi-host
partition/remote-command interruption, native MacBook runtime adaptation and both
UIs are WR-03/WR-04 acceptance. Do not enable recovery on a topology the controller
cannot prove safe. No running application or production service was changed here.

## WR-04 native development MacBook

The checked `oldaplib.src.writer_recovery_macos` controller adds a local launchd
inventory alternative; Docker/SSH remains the production topology. Native services
must be private, hash-pinned LaunchAgents with KeepAlive, bounded ExitTimeOut and
AbandonProcessGroup=false, running reviewed foreground programs without daemonized
children. The local API uses `scripts/native-services.py api --environment FILE`;
its single threaded development process deliberately disables the reloader.
The Redis entry point `native-services.py redis --binary PATH --configuration FILE`
refuses missing AOF manifests and unsafe persistence settings; Redis rejects corrupt
storage with aof-load-truncated=no. No bootstrap/reset path is exposed.

The native inventory uses `runtime: macos-launchd-v1`, `domain`, `databaseService`,
`queryEndpoint`, `operatorRedisUrl`, and `nativeServices` containing `label`, absolute
`plist` and `sha256`. It has no `nodes`/SSH fields. Publish `inventory_digest(config)`
as the API's configured digest only after reviewing every direct writer. A live
recorded owner outside this host's writer services is refused. The operator uses
kernel exit events and launchd job removal, then restarts fresh API/database
processes behind the recovery barrier. Plists or service generations changing
between fencing and reconciliation require a new reviewed fence.

Real disposable GraphDB 11.3.1 and Redis 8.6.3 native tests are in
`tests/probe_native_recovery.py`; this requires an explicit local test license and
uses isolated data, ports and UUID LaunchAgents. No license/credentials are copied
to Git. `tests/test_native_services.py` verifies missing/corrupt AOF refusal.
The existing pinned Redis/container probe also passes all 15 checks. Actual local
runtime/role activation, backups, both UIs and limits are documented in
`FasnachtsPage/docs/wr-04/README.md`. Production inventory remains unmodified and
opted out pending its separate multi-host/reboot/restore acceptance.
