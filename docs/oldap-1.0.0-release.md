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

## Status

Preparation and acceptance are in progress. Exact source revisions, wheel hashes,
image digests, verification results and production activation will be recorded
in the release results alongside this document. No completion is implied by
version metadata or tags alone.
