# OLDAP 1.0.0 final release

Owner-approved scope: oldaplib, oldap-api, oldap-tools and the OLDAP Java wrapper
1.0.0; oldap-app 0.2.8 includes the accepted dependency fixes. Apache Jena remains
6.2.0. Other component versions remain independent. Zod 3 is an explicitly
accepted temporary risk; see oldap-app's dependency review.

## Final artifacts

`scripts/jena-images.py prepare --final --bundle PATH --constraints FILE`
requires clean committed core sources with matching stable versions. It builds
real 1.0.0 wheels (no local/RC suffix), pins API/Tools wheels to the exact library
and prepares new v1.0.0 images. Existing RC mode is unchanged. The optional pip
constraints file is retained and hashed in each build context; this release uses
the union of accepted production API and Tools dependencies, excluding the three
core packages and installer tooling. No unrelated dependency upgrade is intended.

Run build, then accept with the final service bundle, then publish. Acceptance
binds tested image IDs; changed contexts, inconsistent versions and existing tags
are refused. Final publication creates vX.Y.Z-amd64, vX.Y.Z-arm64 and a multiarch
index, without changing latest. PyPI publication is a separate exact-wheel upload;
verify registry hashes against the accepted local files and retain those files.
API/Tools Poetry locks are resolved offline using that same library wheel.

The frontend source freezer now derives frontend versions from package.json.
Build oldap-app v0.2.8 from its frozen context, verify runtime package versions and
HTTP/browser behavior, and publish only the new immutable tag. Keep all previous
images and the exact installed Compose selection for rollback.

## Production boundary

Production uses a consolidated Compose file with pinned literal image references.
Do not run the historical home-only or GraphDB routine-update playbooks there.
A scoped release rollout replaces only API, independent identity and oldap-app,
with pre-pull, saved configuration, readiness checks and old-selection recovery.
Tools is an operator/batch artifact; there is no active Tools service in the
installed production Compose file. Cache the new image and record its digest;
do not rewrite retained backups or stopped historical batch manifests.

The final Java JAR hash is identical to production's currently mounted RC JAR:
`b112fc4db082b315f2297eb1d3527321ec85c2de8943beaa466284209b8a76ad`.
The Fuseki hash also matches. Retain the running namespace owner and its existing
mount path rather than restarting the database solely to rename an identical
artifact. Record the final bundle and this equivalence explicitly; do not claim
that the on-disk RC filename was renamed. No RDF migration or schema change.

## Publication and production activation — 2026-11-09

Completed. The three exact 1.0.0 wheels are published on PyPI and their registry
SHA-256 hashes match the accepted files. Git mainlines and annotated v1.0.0 tags
are published for the core packages; oldap-app uses v0.2.8. Setup's v1.0.0 tag
records this release workflow and receipt. API and Tools have tested AMD64/ARM64
v1.0.0 Docker indexes; oldap-app v0.2.8 is AMD64. Existing tags/latest are unchanged.
See `oldap-1.0.0-release-results.json` for exact revisions, hashes and digests.

Use the retained Poetry environment (poetry-core 2.3.2) to reproduce these wheels.
An intermediate build with poetry-core 2.5.0 changed generated metadata and was
not published. The accepted `core-release` bundle uses 2.3.2 and matches the
library hashes in both client lock files. Third-party versions exactly match
previously accepted API (76 packages) and Tools (60 packages) on both architectures.

Production activation completed at approximately 18:13 CET. Only oldap-api,
oldap-jena-identity and oldap-app containers changed. Jena, Redis, Caddy,
FasnachtsPage and SALSAH kept their exact container IDs and images. Tools 1.0.0
is cached on the API host for explicit operator use. No media, RDF, schedule or
home.org changes. Maintenance exclusivity was released after successful activation;
automatic configuration recovery was available and not used.

The final Java JAR is retained as a release artifact; production continues using
the byte-identical existing JAR under its RC filename, as explained above.

## Acceptance and limits

- All 22 service checks pass, including crash recovery and fulltext persistence.
- All 12 release/lock workflow tests pass without skips.
- Both packaged API architectures pass real Jena transaction, callback,
  contention, bridge isolation and namespace replacement checks.
- Installed imports, package versions, dependency consistency and Tools CLI pass
  on both architectures. App build, typecheck, 20 unit tests and 4 mocked browser
  flows were covered by the security update; final image HTTP/hydration also pass.
- Production health reports v1.0.0 and reachable Jena. Public API, app and archive
  HTTP checks pass. Complete desktop/mobile archive overview, selected object,
  direct medium/image and home-page checks pass without JavaScript errors/5xx.

The first archive sequence timed out waiting for an object heading. An independent
diagnostic and the entire repeated sequence passed; its cause is not established.
This remains an observation alongside the previously documented intermittent
upstream behavior. An initial app network-idle wait also timed out; checking the
actual hydrated content passed. Neither attempt is hidden by the successful repeat.
The existing mobile-media lifecycle missing-secret message is a separate open item.
Production authenticated writes/uploads were not exercised in this read-only smoke.
Zod 3's high finding remains explicitly accepted; npm's zero-critical result does
not imply GitHub's asynchronous alert list has already reconciled.

## Rollback and retained evidence

Exact prior Compose file:
`/opt/oldap/compose/docker-compose.yml.before-final-1.0.0-20261109T181259`.
After checking for intervening changes, restore this file and run
`docker compose up -d --no-deps --wait oldap-jena-identity oldap-api oldap-app`
in `/opt/oldap/compose`. Retain maintenance exclusivity during any operator rollback.
The old images remain available. No database restore is required for this client
release; never restore an old RDF snapshot over subsequent production writes.

Private build contexts, immutable wheels, acceptance logs, scoped Ansible rollout
and its logs are retained in the operator's Application Support directory under
`OLDAP-Jena/releases/20261109-1.0.0`. Only `core-release` is the published core
bundle. The checked-in results intentionally omit credentials and raw service logs.

Next: observe routine backup/harvest runs and normal user workflows. No further
performance change or data migration is included in this release.
