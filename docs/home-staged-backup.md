# Full staged backup and isolated application restoration

Snapshot `20261106-studio-staged-03` completed the full path from coordinated
backup through Studio/Borg to a running isolated application. **Integrity and
restoration passed; the proposed performance optimization did not.** Evidence:
[home-staged-backup-results.json](home-staged-backup-results.json).

## Decision and timing

The producer took 2682.55 seconds (44m43s), including online work. Sampled HTTP
interruption was 975.7 seconds for API and 979.9 seconds for media (about 16m20s).
The previous simpler workflow measured 685.5 seconds of media interruption
(11m25s). The staged run was therefore about five minutes worse on this system.
Measurements are observational, not controlled hardware/cache benchmarks.

| Staged phase | Seconds | Offline? |
| --- | ---: | --- |
| Media pre-copy | 473.8 | No |
| API archive | 28.9 | Yes |
| Final media checksum synchronization | 455.6 | Yes |
| Independent media checksum verification | 435.2 | Yes |
| API source comparison | 33.7 | Yes |
| Archive frozen media staging | 483.8 | No |
| Compare archive with frozen staging | 479.1 | No |
| API archive hash | 51.5 | No |
| Media archive hash | 196.8 | No |

The two offline media scans dominate the staged interruption. Keep the simpler
previously measured offline tar/source-comparison flow as default, with hashing
after recovery (`home_media_precopy=false`). Explicit `true` retains the staged
experiment for testing on different storage. Both mode branches and failure
publication/recovery behavior pass the Ansible test suite; the Linux fixture and
both manifest variants pass. Do not remove integrity checks merely to improve
the timing result.

## Complete acceptance

- Snapshot sizes: API 32,821,770,240 bytes; media 21,153,853,440 bytes.
- Fourteen actual image identities/platform records retained in the manifest.
- Studio pull and hash verification: 287.35s; Borg create: 71.49s; full repository
  data check: 59.68s; extraction: 48.18s; restored-file verification: 22.28s.
- Borg input including manifest: 53,975,630,946 bytes; additional deduplicated
  archive data: 2,088,909,120 bytes (excluding repository metadata overhead).
- Actual **Borg-extracted** files transferred back to Linux in 271.45s. Hash/header
  verification and Linux extraction completed in 117.45s.
- Restore selected the six exact recorded image IDs, not their mutable tags.
  The image-selection regression test verifies this behavior.
- Six containers started in a new isolated project; runtime checks confirm
  private mounts, no published ports, isolated bridge, disabled delivery/jobs and
  no tested TCP reachability to live API/media hosts or the internet.
- All 18 restored functional checks pass: fresh login, capabilities, upload-token
  validation without uploading a file, 30 stories, 100 archive rows, ten fulltext
  matches, signed IIIF metadata and matching JPEG bytes/hash.
- Functional values equal the pre-backup baseline. Raw story hashes differ only
  under the previously documented QName/full-IRI keyword normalization; RDF-aware
  comparison is required and passes. This is not a fix for API serialization.
- All six restored services stopped afterward: five exit 0, Java exit 143 after
  SIGTERM; no OOM or forced-kill exit. All eight original API-VM containers retain
  their IDs, images and start times across the isolated restoration.
- Final 26 public checks and 18 functional checks pass on the running home stack.

This does not test a freshly provisioned host, restored write workflows, worker
replay, browser access to a cloned frontend, or production migration/rollback.
Those remain separate gates. No production host or backup schedule was changed.

## Retained files and cleanup performed

The current stopped restore is project `oldap-restore-staged-03`, rooted at
`api.home.org:/srv/storage/oldap-restore-rehearsal-staged-03`. Data, incoming tar
files, private Compose, image inventory and audit helpers remain there. The API
VM had approximately 40.8 GB free after restoration. Media staging and the new
server snapshot remain; Studio retains the accepted snapshot, Borg archive
`home-20261106-studio-staged-03` and extracted files under `restore-test/`.

Before this run, both earlier Studio extractions were independently rehashed,
and both Borg archive identities checked. Then only redundant working copies
were retired to make space:

- Removed the already stopped `oldap-restore-20261106` containers/network and its
  `incoming`, `tree` and `runtime` directories; private metadata remains.
- Removed old API-server `api.tar` copies for `20261106-studio-rehearsal-01` and
  `20261106-studio-timed-02`, first renaming their ready markers to
  `ready.retired.json`. Retirement records remain beside the old manifests.
- Both original accepted snapshots and both Borg archives remain on Studio.
  No Borg pruning or source/live data deletion occurred. Old server ready paths
  are intentionally no longer usable for a new pull of those retired copies.

Private execution evidence is in `/tmp/oldap-backup-staged-03` on the development
machine and `OLDAP_BACKUP/reports/verification-20261106-studio-staged-03.json` on
Studio. The sanitized repository evidence includes phase/availability timings,
transition samples, image audit, functional reports and final service state.

## Storage observation requiring follow-up

Successive API archives grew from 23.38 GB to 28.70 GB to 32.82 GB. Archive headers
confirm growth in TDB index files: `POSG.idn` grew from 2,399,141,888 to
2,944,401,408 to 3,372,220,416 bytes. Other sampled indexes also grew. The media
archive size remained unchanged. These are observations, not an explanation:
actual dataset changes, transaction churn and storage reclamation have not yet
been distinguished. Investigate before production capacity/scheduling decisions;
no compaction or live database maintenance was performed in this test.
