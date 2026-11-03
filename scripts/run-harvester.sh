#!/bin/sh
# Source-specific manual/scheduled launch under the same in-container backup lock.
# Extra arguments replace the whole source default command, as with Compose run.
set -eu
compose_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source=${1:?Usage: run-harvester.sh europeana|swisscovery [CLI arguments]}
shift
case "$source" in
    europeana)
        files="$compose_dir/docker-compose.yml:$compose_dir/writer-compose.yml:$compose_dir/harvest-schedule-compose.yml"
        command='oldap-harvest-europeana'
        ;;
    swisscovery)
        files="$compose_dir/docker-compose.yml:$compose_dir/writer-compose.yml:$compose_dir/swisscovery-compose.yml:$compose_dir/harvest-schedule-compose.yml"
        command='flock --nonblock --conflict-exit-code 75 --no-fork /var/lib/swisscovery/locks/harvest.lock oldap-harvest-swisscovery'
        ;;
    *) echo "Unknown harvester: $source" >&2; exit 2 ;;
esac
# Absolute paths are required: COMPOSE_FILE resolves relative paths against the
# caller cwd, even with --project-directory. Override .env without editing it.
export COMPOSE_FILE="$files"
exec docker compose --project-directory "$compose_dir" --env-file "$compose_dir/.env" \
    run --rm --no-deps -T --name "oldap-batch-$source" \
    --entrypoint "python /run/oldap-batch/run-locked.py /run/oldap-batch/locks/maintenance.lock $command" \
    oldap-harvesters "$@"
