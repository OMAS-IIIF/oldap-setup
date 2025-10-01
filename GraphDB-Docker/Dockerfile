FROM ontotext/graphdb:11.1.0

LABEL authors="rosenth"

COPY ../files/oldap-config.ttl /opt/graphdb/home/repositories/oldap-config.ttl
COPY import-data/ /opt/graphdb/import/
COPY docker-entrypoint-init.sh /docker-entrypoint-init.sh

ENTRYPOINT ["/docker-entrypoint-init.sh"]