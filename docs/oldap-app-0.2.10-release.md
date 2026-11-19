# OLDAP App 0.2.10 production release — 2026-11-19

Published Git tag `v0.2.10` from source `e094743` and the immutable multi-platform
image recorded in [the receipt](oldap-app-0.2.10-results.json). Includes pagination,
property/reifier editors, multiple superproperties and restored-session avatars.
Production already runs the required API 1.2.3/library 1.2.2 contract.

AMD64 and ARM64 images were built from a clean Git archive, started and checked
for version/HTTP 200, then published without rebuilding. Source typecheck, 55
unit/component tests, 28 mocked browser workflows and 20 updater tests pass.
Only oldap-app was replaced; seven sibling container IDs remain unchanged.
Runtime reports 0.2.10 with the existing public/internal API origins. Public
https://app.oldap.org/en renders correctly without JavaScript errors; API/Jena
health passes and the final partial plan has no changes. Authenticated live edits
were not exercised. No data migration, home update or latest-tag change.

## Reapply and rollback

Use `make plan-vm` / `make deploy-vm` with an absolute `RELEASE_FILE` pointing to
`releases/oldap-app-0.2.10.json`, using the established protected become-vars file.
Rollback uses `releases/oldap-app-0.2.10-rollback.json` through the same workflow;
no database restore is needed. The previous app digest is retained there.
Private configuration backup:
`/opt/oldap/compose/routine-update-20261119T225011204746Z`.

Private logs and screenshot:
`~/Library/Application Support/OLDAP/releases/oldap-app-0.2.10`.
