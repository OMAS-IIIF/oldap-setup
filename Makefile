.PHONY: deploy-rosy rollback-rosy deploy-vm show-version

API_VERSION = $(shell cd ../oldap-api; git describe --tags --abbrev=0)
APP_VERSION = $(shell cd ../oldap-app; git describe --tags --abbrev=0)
TOOLS_VERSION = $(shell cd ../oldap-tools; git describe --tags --abbrev=0)

# Docker image repo (adjust to yours)
IMAGE_API = lrosenth/oldap-api
IMAGE_APP = lrosenth/oldap-app
IMAGE_FASNACHTS = lrosenth/fasnachts-page

# Helper shell command to get latest sever tag from Docker Hub
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

latest-api:
	$(call latest_tag,$(IMAGE_API))

latest-app:
	$(call latest_tag,$(IMAGE_APP))

latest-fasnacht:
	$(call latest_tag,$(IMAGE_FASNACHTS))

copy-ssh-key:
	ssh-copy-id rosenth@dhlab-oldap.dhlab.unibas.ch

#deploy-rosy:
#	 ansible-playbook -i inventory.ini deploy-oldap.yml \
#		-e oldap_api_tag=v0.1.3 \
#		-e oldap_app_tag=v0.3.2 \
#		--ask-become-pass
deploy-rosy:
	ansible-playbook -i inventory.ini oldap-deploy.yml \
		$(if $(API_VERSION),-e oldap_api_tag=$(API_VERSION),) \
		$(if $(APP_VERSION),-e oldap_app_tag=$(APP_VERSION),) \
		$(if $(TOOLS_VERSION),-e oldap_tools_tag=$(TOOLS_VERSION),) \
		-l oldap-test \
		--ask-become-pass

soft-reset-rosy:
	ansible-playbook -i inventory.ini oldap-playbook.yaml \
		-e oldap_reset=soft \
		-l oldap-test \
		--ask-become-pass

deploy-vm:
	ansible-playbook -i inventory.ini oldap-deploy.yml \
		$(if $(API_VERSION),-e oldap_api_tag=$(API_VERSION),) \
		$(if $(APP_VERSION),-e oldap_app_tag=$(APP_VERSION),) \
		$(if $(TOOLS_VERSION),-e oldap_tools_tag=$(TOOLS_VERSION),) \
		-l oldap-prod \
		--ask-become-pass



copy-trigs:
	cp ../oldaplib/oldaplib/ontologies/admin.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/oldap.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/shared.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/standard/dcterms.ttl ./files/
	cp ../oldaplib/oldaplib/ontologies/standard/schemaorg.ttl ./files/
	cp ../oldaplib/oldaplib/ontologies/standard/skos.ttl ./files/