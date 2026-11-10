# SALSAH 0.0.3 release — 2026-11-10

## Artifact and scope

- Source: salsah-2 release commit `dae1bb96c0faa2cb071db22403eac85e6ae757a1`.
- Correction: both SHACL `inversePath` and legacy `inverseOf` fields are excluded
  from writable relation controls in resource editing and staging catalogue.
- Published tag: `lrosenth/salsah-2:v0.0.3`.
- Multi-platform digest: `sha256:27cf49a30537b8931f4173e6bb86b77dcd44049065934a2d9aa9bf5ac5937406`.
- AMD64 manifest: `sha256:9c755cf14330f5a44ab5b46943a0f6fa529743400416060f27c22e17ca6371f1`.
- ARM64 manifest: `sha256:5e5dce10bfbf5559863b7f3c5a6c3d54bb08976569922bbb94f43af3b5830f06`.

Both architectures were built from a clean Git archive, loaded locally, started
and tested for package version 0.0.3, HTTP 200 health/status=ok and the login page.
The same images were pushed without rebuilding. No latest tag was published.
Prior source acceptance: 115 unit/component tests, 20 mocked browser workflows,
build/typecheck and live read-only local Jena API checks for Chama/Fasnacht.

The dedicated immutable selection is `releases/salsah-0.0.3.json`.
Use shared `plan-home`/`deploy-home` or `plan-vm`/`deploy-vm` with that RELEASE_FILE
and the appropriate protected Ansible credential file. This replaces only SALSAH,
preserves installed API/media origins and holds installed coordination locks.
No migration, API/database restart or media-host update is needed.

## Home acceptance

- Applied successfully through the shared Jena updater.
- All seven other container identities stayed unchanged; only SALSAH restarted.
- Runtime package version is 0.0.3; API/media/origin retain their home HTTPS URLs.
- Public HTTPS health and browser-rendered login page pass.
- Configuration rollback: `/opt/oldap/compose/routine-update-20261110T160757640644Z`.
- Previous image: `lrosenth/salsah-2@sha256:83ef7d4910f10826639ab2e5078b4445413ddb0f71d581c4378e1be6d0c1a8c3`.

For an image-only rollback, select the previous immutable image in a partial
release JSON and apply it with the shared updater. No database restore is needed.
Private build, architecture smoke and deployment logs reside under
`~/Library/Application Support/OLDAP/releases/salsah-0.0.3` on the control machine.

## Production acceptance

- Applied successfully through the shared Jena updater; only SALSAH restarted.
- All seven sibling container identities remained unchanged.
- Runtime version is 0.0.3; origin is https://salsah.org, API is
  https://api.salsah.org and media is https://media.oldap.org.
- Container health, public SALSAH/API HTTPS health and browser-rendered login pass.
- Configuration rollback: `/opt/oldap/compose/routine-update-20261110T182028946040Z`.
- Previous image is the same digest as the home predecessor recorded above.
- First apply attempt refused a busy coordination lock before making changes.
  A read-only lock inventory confirmed it was released; the subsequent attempt
  completed normally without bypassing or deleting locks.

Live authenticated edits/uploads have not been repeated during this
frontend-only release; browser workflow tests use mocks.
