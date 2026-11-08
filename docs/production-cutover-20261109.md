# Final production migration — 2026-11-09

## Current boundary

Owner approved the final write pause, exclusion of direct GraphDB console writes,
and keeping production closed through migration/private acceptance. Public
reopening requires a later explicit decision. The cutover lock is held; old
backup/harvest timers are stopped, not resumed against Jena.

- Source: `20261109-final-01`, API `/srv/storage/oldap-cutover-20261109-final-01`,
  media `/data/oldap-cutover-20261109-final-01`; private root-owned checkpoints.
- Target: `/srv/storage/oldap-jena-production-20261108`, independent API/Redis/native
  state. Use registry package 01, never the superseded bare-image-ID package.
- Operator variables: protected local
  `/Users/rosenth/.config/oldap/production-final-cutover-20261109.json`.
- Private execution log: `/tmp/oldap-production-final-private.log` on development
  machine. Once `target-installing.json` exists, use the rehearsed private rollback,
  not source-resume. No opening intent has been authorized at this checkpoint.

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
temporary cache, no public ports. Original media services remain stopped.

Both development and API-host resolvers now resolve `fuseki.oldap.org` to
`131.152.238.105`. Public TLS remains a post-opening check. New backup schedules remain disabled. The
first real Jena production backup/restore and coordinated schedule switch follow
successful opening/operational acceptance; never enable the old GraphDB backup
against Jena. The legacy office LaunchAgent is not currently loaded.


Verified API results: 30 stories, the first 100 sorted archive objects and ten
word-order-independent AND matches. Eight API baseline fields and three signed
media fields match the accepted rehearsal on identical source RDF. All six
project model APIs and the nine Fasnacht text fields pass. Forty-eight reads at
16-way concurrency match sequential baselines. Native UI bytes match the pinned
Apache JAR; authenticated query/update and disposable graph cleanup pass.
Both actual provider images pass CLI help with exact Jena transport settings;
no import was started. All target binds are covered by the installed backup
roots, unattended controller access works, schedules remain stopped and the
cutover lock remains held. First real production Jena backup remains outstanding.

The native probe initially used the API image's default UID, which could not
read the mode-0600 native administration file. Running that disposable probe
as the native UID 1000 resolved it without loosening file permissions. Media
startup logs were separated from the JSON evidence; the functional probe passed.
These were probe-execution corrections, not application/data defects.

Before asking to open: confirm the final target-private lifecycle on both hosts
and absence of `target-opened.json`; these checks passed. Do not mark public
HTTPS/frontend acceptance or first Jena backup as completed based on this report.
