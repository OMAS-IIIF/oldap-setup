# Jena migration Git checkpoint

This checkpoint records the reviewed migration sources on 2026-11-05. All repositories remain on `migration/jena`. It does not publish images, push branches, merge into main or change running services. The setup commit containing this document completes the checkpoint.

## Source revisions

| Repository | Revision |
| --- | --- |
| oldaplib | `e2805e13da7fdeb798d961b2887123682dc20e2c` |
| oldap-api | `491aed72f84bfe886362569eea8e08d3c52bdc1f` |
| oldap-tools | `a4be9592f3f66824d9365290c2f10d6a0e0cda69` |
| oldap-app | `6c01cc453566faa5ffe12a4d87b2ff73f3b6e5ec` |
| oldap-harvesters | `4609323335409e765fd1ed1a7258e55e0ea33b94` |
| oldap-mediaserver | `60c3678d7e6d5cb41a6114107cfc8ef6773c9f2b` |
| salsah-2 | `a0bb3ff3b70c5d6138deb63f10aaee5f5497ccac` |
| FasnachtsPage | `333b250d3910002b8bcb4338dba97f1720ca132d` |

API and Tools already had clean committed candidate states; the other six source repositories and setup receive local checkpoint commits.

## Verification

- Setup: 81 unittest cases, four skipped (77 passed).
- oldap-app: Svelte check without errors/warnings, 20 unit tests, four browser tests.
- Harvesters: 136 tests passed (35 subtests); run with `PYTHONPATH=.:src`.
- Mediaserver: 384 tests passed, 20 skipped, four subtests; changed-file Black and Poetry metadata checks pass. Use the complete existing Poetry environment, not an empty environment created for this checkout.
- Fasnacht: 18 archive tests, targeted ESLint and production build pass. The only new programmatic edit during this checkpoint explains the intentional non-reactive request-local Map.
- SALSAH: Svelte check without errors/warnings; no runtime behavior changes during this checkpoint.
- Library: changed Python syntax and whitespace checks pass; previous exact-service acceptance remains the runtime evidence (20 administration and 22 service checks, including crash/restart coverage).
- Candidate changes were checked for accidental credentials, unexpected binaries and whitespace errors. This is not a historical credential audit.

Packaged sources match the accepted 20261104-apps-rc1 snapshot: oldap-app 220/220, SALSAH 146/146 and mediahelper 42/42. Fasnacht matches 417/418, with only the explanatory lint comment differing. No image rebuild is required for that comment.

Read-only Chromium smoke checks on home return HTTP 200 for `/archive` and `/geschichten`. The archive renders 1,103 records (666 media, 422 objects, 15 events), and stories render real entries. An unauthenticated refresh returns 401 as expected; public archive loading succeeds. These checks do not replace authenticated write/upload acceptance or constitute a performance benchmark.

## Next gates

1. Bound total Jena process memory following the confirmed host OOM; heap alone is insufficient. Measure under representative load.
2. Coordinate automatic recovery of clients sharing the Jena network namespace after backend replacement/restart.
3. Implement and verify mobile worker SIGTERM draining before production operations.
4. Finish authenticated manual write/upload acceptance and off-host backup/restore verification.
5. Build/publish further candidates only for changes that require them, then coordinate final home acceptance, merges and the production 1.0 cutover.

Whole-dataset dump/upload synchronization between matching versions remains explicitly deferred. Existing deployment and rollback evidence is retained in the adjacent home, app, harvester and console documents.
