#!/bin/bash
set -e

# Start GraphDB in background
/opt/graphdb/dist/bin/graphdb &

# Wait for GraphDB REST API to be ready
until curl -s http://localhost:7200/rest/repositories > /dev/null; do
  echo "Waiting for GraphDB..."
  sleep 2
done

# Create repository if not exists
curl -X POST -H "Content-Type:multipart/form-data" \
     -F "config=@/opt/graphdb/home/repositories/oldap-config.ttl" \
     http://localhost:7200/rest/repositories || true

# Load all RDF files in /opt/graphdb/import
for f in /opt/graphdb/import/*; do
  echo "Loading $f ..."
  curl -X POST -H "Content-Type:application/trig" \
       --data-binary @"$f" \
       "http://localhost:7200/repositories/oldap/statements"
done

# Keep GraphDB running in foreground
wait