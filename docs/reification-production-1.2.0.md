# Reification 1.2.0 — production deployment

The owner explicitly authorized promotion to oldap.org after home acceptance.
The exact home-tested immutable API/tools image references were reused without
rebuild, retagging or new package publication. API and oldaplib now report 1.2.0.

## Scope and outcome

Only API and identity containers were replaced. Jena, Redis, Caddy, oldap-app,
SALSAH and FasnachtsPage retained their container IDs. The existing Jena 1.1.0
service was retained. No tools service exists in this production layout; the
release selection pins tools 1.2.0 without provisioning or starting a service.
Harvester selections, schedules, configuration and business data were not changed.

`releases/production-1.2.0.json` retains the two exact promoted image references.
The API/tools entries in `releases/current.json` now match, preventing subsequent
routine updates from reverting these components. All other entries are preserved.

The ontology update added the same nine triples as home for AssertionAnnotation,
ReifierShape and historyReifierSnapshot. It acquired the existing batch-maintenance
lock followed by the recovery lock and rejected active recovery maintenance.
The original oldap:onto graph and exact additive rollback were saved before the
update. Readback confirms 75 triples instead of 66, with zero missing additions.
No SHACL graphs, data graphs or fulltext indexes were rewritten.

## Acceptance

Public health/status and Fasnacht landing page return 200. Health reports v1.2.0,
status ok and Jena reachable. The new reifier model endpoint rejects anonymous
requests with 401. Installed library/API versions and feature imports pass.
The subsequent explicit production deployment plan shows no configuration changes.
The reused release previously passed 99 installed API/library tests per architecture,
packaged Jena integration and tools startup/travel-YAML checks. No production
business-data writes were used for acceptance.

## Recovery

Image/config backup: `/opt/oldap/compose/routine-update-20261114T222409302649Z`.
Ontology before-graph and exact DELETE DATA rollback:
`/srv/storage/oldap-releases/20261114-reification-1.2.0/`.
Private local logs and rollback selection:
`~/Library/Application Support/OLDAP/releases/20261114-1.2.0-production/`.

Use the shared updater with the retained previous API digest for image rollback;
retain all annotation/history data and prevent incompatible older writers from
modifying annotated resources. An image rollback does not authorize restoring or
clearing the database. Ontology rollback must use the same two coordination locks.

[Exact digests and acceptance receipt](reification-production-1.2.0-results.json).
