# Home frontend releases — 2026-11-24

oldap-app **0.2.11** and FasnachtsPage **0.1.54** are published and active on home.
Production was not changed. Source commits/tags and version-only multi-platform
Docker images are pushed; `latest` is retained. Image identities and sanitized
acceptance are in [the receipt](home-frontends-20261124-results.json).

Both images passed AMD64/ARM64 startup/version/HTTP checks. App: 65 unit/component
and 29 mocked browser tests, clean typecheck/audit. Fasnacht: 276 unit tests,
four isolated admin browser suites, production navigation smoke; existing typecheck
baseline and five editor/Zod audit findings remain documented in its repository.
The updater's 20 regression tests passed.

Only the two frontend containers were replaced. Six sibling IDs are unchanged;
API 1.2.4/Jena health is healthy. Read-only Home browser checks cover both sites,
archive, stories, participation, login and anonymous admin denial without JavaScript
exceptions. Named-user live editing was not exercised. Final partial plan is unchanged.

## Disk recovery

The image pull filled the root filesystem and blocked the first final-plan Ansible
temporary directory. Removed only unused Fasnacht image caches v0.1.41/42/43 after
verifying their identical digests remain available in Docker Hub. No containers,
volumes, database files or current rollback images were removed. Final state: 2.7 GiB
free, 94% used. Further cache/retention maintenance is advisable before more releases.

## Reapply and rollback

Use `make plan-home` then `make deploy-home` with absolute `RELEASE_FILE` pointing to
`releases/home-frontends-20261124.json`; rollback selects
`releases/home-frontends-20261124-rollback.json` through the same commands.
Use the existing protected Home become-vars file; never embed passwords in commands.
Private configuration backup: `/opt/oldap/compose/routine-update-20261124T224917713276Z`.
Rollback is image-only and requires no database restore. Global `releases/current.json`
and all unrelated pending workspace changes are retained.
