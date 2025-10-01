.PHONY: deploy-rosy rollback-rosy

#deploy-rosy:
#	 ansible-playbook -i inventory.ini deploy-oldap.yml \
#		-e oldap_api_tag=v0.1.3 \
#		-e oldap_app_tag=v0.3.2 \
#		--ask-become-pass
deploy-rosy:
	 ansible-playbook -i inventory.ini oldap-rosy.yml \
		--ask-become-pass

rollback-rosy:
	ansible-playbook -i inventory.ini oldap-rosy.yml \
		-e rollback=true \
		--ask-become-pass

copy-trigs:
	cp ../oldaplib/oldaplib/ontologies/admin.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/oldap.trig ./files/
	cp ../oldaplib/oldaplib/ontologies/shared.trig ./files/