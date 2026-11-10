# Home frontend alignment — 2026-11-09

Completed at the owner's request. Home now uses the exact FasnachtsPage image previously accepted and deployed to production: `jena-0.1.49-rc1-31da5ef618c6-amd64`, digest `sha256:f8e1e718f55864db013637a803ff295b501d7716ea1488f656d80878e89e0b41`. Installed source fingerprint matches the accepted artifact. No frontend rebuild, new registry publication or source implementation change was needed.

Only `fasnachts-page` changed. All seven other service identities/images remain identical, including the API/identity performance candidate 40e6a2f777e3 and the Jena namespace owner. Production was not changed. Thus frontend code is aligned, while home continues testing the newer API candidate; the complete deployments are not claimed to be version-identical.

## Matched browser comparison

Five fresh Chromium desktop contexts per phase, same home host/data, same public reader, same selected object, unchanged backend. DOM mutation timestamps record visible content readiness rather than locator polling delay. All ten runs completed without JavaScript or observed API HTTP errors.

| Median readiness | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Archive overview | 2720.9 ms | 1634.5 ms | 39.9% |
| Selected object | 1627.7 ms | 783.9 ms | 51.8% |

Overview search requests fell from 18 to 9 in every sample. This is an actual browser improvement on home, additional to the prior API-only rollout. Five local samples are not a production load/concurrency guarantee.

Desktop (1440 px) and mobile (390 px) smoke tests pass overview, selected object and story navigation, with one main route mount, no JavaScript/5xx errors and no unexpected requests to the production API. Existing production build/acceptance evidence applies to this exact immutable image; no source files changed, so no redundant rebuild was performed.

## Deployment and rollback

A scoped home-only Ansible rollout pre-pulled the immutable digest, saved `.env`, changed only `FASNACHTS_PAGE_TAG`, validated Compose and replaced only `fasnachts-page` with `--no-deps`. Internal HTTP readiness passed; automatic previous-selection recovery was prepared and not needed.

Retained environment: `/opt/oldap/compose/.env.before-frontend-20261109T223024`. For later rollback, restore only its `FASNACHTS_PAGE_TAG` value after checking intervening changes, then run `docker compose up -d --no-deps --wait fasnachts-page` in `/opt/oldap/compose`. Preserve current API/Tools selections and credentials; no RDF restore is involved.

Private executable rollout, logs, full browser traces and before/after service inventory are retained under `Library/Application Support/OLDAP-Jena/releases/20261109-home-frontend`. Sanitized evidence: [results](home-frontend-alignment-20261109-results.json).

This supersedes the older-frontend/no-whole-page-gain limitation in the API-only home rollout report. Next: user acceptance on the aligned home frontend, then decide whether to promote the tested API/library candidate to production. No production rollout is implied by this home test.
