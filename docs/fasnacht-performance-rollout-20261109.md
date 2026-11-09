# Fasnacht frontend performance rollout — 2026-11-09

The owner authorized publication and production activation of the three reviewed
FasnachtsPage optimizations: single responsive route mount, shared/parallel detail
metadata reads, and narrower overview projections. Source commit is
`dd316a43fb2b93c456c980d6ef208ff009694418` on `migration/jena`; no merge to main.

## Image and activation

- Published only `lrosenth/fasnachts-page:jena-0.1.49-rc1-31da5ef618c6-amd64`.
- Registry digest: `sha256:f8e1e718f55864db013637a803ff295b501d7716ea1488f656d80878e89e0b41`.
- Source fingerprint: `31da5ef618c6a0614255853478e10d00eab55893cd1315cfda246aa355e3ee5f`.
- Previous image: `lrosenth/fasnachts-page@sha256:e363050b4ae3d45689c58afbd47125809b26781d015c2d3b8a116287629800b9`.

The existing source-freezing script retained 418 allowlisted files; only the
FasnachtsPage context was built. The AMD64 image passed label/architecture and
HTTP startup checks before publication. No stable/latest tag was changed.

Production uses a consolidated `/opt/oldap/compose/docker-compose.yml` with
literal pinned images, rather than the historical Jena overlay/tag selectors.
A scoped, recorded Ansible operation verified the exact preceding image,
pulled the new digest, saved the private Compose file and replaced only that
image reference. `docker compose config --quiet` passed; activation used
`docker compose up -d --no-deps --wait fasnachts-page`, followed by internal
HTTP readiness. Automatic old-configuration recovery was prepared but not used.
All seven other API-host containers retain their exact IDs/start times/images.
No media-host deployment, data migration, secret, permission or schedule change.
Home remains unchanged.

Private build, publication and Ansible logs, the executable scoped rollout and
source manifest are retained under the operator's Application Support directory:
`OLDAP-Jena/releases/20261109-fasnacht-performance`.

## Rollback

The exact pre-rollout file is
`/opt/oldap/compose/docker-compose.yml.before-fasnacht-performance-20261109T172105`.
For immediate rollback, restore that file to `docker-compose.yml` and run
`docker compose up -d --no-deps --wait fasnachts-page` in `/opt/oldap/compose`.
Before any later rollback, check for intervening configuration changes; do not
blindly replace a newer full Compose file. The preceding image remains retained.
No RDF rollback is involved.

## Public verification

Two fresh Chromium samples immediately before/after rollout used the same public
HTTPS route and selected object. These are small sequential samples, not a load
test. All four measured runs completed without HTTP 5xx responses.

| Readiness | Before (ms) | After (ms) |
|---|---|---|
| Archive overview | 7511, 7968 | 4090, 4517 |
| Selected object | 4824, 4321 | 2334, 1811 |

Overview search requests fell from 18 to 9. Combined overview/detail API requests
fell from 56 to 26 in each sample. Mean readiness improved about 44% / 55%.

Desktop/mobile smoke checks cover overview counts, a single main mount, object
navigation, a directly opened two-target medium and the public home page. The
first extra smoke attempt timed out waiting for the medium heading; an independent
fresh read returned all API responses successfully and rendered its image and
metadata. The complete smoke sequence was repeated; see results JSON. This
isolated timeout is not included in performance measurements and its cause is
not proven. Earlier intermittent upstream-reset findings remain open separately.

Authenticated editing/upload workflows were not exercised in this read-only
release check; preceding code tests and failure-path comparisons are documented
in the frontend repository. No public API signature changed.
