# Isolated home application restore rehearsal

## Accepted checkpoint — 2026-11-06

Snapshot `20261106-studio-rehearsal-01` was restored from the **actual Borg
extraction on Studio**, transferred to the home API VM, hash-verified again,
extracted and opened in six isolated containers. This exercises the full path
from coordinated backup through Borg back to running API/database/media services.
Sanitized evidence is in `home-restore-results.json`.

Acceptance passed:

- Administrator/public login and distinct publication capabilities.
- Upload authentication: missing/invalid tokens rejected; a fresh valid token
  reached form validation. No file was uploaded by this test.
- 30 published stories, 100 archive results, 10 fulltext AND matches, independent
  of word order; compared with the running home installation.
- Signed IIIF metadata (1589 × 2914) and a 9,898-byte JPEG with identical hash.
- Runtime storage/network isolation, disabled workers and delivery jobs.
- All six restored containers stopped afterward; no OOM or forced-kill exit.
  Java exited 143 after SIGTERM; the other five exited 0.
- All eight original API-VM container IDs, start times and images unchanged;
  functional acceptance repeated successfully after stopping the clone.

Story keyword identifiers were observed as both `L-StoryKeywords:…` and
`http://fasnacht.digital/ns/StoryKeywords#…`. The comparator retains the raw
response digest and also expands this fixture's keyword QNames for an RDF-aware
comparison. It does not change arbitrary strings or application code. The older
frozen raw story digest is therefore not used as the restore acceptance criterion.
The serialization variability remains a separate API consistency follow-up;
this test establishes equivalent identifiers, not a fix for that variability.

## Topology and retained material

Everything restored is beneath the private directory
`/srv/storage/oldap-restore-rehearsal-20261106` on **api.home.org**:

- `incoming/`: the two tar archives and accepted manifest, copied from
  `studio.home.org:/Users/rosenth/OLDAP_BACKUP/restore-test/borg-20261106-studio-rehearsal-01/`.
- `tree/`: extracted source hierarchy, including data and configuration secrets.
- `compose.json`: private generated configuration; `images.json`: image provenance.
- `runtime/sipi-cache/`: disposable cache, separate from live media caches.
- `live-before.json`: original live container identities and start times.

Project `oldap-restore-20261106` contains Jena, identity, API, Redis, mediahelper
and SIPI. API/identity share the restored Jena network namespace, as in the live
installation. No frontend, proxy, worker or harvester is started. Every bind
mount is rebased into the rehearsal directory; no live named volume is used.

The Docker bridge is internal with `gateway_mode_ipv4=isolated`, has no host IP,
and publishes no ports. Actual connections to both home server addresses and an
external IP failed from the clone. Mail uses console backends and helper import
reconciliation is disabled. See [Docker's isolated gateway documentation](https://docs.docker.com/engine/network/port-publishing/).

Total container memory caps are 3,968 MiB: Jena 2,048, API 512, identity 128,
Redis 256, helper 512 and SIPI 512. Java heap is 1,024 MiB. These conservative
limits make this a recovery test, **not** a performance benchmark.

The old stopped containers and bulk extracted/incoming files were subsequently
retired after both Studio copies were reverified, to make room for the next test.
Metadata remains; the old commands below are historical. The new stopped restore
is `oldap-restore-staged-03`; see `home-staged-backup.md` for current paths and
retention. No automatic restart/backup schedule or production change was made.

## Repeating this specific rehearsal

The scripts deliberately describe this home snapshot/layout, not a general
production restore utility. For another run, pass a distinct `--project oldap-restore-NAME` and
`--root /srv/storage/oldap-restore-rehearsal-NAME` to the preparation and isolation
helpers. Review allowed archive prefixes and fixture namespace before use.
Never point the test at live TDB files or start two writers on the same directory.

1. Obtain both tar files and the manifest from the verified Borg extraction
   documented in `home-borg.md`. Transfer them to a **new private** rehearsal
   root's `incoming/` directory on the home API VM.
2. Run `scripts/prepare-home-restore.py extract --root ROOT` as root on that VM.
   It verifies sizes/hashes, rejects traversal/links/devices/unexpected archive
   paths, and refuses to reuse an existing extraction tree.
3. Load the required images. Run the script's `compose --root ROOT` phase; it
   resolves archived Compose files privately, rebases storage, removes live
   runtime connections, and pins local image content IDs. It refuses to overwrite
   an existing `compose.json` and does not start containers.
4. Inspect the generated configuration privately. Capture original live container
   IDs/start times/images. Start only the named restored project.
5. Run `check-home-restore-isolation.py` on the VM. Run
   `check-home-restore.py` through `docker exec -i … python -` in the restored API
   container. For the live reference, use the live API container with
   `RESTORE_MEDIA_URL=http://media.home.org` and
   `RESTORE_IIIF_URL=http://media.home.org/iiif/3`.
6. Compare all report fields, treating `stories_sha256` as raw serialization
   evidence and requiring `stories_rdf_sha256` to match. Stop the restored project;
   verify live identities/start times and repeat the live acceptance check.

Commands used for the completed stack (root on api.home.org):

```sh
docker compose -p oldap-restore-20261106 \
  -f /srv/storage/oldap-restore-rehearsal-20261106/compose.json up -d
python3 /srv/storage/oldap-restore-rehearsal-20261106/check-isolation.py
docker exec -i oldap-restore-20261106-oldap-api-1 python - \
  < /srv/storage/oldap-restore-rehearsal-20261106/check.py
docker compose -p oldap-restore-20261106 \
  -f /srv/storage/oldap-restore-rehearsal-20261106/compose.json stop --timeout 90
```

Use the existing protected Ansible become file for root operations; never put
passwords into these commands or commit resolved Compose configuration.

## Limits and next steps

- This is an isolated application recovery, not reconstruction of a fresh host.
  Docker and some images were already available. Backup Redis/SIPI references are
  mutable tags. SIPI was fetched by the digest observed on the live media VM;
  Redis used its locally cached image. All six runtime images were then fixed to
  content IDs. Future snapshots should retain image digests/provenance, with a
  documented image acquisition or archival strategy.
- No browser UI, real upload, write workflow, queue replay, email delivery,
  automated schedule or production restore was exercised. Deliberate worker
  exclusion avoids replaying archived jobs.
- Shorten the snapshot producer's roughly 20.5-minute total run before routine
  backups. That historical duration includes preflight/recovery and is not a
  separately measured outage. Preserve the consistent offline final snapshot;
  consider pre-copy/final synchronization and hashing after service recovery.
- Production encryption/key recovery (Apple Passwords preference) remains a
  separate decision. Existing production backups remain unchanged.
