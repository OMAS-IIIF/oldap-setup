# Jena 1.0 merge and release preparation

Status: prepared, not merged or released. This is the coordinated OLDAP 1.0
release proposal, not confirmation of production readiness. Inventory was taken
on 2026-11-03 after fetching all four migration repositories from origin.
See [the exact refs and working-file hashes](jena-merge-inventory.json) and
[the migration/cutover record](../../oldaplib/docs/migration/graphdb-to-jena-cutover.md).

## Checkpoint progress after the initial inventory

Library `827bc56`, API `82d8a50` and Tools `125dd61` are local migration
checkpoints. The subsequent library HTTP-pooling correction and matching API
acceptance documentation are still working-tree changes and must be committed
before final packaging. Tools boundary fixes are included in its checkpoint.
Setup review now includes fail-closed first-cutover/rollback guards, 60 tests plus
34 subtests and nine Jena playbook syntax checks; see
[jena-merge-readiness.md](jena-merge-readiness.md). The table below remains the
historical pre-checkpoint inventory, not a current dirty-file count.

No checkpoint is a final release approval. Next: finish local source checkpoints,
coordinate 1.0 versions/dependencies and verify clean installed artifacts. Setup
still pins OLDAP's service wrapper 0.1.0 and needs its coordinated version update.
Production-specific writer inventory, off-host restore, harvester/media acceptance
and routine Jena updates remain explicit gates.

## What the Git audit establishes

| Repository | Branch | Commits unique to main / branch | Modified tracked / untracked files before preparation |
| --- | --- | --- | --- |
| oldaplib | migration/jena | 0 / 135 | 34 / 80 |
| oldap-api | migration/jena | 0 / 1 | 20 / 121 |
| oldap-tools | migration/jena | 0 / 0 | 14 / 9 |
| oldap-setup | migration/jena | 0 / 0 | 9 / 57 |

All four committed merge simulations (`git merge-tree --write-tree --name-only
origin/main HEAD`) are clean. Main is an ancestor in each case. These checks do
not include uncommitted work and do not establish semantic compatibility. At that inventory, most
Jena implementation was uncommitted; see the progress section for later checkpoints.
Do not use `git add .`: review the inventory and stage explicit source/test/docs
paths, excluding dumps, credentials, generated build output and private evidence.
Review evidence JSON for account/project data before publishing it.

The library is special: main is still 0.4.27; the established GraphDB checkout is
`refactor/ontology` at 0.7.29. The Jena tip contains that entire 134-commit line plus
one migration commit. Merge this ancestry, not a Jena-only cherry-pick onto old
main. The full diff to main includes the ontology refactor and needs that scope in
the PR. Record the 0.7.29 GraphDB baseline, not 0.4.27, for maintenance/rollback.
The exact baseline commit is retained in the inventory.

The original setup checkout also has local harvesting changes. File comparison
shows all its changed implementation/test files are already byte-identical in the
Jena checkout. The Makefile has only the additional Jena block; context/log files
have further Jena entries. Preserve these changes; do not reapply them wholesale.

## Version policy

Proposed coordinated release: **OLDAP 1.0.0**, with oldaplib, oldap-api and
oldap-tools each at 1.0.0, and an oldap-setup `v1.0.0` tag identifying the release
recipe. Use `1.0.0rc1` for Python prerelease packages and `v1.0.0-rc1` for candidate
Git/image labels; only the accepted release gets the final version.
No version files or tags were changed during this preparation.

The private OLDAP Jena service has its own `VERSION = '0.1.0'` in
`oldaplib/services/jena/build.py`. Include it as an explicitly versioned artifact
in the release manifest; propose 1.0.0 for that OLDAP wrapper as well. Apache
Jena/Fuseki keeps its upstream version (currently pinned to 6.2.0).

Keep independent components on their own version sequences: mediahelper,
imageserver/SIPI, FasnachtsPage, harvesters and SALSAH. Their exact tested versions
and digests belong in the coordinated release manifest. A library major version
requires checking consumers even when public Python signatures are unchanged.

### Dependency and packaging work before tagging

- API: replace the editable sibling `oldaplib` path with a released 1.x dependency
  for distribution; preserve a documented explicit local development workflow.
- Tools: `oldaplib = "^0.7.18"` excludes 1.0.0. Update to a tested 1.x range.
- Mediahelper: `oldaplib = "^0.7.0"` also excludes 1.0.0. Decide and test the new
  dependency when rebuilding the upload/auth fixes. Its root Python package
  version (0.1.5) is separate from `mediaserver/VERSION` (component 0.2.17).
- Harvesters: `oldaplib >=0.7.20,<0.8.0` excludes 1.0.0. Test the direct backend,
  credentials, writer lifecycle and import flows before widening the constraint.
  Merely resolving dependencies does not establish Jena compatibility.
- Update lock files, runtime version modules, bump-version configuration and API
  specification version together. Run clean installed-wheel/image checks without
  editable sibling dependencies. Pin exact versions/digests in deployment.
- Existing `scripts/jena-images.py` deliberately produces fingerprinted candidate
  local versions (`+jena.rcN...`) and isolated `jena-*` tags. It is not yet a final
  1.0 release publisher. Add/review a final release path before creating final
  artifacts. Do not simply relabel an RC with different internal package metadata.

## Automation audit and publication boundaries

No tracked `.github` workflows were found on the fetched main refs or in the
four migration checkouts. No active local hooks/custom hooks path were found.
This does NOT rule out GitHub webhooks, external CI or Docker Hub automated builds;
check those service settings before the first push/merge. They were not accessible
through an authenticated CLI in this session.

Do not use Make's bump targets to prepare local versions: library/API/tools
recipes invoke Git pushes; bump configuration also creates commits/tags. The tools
major target additionally has a `bump-my-version-version` typo to repair when
normal release tooling is revised. API/tools legacy image-publication targets
are intentionally disabled in the migration checkout. Retain this protection
until the replacement release workflow is accepted. Mediahelper's `docker-build`
pushes images; its `docker-build-local` is the local-only alternative.

## Ordered merge procedure

1. Record production GraphDB image digests and actual deployed source versions.
   Prepare immutable baseline tags in all affected repositories, plus a
   `maintenance/graphdb` branch if ongoing fixes are needed. Local branch tips
   alone are not evidence of production versions. Do not move existing tags.
2. Review and commit the outstanding implementation to each migration branch in
   coherent units (runtime, tests, operational workflow, migration documentation).
   Keep all required new source files; retain migration scripts for future cutover.
   Include the separate mediahelper/frontend fixes through their own release work.
3. Resolve packaging/version/dependency items above; run focused suites and
   installed-artifact acceptance. Verify signatures used by tools/harvesters;
   document any actual public changes. Preserve the old environment for comparison.
4. Refresh origin refs and repeat the ancestry/merge checks against the exact
   reviewed commits. Push branches and open the prepared PRs only after external
   automation settings have been checked. Prefer history-preserving merge commits
   for this coordinated transition, particularly the library's refactor ancestry.
5. Merge in order: library, API/tools, setup. Main should contain the coherent
   supported state; do not deploy partway through the sequence. Coordinate library
   publication/consumer dependency resolution as an explicit release step.
6. Build and test candidate artifacts on home.org; complete user workflow,
   restricted-user, migration-parity, concurrent request, restart and backup/restore
   acceptance. Home currently runs fingerprinted RC images from dirty snapshots;
   those successes do not alone certify the new clean release artifacts.
7. Freeze final source versions, build the final artifacts once, record component
   Git SHA/version/image digest/service checksum, and run final home smoke checks
   with those exact artifacts. Promote the same digests to production through the
   documented cutover; do not rebuild between final acceptance and production.

No merge, tag, package publication, image push or deployment is performed by this
preparation. No production baseline tag is claimed to exist yet.

## Prepared PR descriptions

### oldaplib — Release the ontology refactor and Jena backend for OLDAP 1.0

Move the established ontology-refactor lineage and Jena implementation into main.
Provide the Jena connection, bounded transaction admission, RDF 1.2 handling,
explicit relationship semantics and configured fulltext search, together with the
persistent service and retained GraphDB migration tools. Preserve public caller
contracts; explicitly document any exceptions found during the consumer audit.

Validation to attach: focused library suites, packaged service/transport checks,
GraphDB conversion/parity evidence, and the exact reviewed commit. Historical
migration evidence exists but must be distinguished from tests of the final tip.

### oldap-api — Integrate the Jena backend for OLDAP 1.0

Select the Jena backend without changing existing public endpoint contracts.
Include fulltext configuration, archive reads/writes, bounded concurrent access,
worker service authentication and diagnostics. Package against the accepted 1.x
library rather than an editable sibling checkout.

Validation to attach: API/worker suites, installed-image acceptance, restricted
and public access, concurrent archive/story checks, final home workflow acceptance.

### oldap-tools — Support Jena ontology and project workflows in OLDAP 1.0

Integrate configurable fulltext fields and Jena project transfer with the existing
ontology YAML workflows. Include the reviewed Fasnacht relationship changes and
use the tested 1.x library dependency. Retain reproducible migration instructions.

Validation to attach: ontology/fulltext/transfer suites and packaged CLI checks.

### oldap-setup — Define the coordinated OLDAP 1.0 Jena deployment

Add persistent Jena provisioning, migration/activation, independent identity
verification, client replacement and media key alignment. Preserve GraphDB data
for rollback, retain existing harvesting work, and pin accepted component artifacts.
Include the cutover, backup/restore and post-deployment acceptance procedure.

Validation to attach: deployment/image/network tests, exact release manifest,
full migration rehearsal and backup/restore evidence. Remaining production update
and writer/harvester gates must be closed before deployment, not hidden by merge.
