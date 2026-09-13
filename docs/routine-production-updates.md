# Routine production updates

After the archive rollout, use `make deploy-vm` in oldap-setup for ordinary
application releases. It runs `oldap-update.yml` against `oldap_prod` and retains
the existing production configuration, including secrets, Writer Redis and recovery.
No local Vault file or Vault password is needed; the server sudo password is required.

## Workflow

1. Commit/tag the changed projects and build/publish their release images.
2. Run `make show-versions` in oldap-setup. All listed images must be published.
3. Finish interactive editing and active uploads/exports before the short update.
4. Run `make deploy-vm`.
5. Check the public pages, login, workspace and the changed workflow.

Versions are derived from sibling repositories, as before. To retain a specific
component release, override it, for example `make deploy-vm APP_VERSION=v0.2.4`.
The last production rollout retained oldap-app v0.2.4; its local repository may
already select a newer tag. Review `make show-versions` before deploying.

## Update boundary

The playbook validates the installed Writer overlay, pulls the five selected images,
and probes API/tools/harvester compatibility with the actual mounted policy and
persistent Writer store. These checks run before changing the installed version tags.
It saves a private timestamped `.env.before-update-*` file and changes only image tags
in `.env`. Compose updates API, oldap-app and FasnachtsPage without starting dependencies
or removing other containers, waits for readiness and checks API health.
Tools and harvesters receive new image selections for subsequent jobs; running jobs
are not replaced. Existing instances of unchanged applications are retained by Compose.

It does not provision Docker, apply templates, rotate secrets, alter ontologies or
permissions, migrate data, change timers, or start/restart GraphDB, Redis or init jobs.
Infrastructure/configuration changes and migrations require a separately reviewed
maintenance deployment; prepare-vm/activate-vm remain first-rollout boundaries.
The media VM uses its separate deployment command. SALSAH-2 is outside this target.

A failure after version selection may leave a partially updated application set.
Inspect the error and current container versions before retrying; there is no automatic
rollback or writer-lock reset. The saved `.env` is a private recovery reference.
