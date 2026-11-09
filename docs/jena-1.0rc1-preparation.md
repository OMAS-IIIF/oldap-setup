# OLDAP 1.0.0rc1 — local candidate preparation

The library, API, Tools and OLDAP Java service wrapper now identify themselves as
`1.0.0rc1`. Apache Jena/Fuseki remains pinned to upstream 6.2.0. This is source and
package preparation, not a public release or permission to activate production.
See [validation and artifact hashes](jena-1.0rc1-results.json).

## Metadata and dependency contract

API and Tools declare `oldaplib >=1.0.0rc1,<2.0.0`, permitting prereleases for this
candidate. Their Poetry locks select the exact RC wheel with SHA-256. No editable
sibling/file URL or private registry is embedded in published package metadata.
Their existing third-party locked versions are unchanged. The library's lock is
now tracked to retain the coordinated development/release solution.

Runtime version modules, bump metadata and API specification agree. Bump parsing
supports rcN and final versions; dry runs to final 1.0.0 pass for all three
projects. The library bump configuration includes the service wrapper; setup's
explicit accepted service version/jar assertion must be updated with each new RC.
Do not run Make's bump targets casually: they still invoke commits/tags/pushes.
No existing tag was moved or created during this preparation.

Mediahelper and harvesters keep their existing independent version sequences.
Their old 0.x library constraints are not widened in the GraphDB checkout. Build
and test dedicated 1.x-compatible candidates before migrating those consumers.
Public library/API call signatures did not change in this packaging step.

## Local development and installation before publication

The RC is not on PyPI. A normal registry-only `poetry install` cannot obtain it
yet. Use an explicitly local environment; existing PyCharm/service venvs were not
silently reinstalled. From the API or Tools migration checkout, an editable
workflow is:

```sh
python3.13 -m venv .venv-rc
.venv-rc/bin/python -m pip install -e ../oldaplib -e .
```

For distribution acceptance, build the three wheels with Poetry and install their
explicit paths into a fresh venv in one pip invocation. Check `pip check`, package
and runtime versions, and module paths outside all source checkouts. Do not copy
an old environment or use `--system-site-packages` for this check.

The current clean-wheel run resolves ordinary declared dependencies with pip; it
is not a claim that every installed third-party version equals a Poetry lock.
Final container images need their own installed dependency inventory and digest.

## Reproducible offline locks for unpublished candidates

`scripts/lock-jena-candidate.py` uses Poetry's resolver and lock writer (tested
with Poetry 2.3.4), not manually edited lock records. It reads distribution
metadata from the built library wheel and supplies it as an ordinary candidate
in an in-memory repository containing the existing locked dependencies. The wheel
filename and hash are retained, but the inspection path is not a package source.
All projects must resolve successfully before any locks are written.

Run it using Python from an environment containing Poetry 2.x:

```sh
/path/to/poetry-environment/bin/python scripts/lock-jena-candidate.py \
  --library-wheel /absolute/wheelhouse/oldaplib-1.0.0rc1-py3-none-any.whl \
  --project ../oldaplib --project ../oldap-api --project ../oldap-tools
/path/to/poetry-environment/bin/python -m unittest tests.test_jena_candidate_locks
```

This adds no repository/source configuration and makes no index request. If a new
requirement cannot be satisfied by the retained locks, it fails rather than
silently updating unrelated dependencies. Two tests cover network-free solving,
portable hashes, replay stability and rejection without lock changes.

Publish only the accepted wheel bytes, or regenerate locks and repeat acceptance
if artifact bytes change. Rebuilding this library wheel produced the same hash.
The local `/tmp` artifacts are inspection output, not durable release storage.
Final artifacts must be retained in the release bundle before publication.

## Container and service preparation

The existing RC publisher maps package `1.0.0rc1` to isolated image labels such as
`jena-1.0.0-rc1-<fingerprint>`. It rejects a mismatch between the package RC number
and the selected RC. Stable/latest and existing-tag protections remain intact.
The clean-source container build and local packaged transport acceptance now pass
for API and Tools on AMD64 and ARM64; no push occurred. See
[jena-1.0rc1-images-results.json](jena-1.0rc1-images-results.json) for exact IDs,
source commits and installed dependency inventories.
This workflow adds local fingerprint versions to staged packages and does not
replace a final release publisher or final artifact acceptance.

The rebuilt wrapper 1.0.0rc1 passes 22 real service checks, including 300 commits,
receipt protection, restart/crash recovery, fulltext durability and authentication.
Preparation accepts the matching jar/version; existing installed home services
are untouched. Python wheel acceptance passes 297 tests plus 26 subtests, and
three real loopback pool/lifecycle tests. OpenAPI validation and pip check pass.

The durable local bundle (wheels, source snapshots, manifests, matching service
and logs) is under `~/Library/Application Support/OLDAP-Jena/releases/20261104-1.0.0rc1`.
Images are loaded into local Docker under
`lrosenth/{oldap-api,oldap-tools}:jena-1.0.0-rc1-4d3c5ef8e1e1-{amd64,arm64}`.
They have not been exported as image archives. On 2026-11-04 the exact accepted
images were published under those isolated tags and multiarch indexes; protected
tags are unchanged. See [publication evidence](jena-1.0rc1-publication-results.json).
Native isolated home transport acceptance also passes. Home API and identity now use the published RC digest; Tools selects its matching
digest. Offline two-host backup, public checks and 48 reads at concurrency 16
pass. All 30 story responses equal the immediate pre-update baseline. See
[home acceptance](jena-1.0rc1-home-results.json).
The accepted image IDs must be retained for publication without rebuilding.

Next: complete manual write workflows, bound Jena total memory after the confirmed
host OOM, coordinate automatic namespace recovery, implement mobile worker draining,
and complete
media/harvester and production cutover gates. Final 1.0.0 publication/deployment
remains a separate step.
