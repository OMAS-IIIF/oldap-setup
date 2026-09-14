# Production publication activation verification

## Accepted deployment

On 2026-09-15, the production harvester completed two Europeana queries with
285 records seen, created and written, zero skipped and zero updated. All 285
entries were subsequently confirmed visible in FasnachtsPage. This establishes
successful import and visual acceptance; it is not a separate exhaustive audit
of all resource permissions or external media URLs.

API, tools and harvester inspection containers each reported oldaplib 0.7.20.
The running API image was v0.2.25; frontends were oldap-app v0.2.6 and
FasnachtsPage v0.1.38. The API mount source was verified as
`/opt/oldap/.env/archive-writer-client`, mounted at `/run/oldap-writer-client`.

The API was stopped while the existing archive-policy.json was backed up and
its `projects.fasnacht.publication` section added. The harvester then validated
model/configuration and reported `enabled: true, canPublish: true` for rosenth.
The subsequent import succeeded using the reviewed publication command.

## Persistent deployment configuration

The local authoritative file is
`/Users/rosenth/ProgDev/OLDAP/auth/writer-production/archive-policy.json`.
`deployment-vars.yml` in the same private directory references it through
`oldap_writer_policy_file`. It now contains the same reviewed publication
object used in the production activation instructions. The definition was
validated with oldaplib 0.7.20; all other parsed policy fields were verified
unchanged. A timestamped private backup was created before the local edit.
The full remote file was not downloaded or independently byte-compared.

Routine `make deploy-vm` retains the installed policy. Full prepare/activate
workflows load the private deployment variables and distribute this policy.
Keep this private directory backed up; do not commit credentials to Git.
`scripts/prepare-production-writer.py` is a new-installation bootstrap generator,
not an updater for this directory. A newly generated environment still needs
an explicit reviewed publication configuration before activation; do not replace
the established production policy with bootstrap defaults.

The tracked harvester TOML template also uses ArchiveMediaEditor DATA_UPDATE
without public draft grants and omits obsolete page limits. Compose forwards the
access-token signing settings needed by direct oldaplib login. Those settings
were adjusted on the VM during the deployment session.

## Evidence and sources

1. Production terminal output and visual acceptance supplied in the deployment
   conversation on 2026-09-15: versions, mounts, capabilities and harvest summary.
2. [Publication activation procedure](../../FasnachtsPage/docs/permissions/archive-roles.md).
3. [Reviewed publication definition](../../FasnachtsPage/docs/permissions/fasnacht-publication-policy.json).
4. [Writer mount template](../templates/writer-compose.yml.j2).
5. [Deployment targets](../Makefile): routine updates versus private configuration inputs.
6. Private local deployment-vars.yml and archive-policy.json at the directory
   above, inspected and synchronized on 2026-09-15; not public repository files.
