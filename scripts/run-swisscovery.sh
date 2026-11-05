#!/bin/sh
# Run the entire batch under the container's shared kernel lock. Preserve exit
# status: 75 means another batch owns the lock; other nonzero statuses are errors.
# Compose reads installed secrets/policy; no temporary environment export is needed.
set -eu
compose_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# Once scheduling is installed, manual launches also respect the backup lock.
if [ -f "$compose_dir/harvest-schedule-compose.yml" ] ||
    sed -n 's/^COMPOSE_FILE=//p' "$compose_dir/.env" | grep -q jena-compose.yml; then
    exec "$compose_dir/run-harvester.sh" swisscovery "$@"
fi
exec docker compose --project-directory "$compose_dir" \
    --env-file "$compose_dir/.env" \
    -f "$compose_dir/docker-compose.yml" \
    -f "$compose_dir/writer-compose.yml" \
    -f "$compose_dir/swisscovery-compose.yml" \
    run --rm --no-deps -T oldap-harvesters "$@"
