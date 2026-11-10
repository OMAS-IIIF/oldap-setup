# Home routine Jena update acceptance — 2026-11-10

The owner authorized updating home through the shared `make deploy-home` workflow.
Production and the media VM were not changed.

## Result

- Preview passed against the installed home overlay layout.
- Initial apply stopped before changes because the batch maintenance lock was absent.
  Inspection confirmed no batch lock directory, scheduling overlay or scheduler
  services: this home installation only has namespace recovery coordination.
- Lock selection now requires recovery unconditionally, and batch locking whenever
  any installed batch coordination indicator exists. Missing installed locks still
  fail closed. Manual home snapshot operations must not overlap deployment.
- Apply succeeded, replacing API, identity and FasnachtsPage only. API/library and
  tools select 1.0.1, FasnachtsPage 0.1.51, standard/OCR harvesters 0.1.14. Exact
  immutable references are recorded in `../releases/current.json` at this commit.
- Tools and harvester pins changed for future jobs; no jobs/imports were started.
- Repeated identical apply returned `unchanged`, Ansible `changed=0`, exit 0.
  Independent before/after Docker inspection confirmed identical IDs, images and
  states for all eight running API-host containers.
- Post-update API status and archive HTTPS return 200. Site root redirects with
  308 to `/landingpage`, which returns 200 (the initial strict-200 probe therefore
  rejected the expected redirect; following it passed).
- Browser archive shows 1,103 records (666 media, 422 objects, 15 events). The
  selected “3 kostümierte Fasnächtler” detail displays metadata, six related media
  and a link to BMG Fasnacht 1909. These are read-only smoke checks.

## Recovery and evidence

Private configuration backup:
`/opt/oldap/compose/routine-update-20261110T133545506847Z`.
Use the locking and recovery instructions in `routine-production-updates.md`.

Local operator evidence, including replay output and sanitized container snapshots:
`~/Library/Application Support/OLDAP-Jena/releases/20261110-setup-home-update/`.

This acceptance does not claim a live rollback drill, authenticated write/upload
coverage, real OCR recognition, import execution or production deployment through
this new shared workflow. Fault-injected rollback is covered by local tests.
