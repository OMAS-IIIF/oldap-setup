# Archive metadata frontend rollout on home — 2026-11-09

The owner authorized image publication and home activation of the tested archive
metadata lifetime change. Production remains unchanged.

## Artifact and deployment

- Image: `lrosenth/fasnachts-page:jena-0.1.49-rc1-ca38b05dc7f7-amd64`.
- Registry digest: `sha256:70a5b4ab750aee44b67d6e4a93dcfaaa2d6c92c14e2e63d8f17bd60691b6b119`.
- Source fingerprint: `ca38b05dc7f7c238f85cf7df706b2a86f8c729145b64352a79ec4ca7ee3f4e85`.
- Source branch: `experiment/archive-page-metadata`, including reviewed uncommitted
  implementation changes. The recorded Git revision alone is not the whole source
  identity; the 418-file allowlisted snapshot and fingerprint identify this build.

The existing source freezer produced the build context. Only FasnachtsPage was
built and published, for AMD64. Architecture, source label, container startup,
archive HTTP response and the refresh control passed before publication. The
new tag did not exist beforehand; no stable/latest or prior release tag changed.

The scoped Ansible rollout checked the exact old image, pre-pulled the new digest,
saved the selection, validated Compose and used `up -d --no-deps --wait` only for
`fasnachts-page`. Runtime readiness passed. The installed image and source label
match the accepted artifact and `PUBLIC_API_URL` remains `https://api.home.org`.
Only the frontend container changed; all seven other container IDs/images remain
identical, including the API performance candidate, Jena and Caddy. No data or
media migration, backend restart or production change.

## Matched live comparison

Three fresh Chromium desktop contexts per action and version, immediately before
and after rollout, using the same home API/data and identical read-only API relay.
Timing covers the filter action to rendered results after initial overview load.

| Action | Before median | After median | API calls before → after |
|---|---:|---:|---:|
| Full text `Laterne` | 1663 ms | 905 ms | 14 → 4 |
| Lower year bound 1940 | 1296 ms | 782 ms | 12 → 2 |
| Image filter | 1445 ms | 856 ms | 13 → 3 |

All displayed counts, card text and link order match. The unchanged Golden Book
control measured 1208 → 1062 ms, 12 calls in both versions; no new detail
optimization is claimed. These small warm samples are not production percentiles
or a first-page-load improvement claim.

The 24 measured contexts captured 552 API responses without HTTP errors.
Additional named-user filter/refresh, logout/public re-entry and mobile public
filter/refresh smoke checks pass. Direct browser checks without relays also pass
archive/object/story navigation at desktop and mobile sizes, one main route mount,
no JavaScript/5xx errors and no production API requests.
Caddy logs contain no new 5xx from the prior transport fix at 22:02:50 UTC through
the final check at 22:28:48 UTC. This is an observed window, not a guarantee against
other future upstream failures.

## Rollback and provenance

Previous image:
`lrosenth/fasnachts-page:jena-0.1.49-rc1-31da5ef618c6-amd64@sha256:f8e1e718f55864db013637a803ff295b501d7716ea1488f656d80878e89e0b41`.

Saved selection:
`/opt/oldap/compose/.env.before-archive-metadata-20261109T232611`.
For rollback, restore only its `FASNACHTS_PAGE_TAG` line after checking intervening
changes, then run `docker compose up -d --no-deps --wait fasnachts-page` from
`/opt/oldap/compose`. Preserve current backend/credential settings. The automatic
activation-failure rescue uses this same scoped selection restore; it was not
needed. No RDF restore is involved.

Private source manifest, frozen contexts, build/acceptance/push/deployment logs,
executable rollout, container inventories and browser traces are retained under
`~/Library/Application Support/OLDAP-Jena/releases/20261109-archive-metadata/`.
Sanitized evidence: [results](archive-metadata-home-20261109-results.json).
