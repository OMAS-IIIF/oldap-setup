# Official Apache Fuseki administration

`https://fuseki.home.org` serves the **unmodified official Apache Fuseki 6.2.0 UI**
embedded in our pinned `fuseki-server.jar`. The earlier custom read-only console
was not the requested interface and is superseded. The corresponding production
hostname is `https://fuseki.oldap.org`; production is not activated by this change.

## Access and supported operations

Use `admin` and the operator-supplied console password. Caddy checks independent
`OLDAP_JENA_CONSOLE_USER` / `OLDAP_JENA_CONSOLE_PASSWORD_HASH` variables. Original
GraphDB credentials remain unchanged. A separate random `OLDAP_JENA_ADMIN_KEY`
is injected by Caddy and required on every request to the private native listener;
the browser never receives this key. Port 8040 is not published to the host.

The registered dataset is `/oldap`. Native Fuseki supplies queries (including
CONSTRUCT/DESCRIBE), SPARQL updates, graph-store uploads, validators, dataset
information and statistics. The Apache HTML/JavaScript/CSS are served directly
from the pinned distribution, without local modifications or imitation APIs.

Direct administrative writes intentionally bypass OLDAP validation and per-record
permissions, as requested by the operator. They still use the shared transactional
and text-indexed application dataset. Internal transaction receipt metadata stays
hidden and cannot be modified through this view. Unsafe HTTP methods require the
configured HTTPS Origin, including scripted requests. Basic authentication alone
does not authorize cross-origin writes.

Dataset creation, deletion, activation/deactivation, physical compaction and
server backup remain deployment responsibilities. The UI is unmodified, so its
management links can still appear; unavailable operations are rejected. The
existing OLDAP dataset must not be closed or replaced independently of its service.
For a backup use the coordinated OLDAP snapshot workflow, not a second TDB process.

## Architecture

`oldaplib/services/jena/src/JenaAdministration.java` builds a second native
`FusekiServer` listener in the **same JVM** as the private OLDAP transaction service.
It uses Apache's dataset/protocol/management servlets and UI assets. It does not
open another TDB database, create a replica, or translate SPARQL through Python.
The private `/tx/*` listener remains loopback-only on 3031 and is not exposed by
the administration server.

A small `LiveDataset` adapter resolves the engine's current protected dataset.
Each administrative request holds the engine's shared maintenance lock, so an
index replacement cannot invalidate a running request. Native writes serialize
with API writes through TDB's existing transaction lock. Native requests resolve
the new text-index view after replacement. Closing the endpoint never closes the
engine-owned storage. Public Python/library signatures are unchanged.

The optional service properties `adminPort`, `adminSecret`, `adminOrigin` must be
supplied together. Without them, the existing private-only service behaves as
before. Caddy's `fuseki-admin-compose.yml` adds only credentials; no extra JVM,
container or data mount is needed. The old reader container remains stopped only
as an immediate rollback artifact and is not part of the new Compose selection.

## Home deployment and rollback

Build with `oldaplib/services/jena/build.py` against the already verified Fuseki
6.2.0 distribution. Run both `check_administration.py` and `check_service.py`
before activation. `oldap-fuseki-admin-install.yml` takes `service_source` (the
local built release directory) and `service_sha256` from its `build.json`, plus the
existing private Ansible become file. It is explicitly home-only.

The installer verifies both JAR hashes, stages a private service configuration,
validates Compose/Caddy, drains ingress and writers, then snapshots the stopped
API-host dataset, text indexes, receipts, Redis and configuration. The archive is
compared with the still-stopped files. Media files are not changed or copied by
this backend update. Shared `tasks/jena-home-stop.yml` and `jena-home-start.yml`
keep snapshot and activation shutdown/recovery ordering identical. Legacy mobile
SIGINT is admitted only after verifying an unused mobile registry.

The new namespace owner starts first, followed by recreated identity/API consumers.
Native administration readiness is checked before reopening ingress and resuming
media workers. Activation failure restores the exact previous environment/Caddy
configuration, recreates the old backend and consumers, and resumes the previous
console if it was running. No database archive is automatically restored over
live data. The pre-update snapshot and deployment manifest are retained under
`/srv/storage/oldap-fuseki-before-TIMESTAMP/`.

For subsequent manual rollback, coordinate the same shutdown, restore `.env` and
`Caddyfile` from the saved archive, recreate the previous namespace owner and all
consumers, check readiness, then reopen ingress. Both service releases are kept.
This restores software/configuration; it does not undo later administrator writes.

Production needs its own reviewed paths, backup and activation; do not run the
home-only installer there. Do not apply the generic GraphDB installer to an
active Jena stack; it would replace the retained overlay selection. The shared source/configuration contract and Caddy
hostname template provide the production deployment basis.

## Verification

`check_administration.py` uses an isolated temporary dataset and tests native UI,
server/dataset discovery, credential and Origin enforcement, SPARQL updates,
Graph Store upload, RDF 1.2, API transaction isolation and writer serialization,
receipt protection, managed fulltext/index replacement and restart persistence.
`check_service.py` checks existing 300-commit, restart/crash and fulltext behavior
without the optional admin listener. Setup tests exercise real Compose resolution,
Caddy opt-in, preserved GraphDB credentials and failure-safe recovery ordering.

Live browser acceptance and source/snapshot provenance are recorded in
`jena-console-home-results.json`. Earlier custom-console artifacts remain historical
records only; they do not describe the current interface.

## Home acceptance — 2026-11-05

Activated service SHA-256:
`42901bf6b98d8a92df2fce65b3799ee5dd45abb6e843ef7016a5a6d6da038694`.
The browser-delivered index is byte-identical to the pinned Apache JAR. The actual
query editor returned all 23 graphs; the official file-upload UI, native update
and graph-store readback passed. The unique acceptance graph was removed.

All 20 isolated native-administration checks, 22 private-service checks (including
300 commits and crash/restart recovery), 13 setup regressions and 26 public API/media
checks pass. Original GraphDB credential lines were verified unchanged against
the pre-console backup. Production is unchanged. The pre-update archive is
`/srv/storage/oldap-fuseki-before-20261105T004721/api.tar`.

One activation attempt exposed an unsupported `compose create --no-deps` option.
The previous service was restored, the command was corrected to
`compose up --no-start --no-deps`, and a pre-maintenance dry-run was added. The
subsequent activation and all acceptance checks passed. No data restore was needed.
