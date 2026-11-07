# Measured home backup — 2026-11-06

Snapshot: `20261106-studio-timed-02`. The user authorized unrestricted work on the
local home test environment, including the temporary interruption. Production
and the office-Mac backup were not touched. No schedule or pruning was enabled.

## Server measurement

The producer completed successfully in **887.10 seconds (14m 47s)**, measured
from the observer's start (including three seconds of baseline sampling).
HTTP probes from the development machine followed the public home URLs:

| Check | Observed interruption | Sampling bounds |
| --- | ---: | ---: |
| API `/status` | 682.44 s (11m 22s) | 679.32–685.95 s |
| Media `/health` | 685.46 s (11m 25s) | 681.42–688.53 s |

Probes ran concurrently, with a two-second pause between rounds and a three-second
request timeout. Bounds bracket observed transitions; they are not an exact
measurement of every internal service's availability. Each endpoint had one
continuous observed outage and recovered before hashing began. Separate public
and functional API/media checks passed before and after recovery.

Ansible task-start intervals (including small task/connection overheads):

| Phase | Seconds | Services stopped? |
| --- | ---: | --- |
| API archive | 23.14 | Yes |
| Media archive | 484.10 | Yes |
| API source comparison | 26.26 | Yes |
| Media source comparison | 123.86 | Yes |
| API archive SHA-256 | 46.17 | No |
| Media archive SHA-256 | 141.09 | No |

The two hashing tasks used **187.26 seconds (3m 7s) outside the interruption**.
The code change removes this work from the offline phase; it does not accelerate
copying or eliminate online I/O load. Media copy/comparison account for about
608 seconds of the 685-second media interruption, making them the dominant
remaining optimization target.

The earlier producer took 1232.4 seconds in total, but exact outage was not
measured then. Cache/storage conditions were not controlled between runs, so
the total-time difference is not a controlled estimate of this change's benefit.

## Functional and artifact acceptance

Public checks cover Jena selection, stopped GraphDB, private backend, login,
upload-token handling, protected internal routes, stories, fulltext, signed media
and frontend availability. Additional functional checks compare capabilities,
30 stories, 100 archive rows, 10 fulltext matches, image dimensions and JPEG hash.
All semantic results match the baseline. The known story-keyword QName/full-IRI
serialization difference appears in the raw digest; the RDF-aware digest matches.

The manifest records eight API-host and six media-host containers; all fourteen
have repository digests. API archive: 28,702,310,400 bytes; media archive:
21,153,853,440 bytes. The API archive is larger than in the previous rehearsal,
an additional reason not to treat total runtime as a controlled comparison.

Studio completed every acceptance phase:

| Phase | Seconds |
| --- | ---: |
| Pull and receiver verification | 256.58 |
| Borg archive creation | 67.42 |
| Borg full data integrity check | 51.93 |
| Extraction into a new test directory | 46.71 |
| Restored manifest equality and archive hashes | 21.02 |

Borg input was 49,856,171,036 bytes including the manifest; deduplication added
2,101,094,855 bytes of archive data, excluding repository metadata overhead.
Archive `home-20261106-studio-timed-02` and the original archive are both retained.
Accepted inputs and restored files remain under Studio's `OLDAP_BACKUP/snapshots/`
and `OLDAP_BACKUP/restore-test/borg-20261106-studio-timed-02/` respectively.

Evidence: [home-backup-timing-results.json](home-backup-timing-results.json).
Private producer logs and HTTP samples are in the development machine's
`/tmp/oldap-backup-timed-20261106/`; Studio's durable execution report is
`OLDAP_BACKUP/reports/verification-20261106-studio-timed-02.json`.
This run verified the new backup files through Borg extraction, not a second
application-instance restoration; that was proven separately in the earlier
[isolated restore](home-restore.md).

## Next optimization

A staged pre-copy with a short stopped final synchronization is worth evaluating
for media. The final snapshot must still cover deletions, in-progress operation
registries, metadata and configuration consistently. Do not treat a live copy as
an accepted backup. Separate staging from the live directories and retain strict
failure/recovery/publication ordering. This run does not implement that change.

Retain the new and previous snapshots for comparison. Home has adequate space,
but stopped restore trees and duplicate tar files need an explicit later cleanup
policy. Registry digests are recorded; actual long-term image availability still
requires registry retention or separate image archives.
