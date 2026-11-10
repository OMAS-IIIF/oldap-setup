.PHONY: deploy-home soft-reset-home deploy-vm show-versions latest-api latest-app latest-fasnacht latest-harvesters check-auth-secrets test-deployment-config

# Jena staging only. These inputs contain private keys and stay outside Git.
# No dependency on missing frontend sibling checkouts in OLDAP-Jena.
JENA_VARS ?= $(HOME)/ProgDev/OLDAP/auth/jena-candidate.yml
.PHONY: prepare-jena-home prepare-jena-vm test-jena-deployment
prepare-jena-home prepare-jena-vm:
	@test -f "$(JENA_VARS)"
	ansible-playbook -i inventory.ini oldap-jena-prepare.yml \
		-e "@$(JENA_VARS)" $(ANSIBLE_VAULT_ARGS) \
		-l $(if $(filter prepare-jena-home,$@),oldap_home,oldap_prod) --ask-become-pass

test-jena-deployment:
	../oldap-api/.venv/bin/python -m unittest tests.test_jena_deployment tests.test_jena_activation tests.test_jena_images tests.test_jena_home_acceptance tests.test_jena_home_backup -v

API_VERSION = $(shell cd ../oldap-api; git describe --tags --abbrev=0)
APP_VERSION = $(shell cd ../oldap-app; git describe --tags --abbrev=0)
TOOLS_VERSION = $(shell cd ../oldap-tools; git describe --tags --abbrev=0)
HARVESTERS_VERSION = $(shell cd ../oldap-harvesters; poetry version -s)
FASNACHTS_VERSION = v$(shell cd ../FasnachtsPage; node -p "require('./package.json').version")
SALSAH_VERSION ?= v$(shell cd ../salsah-2; node -p "require('./package.json').version")
AUTH_SECRETS_FILE ?= $(HOME)/ProgDev/OLDAP/auth/auth.vault.yml
ANSIBLE_VAULT_ARGS ?= --ask-vault-pass

# Docker image repo (adjust to yours)
IMAGE_API = lrosenth/oldap-api
IMAGE_APP = lrosenth/oldap-app
IMAGE_HARVESTERS = lrosenth/oldap-harvesters
IMAGE_FASNACHTS = lrosenth/fasnachts-page

# Helper shell command to get latest server tag from Docker Hub
define latest_tag
	@curl -s https://hub.docker.com/v2/repositories/$(1)/tags?page_size=100 \
	| jq -r '.results[].name' \
	| grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+$$' \
	| sort -V \
	| tail -1
endef

show-versions:
	@echo "Repository versions only; routine deployments use RELEASE_FILE (make show-release)."
	@echo "API-VERSION=$(API_VERSION)"
	@echo "APP-VERSION=$(APP_VERSION)"
	@echo "TOOLS-VERSION=$(TOOLS_VERSION)"
	@echo "HARVESTERS-VERSION=$(HARVESTERS_VERSION)"
	@echo "FASNACHTS-VERSION=$(FASNACHTS_VERSION)"
	@echo "SALSAH-VERSION=$(SALSAH_VERSION)"

latest-api:
	$(call latest_tag,$(IMAGE_API))

latest-app:
	$(call latest_tag,$(IMAGE_APP))

latest-fasnacht:
	$(call latest_tag,$(IMAGE_FASNACHTS))

latest-harvesters:
	$(call latest_tag,$(IMAGE_HARVESTERS))

copy-ssh-key:
	ssh-copy-id rosenth@dhlab-oldap.dhlab.unibas.ch

check-auth-secrets:
	@test -f "$(AUTH_SECRETS_FILE)" || { \
		echo "Missing authentication Vault file: $(AUTH_SECRETS_FILE)"; \
		exit 1; \
	}

test-deployment-config:
	python3 -m unittest tests/test_production_auth_config.py

# Routine Jena updates use published immutable images, never sibling HEAD guesses.
RELEASE_FILE ?= $(CURDIR)/releases/current.json
ANSIBLE_BECOME_ARGS ?= --ask-become-pass
LEGACY_RELEASE_OVERRIDES = $(foreach var,API_VERSION APP_VERSION TOOLS_VERSION HARVESTERS_VERSION FASNACHTS_VERSION SALSAH_VERSION,$(if $(filter command,$(origin $(var))),$(var)))
.PHONY: plan-home plan-vm show-release
show-release:
	@python3 -m json.tool "$(RELEASE_FILE)"
plan-home plan-vm deploy-home deploy-vm:
	@test -z "$(strip $(LEGACY_RELEASE_OVERRIDES))" || { echo "Use RELEASE_FILE instead of version overrides: $(strip $(LEGACY_RELEASE_OVERRIDES))" >&2; exit 2; }
	@test -f "$(RELEASE_FILE)"
	ansible-playbook -i inventory.ini oldap-jena-update.yml \
		-e 'oldap_release_file="$(RELEASE_FILE)"' \
		-e oldap_update_apply=$(if $(filter deploy-home deploy-vm,$@),true,false) \
		-l $(if $(filter plan-home deploy-home,$@),oldap_home,oldap_prod) \
		$(ANSIBLE_BECOME_ARGS)

soft-reset-home:
	ansible-playbook -i inventory.ini oldap-playbook.yaml \
		-e oldap_reset=soft \
		-l oldap_home \
		--ask-become-pass




copy-trigs:
	cp ../oldaplib/oldaplib/ontologies/admin.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/oldap.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/shared.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/standard/dcterms.ttl ./files/
	cp ../oldaplib/oldaplib/ontologies/standard/schemaorg.ttl ./files/
	cp ../oldaplib/oldaplib/ontologies/standard/skos.ttl ./files/

# Existing production host only. This prepares configuration and writer Redis,
# but does NOT start API/tools/harvesters or migrate model, roles or data.
# First follow docs/production-preparation.md; stop writers and verify backups.
# activate-vm: first start AFTER verified migration/operator installation. Loads
# the same Vault/Writer inputs and starts only API + both frontends (--no-deps).
# GraphDB/init jobs, media workers and the backup timer are not started by it.
# Requires bootstrap=false and all application writers still stopped.
WRITER_PRODUCTION_DIR ?= $(HOME)/ProgDev/OLDAP/auth/writer-production
.PHONY: prepare-vm activate-vm
prepare-vm activate-vm: check-auth-secrets
	@test -f "$(WRITER_PRODUCTION_DIR)/writer-secrets.yml"
	@test -f "$(WRITER_PRODUCTION_DIR)/deployment-vars.yml"
	ansible-playbook -i inventory.ini oldap-deploy.yml \
		-e "@$(AUTH_SECRETS_FILE)" $(ANSIBLE_VAULT_ARGS) \
		-e "@$(WRITER_PRODUCTION_DIR)/writer-secrets.yml" \
		-e "@$(WRITER_PRODUCTION_DIR)/deployment-vars.yml" \
		-e oldap_deploy_phase=$(if $(filter activate-vm,$@),activate,prepare) \
		-e oldap_api_tag=$(API_VERSION) -e oldap_app_tag=$(APP_VERSION) \
		-e oldap_tools_tag=$(TOOLS_VERSION) -e oldap_harvesters_tag=$(HARVESTERS_VERSION) \
		-e fasnachts_page_tag=$(FASNACHTS_VERSION) -e salsah_tag=$(SALSAH_VERSION) \
		-l oldap_prod --ask-become-pass

.PHONY: deploy-salsah-vm deploy-salsah-home install-salsah-vm install-salsah-home
deploy-salsah-vm deploy-salsah-home:
	ansible-playbook -i inventory.ini oldap-salsah-update.yml \
		-e salsah_tag=$(SALSAH_VERSION) \
		-l $(if $(filter deploy-salsah-vm,$@),oldap_prod,oldap_home) --ask-become-pass

# Explicit first-install boundary; does not provision or initialize infrastructure.
install-salsah-vm install-salsah-home:
	ansible-playbook -i inventory.ini oldap-salsah-install.yml \
		-e salsah_tag=$(SALSAH_VERSION) \
		-l $(if $(filter install-salsah-vm,$@),oldap_prod,oldap_home) --ask-become-pass

# Inputs contain existing remote config/model paths and the audited model checksum.
SWISSCOVERY_VARS ?= $(HOME)/ProgDev/OLDAP/auth/swisscovery-production.yml
.PHONY: install-swisscovery-vm
install-swisscovery-vm:
	@test -f "$(SWISSCOVERY_VARS)" || { \
		printf 'Missing Swisscovery installation inputs: %s\nSee docs/swisscovery.md or set SWISSCOVERY_VARS=/path/to/file.yml\n' "$(SWISSCOVERY_VARS)" >&2; \
		exit 1; \
	}
	ansible-playbook -i inventory.ini oldap-swisscovery-install.yml \
		-e "@$(SWISSCOVERY_VARS)" -e oldap_harvesters_tag=$(HARVESTERS_VERSION) \
		-l oldap_prod --ask-become-pass

# Opt-in weekly VM schedule; reuses installed images, secrets and backup mail transport.
.PHONY: install-harvest-schedule-vm
install-harvest-schedule-vm:
	ansible-playbook -i inventory.ini oldap-harvest-schedule-install.yml -l oldap_prod --ask-become-pass
