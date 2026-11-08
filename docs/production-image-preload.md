# Production image preload and staged candidate — 2026-11-08

Production still runs GraphDB. All accepted core, provider and Tools images are
now downloaded on the intended production hosts. No existing application
container was restarted, replaced or stopped. The fourteen running container IDs
and image IDs still equal the retained source checkpoint; start times also remain
unchanged across the verified preload. Source API/media resolved configurations
still equal their frozen copies, including identity, policy and mount settings.

## Docker store compatibility correction

The API host uses Docker's classic image store, while home and the media host
expose OCI manifest/index identities. A bare `sha256:...` copied from home is not
necessarily a resolvable local image ID on the API host, even after a successful
pull. The first identity check correctly stopped on this mismatch; no candidate
was activated. The earlier raw-ID availability inventory alone did not establish
whether equivalent content was already cached in the classic store.

`oldap-production-images-preload.yml` now pulls reviewed `repository@sha256:...`
references and checks that the exact reference is present in RepoDigests, with
Linux/AMD64 architecture. It records the engine-specific local config ID separately.
This is not a substitution of versions or a relaxation to mutable tags.

`prepare-production-registry-package.py` verifies the original package manifest,
rejects extra/missing files and links, then creates a new package. It permits only
image-selector changes whose registry digest equals the original reviewed digest.
Runtime bytes, keys, policy, mount paths, application environment and commands
remain unchanged. The original package is retained for provenance.

**Deployment now selects `package-registry-01` and `batch-registry-01`, replacing
`package-final` and `batch-01` for installation.** The native target state root
remains `/srv/storage/oldap-jena-production-20261108`.

## Verified state

- Both core archives pass safe archive and target-state boundary checks; Compose
  resolves successfully. Real configurations differ only in image selectors.
- The actual production Docker engine ran the API's Jena library import and both
  harvester CLI help checks with networking disabled, without credentials or input
  data. No import was performed.
- Seventy-three production tests pass. Batch generation accepts immutable registry
  references as well as local IDs; mutable references remain rejected.
- Seven deployment artifacts are staged privately under
  `/srv/storage/oldap-release-candidate-20261108` on the API VM and retained under
  `OLDAP_BACKUP/releases/production-registry-20261108` on the office Mac. Every
  artifact's size and SHA-256 were checked at both destinations. Nothing was
  extracted into the active `/opt/oldap/compose` installation.
- API Docker storage has approximately 13 GiB free after preload. Data storage
  remains separate; check capacity again before the final paired snapshot.

See `production-preload-results.json` and the private
`deployment-registry-manifest.json` for exact identities and hashes. Do not use
old candidate archive hashes with the new selector package.

## Remaining activation boundary

The source backup/harvest timers remain unchanged. The production VM has the
existing mail transport, but no Ansible controller or dedicated root SSH public
identity for autonomous two-host backup. Prepare that operational arrangement
and the office pull/Borg/notification acceptance before declaring backup readiness.
The prepared manual producer is not evidence of an installed unattended service.

Then take a new coordinated source checkpoint in the agreed write window, migrate
that final RDF/state, and pass all nine private target checks. No source pause,
source data change, target opening marker or Jena production activation occurred
in this preload step.
