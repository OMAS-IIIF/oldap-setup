# Setup merge preparation — 2026-11-03

Later packaging status: core metadata and locks are now prepared as 1.0.0rc1.
See the coordinated `oldap-setup/docs/jena-1.0rc1-preparation.md` for current
artifact acceptance; the original checkpoint versions below are historical.

Local `migration/jena` checkpoint, not a release or production approval.
See [the coordinated merge/release plan](jena-1.0-merge-plan.md).

## Reviewed deployment boundaries

- Candidate preparation requires new storage, immutable image references, distinct
  private keys and verified service/dependency/backup-tool hashes. It starts no
  application and does not replace the installed environment.
- Rehearsal imports a checksum-bound snapshot into a new dataset and uses isolated
  API/Redis storage plus a loopback listener. It does not export/freeze the source.
- Home freeze retains the asserted GraphDB export and two-host filesystem backups;
  activation requires the accepted source hash and stopped source services.
- The Jena network namespace is shared only with its intended clients. Identity
  verification has independent worker capacity and no database credentials.
  Caddy blocks `/internal/jena` while service-authenticated worker routes remain.
- Client replacement retains the namespace owner/data/policy/signing keys and
  updates identity before API. Media verification keys are synchronized separately.
- Candidate publication permits content-qualified Jena tags only, verifies source
  contexts and tested image IDs, refuses existing registry tags and records protected
  normal-tag digests. Build does not push. This is an RC workflow, not a final
  1.0 publisher; concurrent publishers are unsupported.
- Existing Swisscovery and weekly harvesting changes are retained. Their runtime
  lock test is separately opt-in; they do not certify Jena harvester compatibility.

The separate preparation/rehearsal/freeze/activation/update boundaries remain
appropriate. No general deployment framework or cross-host recovery abstraction
was introduced. Home-specific paths, sudo setup and container names are explicit;
production needs its own inventoried workflow rather than copied host substitutions.

## Corrections during review

The old activation rescue ignored errors from target `docker stop` and `docker rm`
and could proceed to source restart without confirmed target shutdown. Rescue now
first enumerates existing containers, tolerates containers never created, and
requires successful stop/removal before restoring GraphDB. Client-before-backend
order remains explicit. Docker enumeration failure also stops the rescue.

Activation now refuses a retained `target-opened.txt` marker, since target writes
may already exist. Freeze requires the current API to select GraphDB, preventing
a fresh backup path from bypassing the first-cutover boundary on an active Jena
installation. These guards do not replace operator fencing or reconciliation.

## Validation

- 60 local tests and 34 subtests pass across setup configuration, publication,
  content comparison, writer/recovery deployment, provisioning/update boundaries,
  authentication, harvesting and the new activation cases.
- Rollback tests execute the actual Ansible rescue command tasks on localhost with
  a fake Docker executable. Inventory, stop and removal failures prevent a source
  restart sentinel; partial/empty container inventories succeed safely.
- One opt-in Swisscovery Linux/container lock test is skipped because no dedicated
  image was selected. No shared harvest job was started.
- All nine `oldap-jena-*.yml` playbooks pass Ansible syntax checks. Compose overlay
  merges and Caddy adaptation use synthetic settings. No SSH or remote playbook
  execution, registry publication, source migration or service replacement occurs.

Historical home/native-container acceptance JSON is retained as historical
release evidence, not silently re-labelled as tests of this new tip. The rollback
correction is tested locally; it has not been applied on home.org.

## Recovery and release gates

The library's packaged offline backup operator preserves application RDF, private
receipts, text-index state, configuration/media and coordination snapshots with
checksums and a fresh restore-generation handoff. Its earlier isolated acceptance
is in sibling library docs. Setup's home GraphDB backups are a different source
backup path and remain same-host copies. This review does not claim a newly tested
restore or automated production-wide recovery.

Before production: rehearse off-host restoration of the complete multi-host state,
verify storage and generation/fencing policy, inventory all writers/timers, resolve
worker shutdown, accept harvester/media releases, and complete coordinated Jena
routine-update/recovery automation. After target writes, returning to GraphDB
requires data reconciliation; never delete the opening marker to enable rescue.

Before 1.0: checkpoint remaining library/API corrections, update package/runtime/
OpenAPI/lock metadata and 1.x consumer constraints, change the explicitly pinned
OLDAP service wrapper from 0.1.0 together with its preparation/build checks, and
validate clean final artifacts on home. Apache Jena retains its upstream version.
Git main, remote branches, existing image tags and deployed services remain unchanged.
