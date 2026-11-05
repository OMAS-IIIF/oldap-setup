# Jena batch harvesters

Build and acceptance instructions live in sibling `oldap-harvesters/docs/jena.md`.
Local acceptance passes 136 tests in each of three images, 17 deployment tests,
three offline lock tests and the owned full-model Jena integration. Evidence:
`../oldap-harvesters/docs/jena-results.json`. RC2 images are published and installed on home. Final evidence is in sibling
`oldap-harvesters/docs/jena-home-results.json`.

The harvester follows its own version sequence (0.1.14rc2); the library is the
coordinated OLDAP 1.0 candidate. Original GraphDB images/tags remain intact.

Publish accepted local standard/OCR candidates under separate Jena tags and
record their registry manifest digests. Never use a local Docker image ID as a
registry digest. Then run `oldap-jena-harvesters-install.yml` with inventory group
`oldap_home` and explicit `oldap_jena_harvesters_image` and
`oldap_jena_harvesters_ocr_image` variables (`lrosenth/oldap-harvesters@sha256:...`).
Use the existing protected become variables file, not command-line passwords.

The playbook requires api.home.org with an active Jena API. It pulls/checks both
images before changing configuration, backs up .env privately, installs the two
batch-only overrides and backend-aware launchers, and selects the supplied
images. It does not start jobs, recreate services or enable schedules.

Prerequisites: installed base/Jena/policy Compose selection in .env, existing
Europeana settings/secrets and authorized publisher membership. For a first
Swisscovery installation, supply controller-local `oldap_jena_harvesters_config_source`
and `oldap_jena_harvesters_model_source`. The installer preserves existing inputs,
checks the approved model SHA256 and validates the config. It installs the
Swisscovery override and private persistent directories. Review source/provider
IRIs against the migrated dataset before starting a batch. The launcher preserves the installed Compose selection, appends
the source-specific image override, and retains the optional shared maintenance
lock and the Swisscovery-specific flock. Existing GraphDB launch behavior stays
available in the original environment.

Before production, run a bounded real-source batch on home, inspect public API
results and text, and replay it to verify duplicate skipping. OCR runtime reuse
and isolated RDF persistence tests do not replace native end-to-end OCR
acceptance. Rollback requires restoring the saved .env and launcher backups;
imported records require their separately planned data rollback.

## Accepted home run, 2026-11-04

The first home attempt exposed retained GraphDB endpoint arguments; RC2 fixes
this at the harvester backend boundary. Missing home credential files were
populated from the existing approved Europeana key and the already configured
same-user home API login. The installer now checks nonempty credentials before
pull/configuration work. No passwords are recorded in repository evidence.

One Europeana record was created/published. One Swisscovery object and its PDF
were retained; both full CLI runs succeeded twice, with identical second-run API
snapshots and no changes to preexisting resources. Three public API reads pass.
The standard-image launcher separately skipped the new Europeana record. Native
OCR on the accepted image recognized a retained historic page in 24.07 seconds,
34 lines, byte-identical to the earlier reference. Full discovery, schedules and
production activation remain separate; the one real new home record is retained.
