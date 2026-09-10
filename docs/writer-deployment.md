# Dedicated archive writer store (WR-01)

## Scope and topology

Archive-enabled deployments use a dedicated Redis primary with AOF, fsync always,
no eviction, TLS and a narrowly scoped writer ACL. This is operational state, not
a cache. Existing cache configuration is unchanged. Deployment remains explicitly
disabled in the real inventory until a coordinated rollout selects compatible
API/tools/harvester releases, policy, certificates and secrets.

Each coordination domain has one inventory owner and an explicit member list.
Only the owner receives the `archive-writer` Compose service. Every member gets the
same Redis endpoint, policy, GraphDB target and repository. Members may be added to
an environment group; never enable this globally across unrelated test/production
hosts. A new VM is not an independent lock owner. The general stack playbook still
provisions its existing services; this change is not an application-only VM role.

`templates/writer-compose.yml.j2` augments the existing Compose file. The generated
`.env` selects both files through COMPOSE_FILE. A single-host installation publishes
no Redis host port: clients use the internal DNS alias and container port 6379.
Cross-VM deployments publish only a configured private IPv4 address, use a shared
DNS name and TLS, and restrict forwarding through Docker's DOCKER-USER chain. The
firewall oneshot runs before Docker at boot and is coupled to Docker restarts; it
preserves unrelated rules and is installed before the service is first published.
The supported host firewall backend is Docker's iptables integration. Native Docker
nftables or a different network architecture requires a reviewed equivalent first.

## Inventory and secret inputs

Use `docs/writer-inventory.example.yml` as an environment-group template. Required:

- enabled flag, stable domain ID, owner inventory hostname and complete member list;
- shared Redis hostname (must match the certificate SAN), port and trusted CA file;
- owner server certificate/key files, private publish address/interface and allowed
  source CIDRs when clients span hosts;
- a Vault-supplied random 64-hex-character password (not a human password);
- one reviewed policy JSON file and matching pinned application/library releases;
- shared GraphDB URL/repository; cross-host access requires HTTPS. Optional database
  HTTP Basic credentials are supplied through Vault. Do not put credentials in URLs;
- `oldap_writer_compatible_releases: true` only after the release review includes
  persistent mutation_gate and the selected archive policy features in every writer.

Redis 7.4.6-alpine is pinned to its tested multi-platform digest in group defaults.
Update this pin through normal security/release maintenance and repeat persistence
and ACL tests; never use an uncontrolled latest tag for operational storage.

Ansible renders the ACL with a password hash; raw credentials are confined to
protected generated files and container environments. Certificates rotate by
re-running deployment: file checksum labels force the owner service/client
containers to be recreated where required. Plan rotation with writer maintenance;
existing long-lived connections must not be assumed to refresh trust immediately.

## First installation, restart and loss of storage

1. Quiesce all existing writers, verify backup/restore and review policy/model/roles
   under the AS-09 rollout procedure. Installing this service does not perform RDF
   migrations or provision roles.
2. Configure owner and all members. For the first empty installation only, select
   `oldap_writer_bootstrap: true` explicitly. Ansible bootstraps AOF using a one-shot
   isolated container, then retains a provisioning marker outside the data volume.
3. Reset the bootstrap variable to false for normal operation. An ordinary deploy
   requires the AOF manifest. An existing provisioning marker forbids bootstrap
   after volume loss, even if the flag is accidentally still true. Redis itself
   refuses truncated AOF; the startup guard refuses missing AOF.
4. Start the owner first (or include it in the same default linear Ansible run).
   Consumers-only deployment requires the owner to be reachable already. A
   read-only preflight runs in API/tools/harvester images before the main stack is
   brought up; it checks library availability, selected policy syntax, TLS/auth,
   primary role, persistence settings, WAITAOF and last AOF write health.
5. Never disable or change a provisioned domain/endpoint through a normal deploy.
   External client-contract markers reject such drift. Domain migration requires
   planned maintenance and reconciliation; it is not a variable-only change.

The persistent bind mount is `<oldap_data>/archive-writer`; protected configuration
and markers live below `<env_dir>`. Keep them together in the recovery inventory.
Compose down/recreate, cache clearing and host restart must preserve the bind mount.
Existing hard-reset code does not delete this host directory, but hard reset is
not an archive recovery procedure and must not be used while writers can resume.

If storage is lost/corrupt or an old snapshot is restored, stop/quarantine every
writer and reconcile GraphDB outcomes before any fresh ownership store is allowed.
A Redis backup alone cannot establish that a lock was free at the time of failure.
Do not delete markers or re-bootstrap to fix a blocked application. The gate's
current operator recovery procedure is in `../oldaplib/docs/writer_recovery.md`;
WR-02 will provide the verified recovery mechanism, followed by API/client tooling.

## Writer coverage and limits

| Participant | Access | WR-01 treatment |
| --- | --- | --- |
| oldap-api workers, including Capture/ingest/export HTTP handlers | Resource operations through oldaplib | Shared policy/URL/trust installed; image preflight |
| oldap-tools resource commands (archive, staging folders, data import/batch) | Direct oldaplib | Same configuration and preflight; operator CLI target must match the configured domain |
| oldap-harvesters | Direct ResourceInstanceFactory | Same configuration/preflight; rendered TOML uses shared GraphDB target |
| Media helper, ingest/export workers, desktop clients, CaptureApp | HTTP callers of OLDAP API | No independent Redis credentials/store needed; API is their write boundary |
| Ontology/taxonomy migration commands, GraphDB initialization, manual SPARQL | Raw/model operations that can bypass resource gate | Maintenance-only with all domain writers quiesced; not made safe merely by exporting a Redis URL |

Concrete bypasses include oldap-tools `ontology.py` update_query and
`fasnacht_taxonomy_migration.py` raw transaction updates. They must not run as
uncoordinated online jobs. WR-01 does not rewrite these domain migration tools.

## Monitoring and verification

The service healthcheck verifies authenticated TLS connectivity, AOF enablement,
last AOF write status and WAITAOF. Check free disk before deployment and monitor disk
space, container health/restarts, certificate expiry and application coordination
errors in the host monitoring system. Redis becoming unhealthy is an alert, not
permission to clear its store. Lock age is diagnostic and never an expiry rule.

Reproduce local checks with an environment containing Ansible, community.docker,
Jinja2, PyYAML, redis and the current oldaplib:

```
ansible-playbook -i inventory.ini oldap-deploy.yml --syntax-check
python -m unittest discover -s tests -p 'test_*.py'
python -m tests.probe_writer_runtime --output /tmp/wr01-runtime-result.json
```

The runtime probe owns UUID Docker fixtures only. It checks actual TLS/ACL, generated
Compose idempotence, two independent Python writers, isolated cache clear, killed
writer plus Redis restart, controlled recovery of a known transaction-free fixture,
container recreation and refusal of missing storage. It never contacts GraphDB.

Evidence is recorded in `../FasnachtsPage/docs/wr-01/`. Full Linux VM reboot,
site-specific firewall/DNS/certificate routing and versioned production image
acceptance remain WR-04/target-rollout checks; local container evidence is not
reported as production deployment. No production inventory was enabled by WR-01.
