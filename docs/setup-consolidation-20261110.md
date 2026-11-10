# Setup checkout consolidation — 2026-11-10

## Scope

Git consolidation only. Preserve existing implementation and operational evidence;
do not run deployment, migration, backup, imports or service control. The primary
checkout after synchronization is OLDAP/oldap-setup on main.

## Retained safety copies

Both original repositories have full Git bundles, binary tracked patches, status
and ref inventories, and archives/hash manifests of changed and untracked files:

/Users/rosenth/Library/Application Support/OLDAP-Jena/git-safety/20261110-141100-setup-consolidation

The old OLDAP checkout's working changes are additionally retained in the named
stash setup-consolidation-20261110-superseded-local. Do not apply this stash onto
current main: its changes are already represented by the newer implementation.
Ignored files and local private configuration remain in their original checkout;
this step does not archive or remove either repository.

## Reconciliation

- Remote main and the Jena experiment branch initially shared commit 3414ce3.
- OLDAP/main started at 938f7ed with uncommitted Swisscovery/scheduling work.
- Its oldap-update.yml, Swisscovery/scheduling playbooks, overlays, tasks,
  templates, documentation and remaining helper/tests match the Jena tree.
- All added Makefile/context lines and four local technical-log entries are
  already present in the Jena tree.
- run-harvester.sh, run-swisscovery.sh and test_harvest_schedule.py have newer
  Jena/backend-aware implementations. All former test names are retained.
- Retain pending Jena changes: Caddy upstream keepalive, scoped home client
  update locking/rollback, optional retired GraphDB inspection, and associated
  deployment/performance evidence. No new deployment behavior is implemented
  as part of consolidation.

## Next steps (not executed)

Unify routine Jena updates for home/production; reconnect deploy-home/deploy-vm,
release selection and build targets. Then update local API services controls,
which still address GraphDB. Test the workflow on home before production.
Existing Make deployment targets are not yet the consolidated Jena workflow.

Current component releases are documented by their primary repositories:
API/library/tools 1.0.1, FasnachtsPage 0.1.51, harvesters 0.1.14. Preserve the actual
installed per-environment selections rather than assuming home matches production.

## Validation

15 focused tests pass for harvesting, Swisscovery and home acceptance; the
client-update playbook passes Ansible syntax validation. New JSON evidence and
whitespace checks pass. These are local checks, not a new deployment rehearsal.
