# FasnachtsPage 0.1.50 — production release, 2026-11-09

The owner authorized the version increase and production deployment of the
home-accepted archive metadata optimization. FasnachtsPage is now 0.1.50.
Production API/identity remain v1.0.0; no API/library candidate was promoted.

## Source and artifact

Only package.json and the root lockfile version entries changed from the accepted
home snapshot ca38b05dc7f7. Dependency records and application code are identical
to that accepted snapshot. Compared with the preceding production source, the
only additional changed file is the archive overview page.

- Published image: `lrosenth/fasnachts-page:jena-0.1.50-f80d6f7f5d6b-amd64`.
- Digest: `sha256:691e6730e0f5015653dd76dac4cbd94c0b619e6248cef89be5b35e967103b8d0`.
- Source fingerprint: `f80d6f7f5d6be0515eb1bab29b05fecf1d787e7fe4543135b03024c0e7cf47cf`.
- Source branch: `experiment/archive-page-metadata`, including reviewed uncommitted
  changes; the fingerprint/418-file manifest identifies the complete build source.

The source-addressed tag did not exist beforehand. No existing release/latest tag
was overwritten. The AMD64 image passed architecture/source/version label checks,
HTTP startup, refresh-control and rendered landing-page version checks before
publication. Sixteen focused tests and targeted ESLint pass; the production
image build succeeds with the previously known accessibility warnings.

## Activation and scope

The production Compose configuration used the exact expected old frontend digest.
The scoped rollout pre-pulled the new digest, retained the previous configuration,
changed only the frontend image and ran `up -d --no-deps --wait fasnachts-page`.
Internal readiness, installed digest/source/version and the production API origin
are verified. The new container started at 22:47:38 UTC.

Only FasnachtsPage's container identity/image changed. The other seven containers
(API, identity, Jena, Redis, Caddy, oldap-app and SALSAH) remain identical.
Caddy's configuration was independently changed and reloaded, as described below.
No RDF changes, backend restarts, imports, permission edits or media deployment.
Home retains its accepted 0.1.49 candidate; application code differs only by the
new production version declarations.

The first activation attempt stopped at a malformed Ansible assertion before any
frontend mutation. The assertion was corrected, and the guarded rollout then
completed without recovery. Both logs are retained; this was not a runtime outage.

## Production 502 correction

Both API proxy routes had the same mismatch tested on home: Caddy's default idle
keepalive exceeded Gunicorn 26's 2-second default. Only their HTTP transports were
changed to `keepalive 1s`. Existing routes, private callback boundaries, TLS and
headers remain intact. Candidate configuration validation passed, then the bound
Caddyfile was updated in place and reloaded at approximately 22:38:09 UTC.
Live Caddy configuration confirms 1s on both routes. Caddy was not restarted and
arbitrary POST retries were not enabled.

The initial diagnosis and rationale are documented in
[caddy-api-keepalive-20261109.md](caddy-api-keepalive-20261109.md).
No new Caddy 5xx appeared between the correction and the final check at 22:50:49 UTC.
This observed window is not a guarantee against unrelated future upstream errors.

## Public acceptance and timing

Three fresh desktop browser contexts per action and version, same production
API/data and identical read-only API relay. Both arms use the corrected Caddy
transport, isolating the frontend change from the transport correction.

| Filter action | Before median | After median | API calls before → after |
|---|---:|---:|---:|
| Full text `Laterne` | 3498 ms | 1990 ms | 14 → 4 |
| Lower year bound 1940 | 3797 ms | 1656 ms | 12 → 2 |
| Image filter | 4163 ms | 1925 ms | 13 → 3 |

Displayed counts, card text and link order match in every pair. The unchanged
Golden Book detail control measured 2058 → 2424 ms, with 12 calls in both arms;
its source is unchanged and no detail speedup is claimed. Three sequential warm
samples do not establish percentiles or attribute that control variation.

The comparison captured 552 API responses without HTTP errors. Direct browsers
without relays and with normal TLS verification pass archive refresh, object and
story navigation, and visible version 0.1.50 on desktop and mobile. There are no
JavaScript/5xx errors, no home API requests, and only one main route mount.
The public archive also returns HTTPS 200 with certificate verification enabled.
No authenticated production mutations were tested; named-reader lifecycle and
logout acceptance was already completed on the identical application code on home.

## Rollback

Preceding frontend image:
`lrosenth/fasnachts-page:jena-0.1.49-rc1-31da5ef618c6-amd64@sha256:f8e1e718f55864db013637a803ff295b501d7716ea1488f656d80878e89e0b41`.

Saved Compose:
`/opt/oldap/compose/docker-compose.yml.before-fasnacht-0.1.50-20261109T234719`.
Restore only the preceding frontend image selection, preserving intervening
configuration changes, then run `docker compose up -d --no-deps --wait fasnachts-page`
from `/opt/oldap/compose`. The automatic readiness-failure recovery follows this
scoped approach; it was not needed. No RDF rollback is involved.

Independent Caddy rollback copy:
`/opt/oldap/compose/Caddyfile.before-fasnacht-0.1.50-20261109T233805`.
If needed, restore its contents into the existing bind-mounted file inode and run
`docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`.
Rolling back the frontend does not require reverting the transport correction.

Private frozen sources, manifests, build/acceptance/push/rollout logs, executable
plays, inventories and browser traces are retained in
`~/Library/Application Support/OLDAP-Jena/releases/20261109-fasnacht-0.1.50/`.
Sanitized evidence: [results](fasnacht-0.1.50-production-20261109-results.json).
