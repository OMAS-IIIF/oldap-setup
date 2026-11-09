# Media pre-copy experiment

## Status and selection

`home_media_precopy=false` is the default: use the previously measured offline
media tar/compare flow with hashing after recovery. The full-size staged run
`20261106-studio-staged-03` observed roughly 16m20s media interruption, compared
with 11m25s for the simpler flow. Therefore staging is **not recommended on the
current home storage**. Its full Borg/application restoration passed; see
[the completed rehearsal](home-staged-backup.md) for evidence and limitations.

To reproduce the experiment explicitly, pass `-e home_media_precopy=true` to the
home backup playbook. The immutable source list and receiver/archive format are
shared between both modes. This flag does not change production deployment.

## Workflow

With pre-copy explicitly enabled, `oldap-jena-home-backup.yml` copies media into a new private
`/data/oldap-jena-snapshot-ID/tree/` while services are running. The staging tree
is a separate physical copy, not a hardlink farm or a live bind mount. It covers
the same six media/configuration/operation-state roots as the previous archive.
The single `media_paths` list drives synchronization and archive creation.

1. Create new snapshot directories and pre-copy media using Linux rsync with
   permissions, ACLs, extended attributes, hardlinks and numeric ownership.
   A vanished-file result (24) is allowed only during this untrusted live phase.
   Other errors abort before maintenance; no snapshot is published.
2. Drain workers and stop both hosts using the existing coordinated sequence.
   Capture images and archive API/Jena/Redis state as before.
3. Synchronize the stopped media sources into staging, including deletions.
   `--checksum` detects changes even when length and modification time match.
4. Independently run a checksum/itemized dry-run against the still-stopped
   sources. Both a nonzero exit code and any itemized difference reject the
   snapshot. Source directory metadata is preserved; implied parents such as
   `/data` and `/opt` are layout only (`--no-implied-dirs`).
5. Recover services through the existing `always` path. A failed final sync,
   comparison or recovery prevents all later publication.
6. Archive and compare the frozen staging tree after recovery. No later task
   synchronizes that tree with live data. Hash both archives and publish last.

Manifest `status=offline-compared` remains compatible with existing receivers:
API tar was compared directly offline, media staging was compared offline and
its tar subsequently compared with that frozen staging. The new
`media_snapshot_method=online-precopy-offline-checksum-sync` field records this
chain explicitly. Existing receivers preserve it unchanged. Linux tar layout
is unchanged, so the existing restoration procedure still applies.

## Validation completed

The opt-in test `tests/test_home_media_staging.py` executes the actual playbook
sync/archive tasks against a fresh private `/tmp` fixture on media.home.org.
It verifies same-size/same-mtime content changes, deletion/addition, file modes,
extended attributes, hardlink relationships and operation-state changes. It also
requires the comparison to reject detected differences despite rsync returning
zero. After accepted comparison, simulated live writes are excluded from the
archive; tar comparison and archived-content assertions pass. Temporary fixture
files are removed afterward. No real media or services are modified.

Run from a controller Python with Ansible and PyYAML:

```sh
OLDAP_MEDIA_TEST_HOST=media.home.org python -m unittest discover \
  -s tests -p test_home_media_staging.py
```

Ansible failure-injection tests additionally verify recovery/publication ordering
for pre-copy, final sync, final comparison, API comparison, recovery, frozen tar
comparison and hashing failures. A pre-copy failure never enters maintenance;
failures inside maintenance attempt recovery and never publish a ready marker.

The 11m25s measurement in `home-backup-timing.md` belongs to the simpler flow.
The staged full-size run is slower: full checksum reads still occur offline,
and their disk cost exceeds the saved offline tar work on this VM. The method
moves bulk writes and tar creation/comparison online but does not guarantee a
shorter outage. Do not remove integrity checks merely to improve that metric.

## Operational boundaries

- Single operator; no concurrent deployments or direct writers. Existing shared
  drain/recovery controls remain in effect. This is not a distributed lock.
- Media-host peak space increases by approximately one complete media tree beyond
  the tar archive. Retain staging for diagnosis until backup acceptance; cleanup
  must never target live media and is not automatic in this playbook.
- Never reuse a snapshot ID or retry final synchronization after services have
  resumed. Start a new run; a failed staging tree is not a valid backup.
- Do not prune older verified backups after an unsuccessful run. No production
  deployment, backup schedule, encryption policy or retention change is included.
