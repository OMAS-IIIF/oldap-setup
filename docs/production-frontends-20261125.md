# Production frontend promotion — 2026-11-25

Promoted the exact Home-accepted images: oldap-app **0.2.11** and FasnachtsPage
**0.1.54**. No rebuild. Runtime versions, seven read-only browser checks and the
final unchanged plan pass. Six sibling container IDs are unchanged; API 1.2.4/Jena
health remains healthy. Named-user live editing was not exercised.

[Sanitized receipt](production-frontends-20261125-results.json) records images,
container IDs and browser results. Source tags/images were already published;
only deployment evidence and the two default frontend selections are updated.

Selection: `releases/production-frontends-20261124.json` (prepared before midnight).
Rollback: `releases/production-frontends-20261124-rollback.json` through `make plan-vm`
then `make deploy-vm`, absolute `RELEASE_FILE`, and the existing protected production
become-vars file. No database restore is required. Private configuration backup:
`/opt/oldap/compose/routine-update-20261124T230309516443Z`.

The initial attempt stopped before changes because the stored sudo credential was
outdated. The user refreshed it. Before pulling, removed only unused Fasnacht image
caches 0.1.41/42/43 after confirming their registry availability. Current rollback
images/data/volumes remain intact. `/var` now has 2.9 GiB free (94% used); further
cache/capacity maintenance is advisable before additional releases.
