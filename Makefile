.PHONY: deploy-home soft-reset-home deploy-vm show-versions latest-api latest-app latest-fasnacht latest-harvesters check-auth-secrets test-deployment-config

API_VERSION = $(shell cd ../oldap-api; git describe --tags --abbrev=0)
APP_VERSION = $(shell cd ../oldap-app; git describe --tags --abbrev=0)
TOOLS_VERSION = $(shell cd ../oldap-tools; git describe --tags --abbrev=0)
HARVESTERS_VERSION = $(shell cd ../oldap-harvesters; poetry version -s)
FASNACHTS_VERSION = v$(shell cd ../FasnachtsPage; node -p "require('./package.json').version")
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
	echo "API-VERSION=$(API_VERSION)"
	echo "APP-VERSION=$(APP_VERSION)"
	echo "TOOLS-VERSION=$(TOOLS_VERSION)"
	echo "HARVESTERS-VERSION=$(HARVESTERS_VERSION)"
	echo "FASNACHTS-VERSION=$(FASNACHTS_VERSION)"

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

deploy-home: check-auth-secrets
	ansible-playbook -i inventory.ini oldap-deploy.yml \
		-e "@$(AUTH_SECRETS_FILE)" $(ANSIBLE_VAULT_ARGS) \
		$(if $(API_VERSION),-e oldap_api_tag=$(API_VERSION),) \
		$(if $(APP_VERSION),-e oldap_app_tag=$(APP_VERSION),) \
		$(if $(TOOLS_VERSION),-e oldap_tools_tag=$(TOOLS_VERSION),) \
		$(if $(HARVESTERS_VERSION),-e oldap_harvesters_tag=$(HARVESTERS_VERSION),) \
		$(if $(FASNACHTS_VERSION),-e fasnachts_page_tag=$(FASNACHTS_VERSION),) \
		-l oldap_home \
		--ask-become-pass

soft-reset-home:
	ansible-playbook -i inventory.ini oldap-playbook.yaml \
		-e oldap_reset=soft \
		-l oldap_home \
		--ask-become-pass

# Routine production updates: publish immutable release images first.
# Uses installed secrets and Writer configuration; only application versions change.
# Does not provision Docker, restart GraphDB/Redis, migrate data, or change timers.
# Versions come from sibling repositories (make show-versions); override explicitly
# when keeping another component pinned, e.g. make deploy-vm APP_VERSION=v0.2.4.
# Media VM deployment remains separate. Initial setup uses prepare-vm/activate-vm.
deploy-vm:
	ansible-playbook -i inventory.ini oldap-update.yml \
		$(if $(API_VERSION),-e oldap_api_tag=$(API_VERSION),) \
		$(if $(APP_VERSION),-e oldap_app_tag=$(APP_VERSION),) \
		$(if $(TOOLS_VERSION),-e oldap_tools_tag=$(TOOLS_VERSION),) \
		$(if $(HARVESTERS_VERSION),-e oldap_harvesters_tag=$(HARVESTERS_VERSION),) \
		$(if $(FASNACHTS_VERSION),-e fasnachts_page_tag=$(FASNACHTS_VERSION),) \
		-l oldap_prod \
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
		-e fasnachts_page_tag=$(FASNACHTS_VERSION) \
		-l oldap_prod --ask-become-pass
