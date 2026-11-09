# Final production migration — 2026-11-09

## Current boundary

Production is publicly running Jena following explicit owner approval. The durable
`target-opened.json` marker exists in checkpoint `20261109-final-01`. Both public
acceptance and the first complete producer/office backup passed. All operational
schedules are active; the old GraphDB backup timer and source containers remain
stopped. The cutover lock has been released.

Target: `/srv/storage/oldap-jena-production-20261108`. Frozen source checkpoints
remain at `/srv/storage/oldap-cutover-20261109-final-01` and
`/data/oldap-cutover-20261109-final-01`; keep these and historical GraphDB backups.
**Do not simply restart the frozen GraphDB source: reconcile all post-opening
writes before any return to that system.**

## Public acceptance and first backup — passed

Public HTTPS checks pass for Fasnacht, OLDAP App, SALSAH, API and media. Actual
browser rendering shows 48 archive detail links and 30 story cards, without
JavaScript/server errors. All 19 API/media checks passed both before and after
the backup, including eleven exact source-baseline fields. The reusable probe
accepts `RESTORE_API_URL` for public checks while keeping its local default.
The official Fuseki endpoint has valid TLS and rejects unauthenticated access
with 401. Authenticated native UI/query/update was tested privately; a public
browser login with the production password was not repeated.

First real snapshot: `20261108T235609Z-1b5ca95a`. API tar: 463,124,480 bytes;
media tar: 21,283,594,240 bytes. The producer completed successfully and published
its matched manifest. API ingress container timestamps show 172.067 seconds
stopped (23:56:19 to 23:59:11 UTC); this is not a continuous external availability
measurement. The office receiver exited 0 at 00:10:19 UTC after complete pull,
encrypted Borg creation, streamed restoration/SHA verification of both archives,
paired source acknowledgements, guarded retention and SUCCESS mail submission.
The owner confirmed receipt of both real SUCCESS emails (producer and office).
This verifies restored archive bytes; full application restore was rehearsed
previously on home, not repeated against the live production store.

Schedules activated only after that complete receiver acceptance:
- API snapshot daily 03:15 Europe/Zurich (`Persistent=false`).
- Office pull/Borg daily 04:00 local Europe/Zurich, user GUI LaunchAgent.
- Harvest Sunday 05:00 Europe/Zurich; next trigger November 15, no manual import.
- Namespace recovery every ten seconds; first healthy check exit 0.

The legacy office `OldapBackup` job is disabled and its plist retained outside
LaunchAgents under `jena/schedule/legacy-oldap_backup.plist`. Its script and old
archives are unchanged. The office user session and machine must remain available
for the LaunchAgent. Server GraphDB backup remains disabled. Retention is 30 daily,
12 weekly, 24 monthly Borg archives; three confirmed server transport pairs and
two office pairs. Unconfirmed copies are not retired.

Protected full evidence is retained in the development `final-readiness-20261109`
directory, the source API checkpoint and the office Jena receipts/schedule folders.
Sanitized evidence is in the adjacent results JSON.

## Accepted source and offline target

Both online configurations/image identities still matched the frozen release
inputs. Source topology and capacity passed on both VMs. The source snapshot play
completed without rescue: stopped-file comparisons and all artifact hashes pass.
The fresh RDF SHA-256 is
`39f67d8bfd02750bb33e12c7277d42f91b6f592042c384fbe477588549356072`, identical
to the earlier accepted rehearsal. Existing semantic/API baselines remain relevant.

Separate transfer copies preserve the exact 0700/root ownership required for
rollback checkpoints. Copies live under `oldap-transfer-20261109-final-01` on
both data filesystems; originals were not made user-owned or group-accessible.
The office retained all seven files at
`/Users/rosenth/OLDAP_BACKUP/checkpoints/20261109-final-01` and in the encrypted
new repository as `cutover-20261109-final-01`. Every file was streamed back from
Borg and matched in size/SHA. This archive is outside `production-*` pruning.
Its acceptance receipt is retained in the API checkpoint before installation.

`prepare-production-frozen-data.py` validates pinned runtime/operator archives,
requires a new target and stopped source, then copies API/Redis state separately.
Fresh conversion, approved one-default-permission removal/two data-part reversals,
all-project connector audit, bounded model cleanup and reopened TDB import pass.
It does not replace Compose or start services. The target RDF serialization hash
may differ from rehearsal due to generated blank-node identifiers; semantic
round-trip/persisted dataset comparisons are the acceptance criteria.

`check-production-offhost-checkpoint.py` binds the receiver receipt to this exact
manifest and every frozen artifact before the private play replaces configuration.
The private play now runs `clear-migrated-model-cache.py --private-production-root`
after Redis/native startup and before either identity/API client. This verifies
actual Docker mounts and stopped clients before planned/applied selective cleanup;
it never flushes Redis or modifies the source store.

## Private acceptance — passed

All nine gates passed: data, permissions, relationships, fulltext, media-auth,
concurrency, native-console, harvester-backend and backup-readiness. The exact
fourteen target image identities and per-report hashes are recorded in
`private-acceptance.json` on the API checkpoint; sanitized evidence is in
`production-cutover-20261109-results.json`. API-only probes explicitly
exclude media; run the separate disposable media check before declaring that gate.
Its helper has no network/data mounts; its SIPI has read-only source media and a
temporary cache, no public ports. At this private stage, original media services were stopped.

Verified API results: 30 stories, the first 100 sorted archive objects and ten
word-order-independent AND matches. Eight API baseline fields and three signed
media fields match the accepted rehearsal on identical source RDF. All six
project model APIs and the nine Fasnacht text fields pass. Forty-eight reads at
16-way concurrency match sequential baselines. Native UI bytes match the pinned
Apache JAR; authenticated query/update and disposable graph cleanup pass.
Both actual provider images pass CLI help with exact Jena transport settings;
no import was started. All target binds are covered by the installed backup
roots and unattended controller access passed. Scheduling and lock release
subsequently followed the accepted public opening and first backup above.

The native probe initially used the API image's default UID, which could not
read the mode-0600 native administration file. Running that disposable probe
as the native UID 1000 resolved it without loosening file permissions. Media
startup logs were separated from the JSON evidence; the functional probe passed.
These were probe-execution corrections, not application/data defects.
