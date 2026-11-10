# Archive performance candidate on home — 2026-11-09

Follow-up: the frontend was subsequently aligned and browser gains confirmed; see [home frontend alignment](home-frontend-alignment-20261109.md). Measurements below retain the API-only rollout boundary.

Status: published and active on home.org. Production, stable/latest tags, Java service, RDF, media and frontend selections are unchanged. Source remains on experiment branches; no Git or PyPI publication.

## Artifacts and activation

API and Tools `jena-1.0.0-rc1-40e6a2f777e3` were built and accepted for AMD64/ARM64. Each contains the exact private library version `1.0.0+jena.rc1.40e6a2f777e3`. Frozen source fingerprints capture the uncommitted optimization work; the base Git commit alone does not identify these images. Candidate wheels used poetry-core 2.5.0; third-party package versions match the accepted final release exactly (76 API / 60 Tools on each architecture).

Published multiarch selections:

- API: `lrosenth/oldap-api@sha256:02c42245bb49a53e6bd709c4a511542b0d1925b535aacb20440324b1877e977a`
- Tools: `lrosenth/oldap-tools@sha256:ca66014bca0093415d363f5d84bd19a8bc042be0fb46bc5d94b3d1562ee9c324`

The home client playbook pre-pulls immutable artifacts, holds the namespace-recovery lock during replacement, retains the preceding environment and restores it on activation failure. Lock ownership is released on exit. Only API and independent identity containers changed; all six other running service identities/images and the Jena namespace owner were verified unchanged. Tools is selected/cached for operator use, not started as a persistent service. Recovery timer is active after rollout. The installed API/identity source fingerprints match the accepted bundle.

## Acceptance

- Four images build and pass installed imports/dependency checks; both API architectures pass 29 focused installed tests.
- Both packaged architectures pass real Jena identity/callback, commit/read, concurrent BEGIN refusal/retry, bridge isolation and coordinated namespace replacement checks.
- Deployment tests: 18 passed plus two subtests; syntax/compilation/whitespace checks pass.
- Home readiness checks: 26 before, 27 after, including unchanged story content, administrator/public authentication, signed media delivery and upload authentication rejection before any write.
- All 18 complete overview responses (nine requests, public/admin) match before/after. Four timed samples follow a warmup per request; outer row order is retained.
- Desktop (1440 px) and mobile (390 px) browser smoke passes archive overview, selected object and story navigation without JavaScript errors or 5xx responses.

Two checker assumptions were corrected: GraphDB is already removed rather than merely stopped, and old API workers alternate between full ObjectTaxonomy IRIs and their `L-ObjectTaxonomy:` alias. The checker accepts absent/stopped GraphDB, and benchmark normalization expands only that known IRI field. Literal content and row order remain checked. Early browser harness attempts incorrectly assumed a unique responsive loading element and anchor-based story cards; corrected selectors use actual rendered content and clickable headings. These were harness failures, not observed application errors; raw attempts are retained.

## Measured result on home

| Median request | Before | After |
| --- | ---: | ---: |
| Public dating search | 1010 ms | 653 ms |
| Administrator dating search | 2063 ms | 786 ms |
| Administrator Agent metadata | 551 ms | 229 ms |
| Administrator media preview metadata | 443 ms | 272 ms |
| Sum of nine public case medians | 2723 ms | 2291 ms |
| Sum of nine administrator case medians | 5273 ms | 2527 ms |

These are actual home measurements against its prior installed candidate, so they include both the focused dating read and the subsequent schema/role-join improvements. Sums describe serial API work, not browser latency.

The complete browser overview median is 2751 ms before and 2676 ms after (three fresh contexts each): **no convincing whole-page speedup is established**. The older unchanged home frontend still produces duplicate searches. Updating it to the already reviewed newer frontend is a separate next step; do not claim the API gains directly translate into page gains.

## Rollback and evidence

Retained private environment: `/opt/oldap/compose/.env.before-client-update-20261109T221348`. After the subsequent frontend update, restore only the prior `OLDAP_JENA_API_IMAGE` and `OLDAP_JENA_TOOLS_IMAGE` values under the recovery lock, preserving the current frontend/other settings and replace only `oldap-jena-identity` and `oldap-api` with `docker compose up -d --no-deps --wait`. Recheck readiness before releasing the lock. Prior images remain available. No database restore is required or appropriate for this client-only rollback.

Sanitized provenance and measurements: [archive-performance-home-20261109-results.json](archive-performance-home-20261109-results.json). Frozen sources, wheels, logs, exact private responses and benchmark/browser scripts are retained locally under `Library/Application Support/OLDAP-Jena/releases/20261109-archive-performance`; remote read-only benchmark evidence is in `/home/rosenth/archive-performance-20261109`. No production changes were made.
