# Production operational preflight — 2026-11-08

Read-only SSH/Ansible inspection of both production VMs and the office receiver.
No services, images, schedules, secrets or production files were changed. The
Ansible changed count reflects only a local inventory evidence file.
See `production-operational-preflight-results.json` for image IDs and results.

## Verified boundaries

- The API Caddyfile, frontends.json, archive policy and media Caddyfile hashes
  still match the frozen production package. This is not a complete resolved
  Compose/credential drift check; repeat that at final freeze.
- API VM: approximately 16 GiB RAM, 12 GiB available and 371 GiB free data space.
  Media VM: approximately 16 GiB RAM, 14 GiB available and 780 GiB free data space.
  Office receiver: approximately 1.6 TiB free. These are point-in-time readings.
- Exact candidate images: zero of eight API service references and one of six
  media service references are locally available. Counts refer to services,
  not distinct image blobs. Preload and verify immutable IDs before downtime.

## Concrete operational integration gaps

1. `run-harvester.sh` and `run-swisscovery.sh` recognize Jena by the filename
   `jena-compose.yml` in COMPOSE_FILE. The accepted production core package
   intentionally resolves everything into `docker-compose.yml`; the current
   launchers would select the legacy writer stack. The core package also omits
   batch services. Prepare a separate pinned batch overlay with production
   credentials, provider config, OCR model, Jena endpoint/keys and maintenance
   lock; select the backend explicitly or from resolved configuration. Test both
   providers with network-isolated CLI fixtures before installing. Do not enable
   schedules merely after changing backend detection.
2. `oldap-jena-home-backup.yml` fixes the source host and API storage paths to
   home.org. Production uses a different isolated state root and requires the
   shared harvest/backup lock and existing SUCCESS/FAILURE mail. Extract the
   proven snapshot mechanics behind explicit environment inputs; retain strict
   host/path validation, clean drain and recovery, and publish the ready marker
   only after successful archive comparison and service recovery.
3. `pull-home-snapshot.py` deliberately fixes both endpoints to home.org. The
   office receiver needs an explicit production endpoint policy, coordinated
   snapshot acceptance, Borg retention and protected secrets/key recovery. Do
   not simply substitute hosts in the old live-media rsync job. Keep the old
   GraphDB history and old receiver job intact until replacement acceptance.

## Next execution order

Prepare and test the batch configuration and producer/receiver adaptation
locally; preload exact images without starting containers. Revalidate source
configuration and schedules before the agreed final pause. Perform fresh paired
capture, migration and all nine private acceptance checks. Activate replacement
backup/harvest schedules only after their production-specific checks pass.

The core package remains unchanged. These findings do not invalidate the model,
API, fulltext or pre-opening rollback rehearsals, and do not authorize treating
operational acceptance as complete.

## Follow-up

The provider selectors, pinned batch supplement, shared producer and explicit
production receiver policy are now prepared; see
`production-operational-integration.md`. Deployment/scheduling and final production
acceptance remain open. The preflight above records the original findings.
