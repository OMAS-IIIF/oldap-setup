# Reification 1.2.0 home deployment


## Publication and home result

Both API and tools v1.2.0 images are published for AMD64 and ARM64. Installed
API/library regressions: 99 passed on each architecture. Packaged Jena identity,
transaction, persistence, restart and network-isolation acceptance passed on both.
Tools CLI and travel-YAML syntax/field checks passed on both architectures.
All 155 library runtime/data files in the image build match the published PyPI
wheel byte-for-byte; wheel builder metadata and an excluded HTTP scratch file differ.

Home now runs API/library 1.2.0; the on-demand tools selection also uses 1.2.0.
Only API and identity container IDs changed. Jena, Redis, Caddy and all three
frontends retained their container IDs. Public health/status and Fasnacht return
200; health reports Jena reachable and v1.2.0. The new model endpoint rejects
anonymous access with 401. The final image plan is unchanged. Ontology readback
shows 75 triples (66 + 9) and no missing additions. No live business-data writes
were used for acceptance. Production remains unchanged.

Use the explicit home release selection for subsequent home deployments:
`make deploy-home RELEASE_FILE=/Users/rosenth/ProgDev/OLDAP/oldap-setup/releases/home-1.2.0.json`.
Do not reuse the older default/1.1.0 selection for this home release.

Image/config rollback is retained at
`/opt/oldap/compose/routine-update-20261114T182634810080Z`.
The ontology before-graph and additive rollback are retained at
`/srv/storage/oldap-releases/20261114-reification-1.2.0/`.
Reverting application images never authorizes removing annotation data.

Digests, exact source commits, validation and recovery references:
[release receipt](reification-home-1.2.0-results.json).
