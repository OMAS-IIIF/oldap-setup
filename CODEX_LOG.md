# CODEX_LOG

### Update 2026-06-16 23:56
- Decisions: Deploy `oldap-harvesters` as a no-restart Docker Compose job in both `tools` and `harvesters` profiles so it remains analogous to `oldap-tools` while allowing targeted harvester runs.
- Implementation: Added the Compose service, harvester image tag/env paths, Ansible host directories/config rendering/optional Vault-backed secret writes, `templates/harvesters.toml.j2`, Makefile tag propagation, group defaults, and README/context documentation.
- Open: Provide `oldap_harvesters_europeana_api_key` and `oldap_harvesters_oldap_password` via Ansible Vault or create `/srv/storage/oldap-data/oldap-harvesters/secrets/europeana.key` and `oldap.password` manually before running the job.
- Risks/Assumptions: Assumes the harvester image entrypoint accepts `--config /app/harvesters.toml --write-oldap`, that `user_id = "rosenth"` is the intended default unless overridden, and that a world-writable log directory is acceptable for container UID compatibility.

### Update 2026-05-31 23:20
- Decisions: Treat the production deployment render as still open because Ansible could not reach the server.
- Implementation: Validated the cleaned inventory and production host variables; ran the production deployment command, but SSH to `dhlab-oldap.dhlab.unibas.ch:22` timed out before facts were gathered.
- Open: Re-run `ansible-playbook -i inventory.ini oldap-deploy.yml -e oldap_api_tag=v0.2.4 -e oldap_app_tag=v0.2.2 -e oldap_tools_tag=v0.3.5 -e fasnachts_page_tag=v0.1.18 -l oldap_prod` once the server or network path is reachable.
- Risks/Assumptions: No remote files were changed during the failed deployment attempt.

### Update 2026-05-31 23:18
- Decisions: Keep only underscore-based Ansible inventory groups to avoid invalid group-name warnings and duplicate host definitions.
- Implementation: Removed hyphenated duplicate groups from `inventory.ini`; moved shared GraphDB/Caddy defaults into `[oldap:vars]`; set production `public_upload_url` to `https://media.oldap.org/upload` and aligned `public_iiif_url` with `https://media.oldap.org`; updated Makefile limits to `oldap_test` and `oldap_prod`; added project context files.
- Open: Re-run the production deployment so `/opt/oldap/compose/.env` is rendered with the corrected production media URLs.
- Risks/Assumptions: Assumes `media.oldap.org` is the intended public IIIF/media host for production.
