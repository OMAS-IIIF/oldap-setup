#!/bin/sh
# Source-specific manual/scheduled launch under the same in-container backup lock.
# Extra arguments replace the whole source default command, as with Compose run.
set -eu
compose_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source=${1:?Usage: run-harvester.sh europeana|swisscovery [CLI arguments]}
shift
case "$source" in
    europeana)
        files="$compose_dir/docker-compose.yml:$compose_dir/writer-compose.yml"
        command='oldap-harvest-europeana'
        ;;
    swisscovery)
        files="$compose_dir/docker-compose.yml:$compose_dir/writer-compose.yml:$compose_dir/swisscovery-compose.yml"
        command='flock --nonblock --conflict-exit-code 75 --no-fork /var/lib/swisscovery/locks/harvest.lock oldap-harvest-swisscovery'
        ;;
    *) echo "Unknown harvester: $source" >&2; exit 2 ;;
esac
# A Jena batch must preserve the installed backend/policy stack, rather than
# reconstructing the GraphDB writer stack above. Read only the literal selection;
# never source the .env file (it contains data, not executable shell code).
selection=$(sed -n 's/^COMPOSE_FILE=//p' "$compose_dir/.env")
case "$selection" in
    *jena-compose.yml*)
        files=""
        previous_ifs=$IFS
        IFS=:
        for file in $selection; do
            case "$file" in /*) ;; *) file="$compose_dir/$file" ;; esac
            files="${files:+$files:}$file"
        done
        IFS=$previous_ifs
        if [ "$source" = swisscovery ]; then
            files="$files:$compose_dir/swisscovery-compose.yml:$compose_dir/jena-swisscovery-compose.yml"
        else
            files="$files:$compose_dir/jena-harvesters-compose.yml"
        fi
        ;;
esac
# Scheduling is optional on home. Its shared maintenance lock remains mandatory
# when installed, and the Swisscovery-specific flock remains in its own overlay.
if [ -f "$compose_dir/harvest-schedule-compose.yml" ]; then
    files="$files:$compose_dir/harvest-schedule-compose.yml"
    entrypoint="python /run/oldap-batch/run-locked.py /run/oldap-batch/locks/maintenance.lock $command"
else
    entrypoint="$command"
fi
export COMPOSE_FILE="$files"
exec docker compose --project-directory "$compose_dir" --env-file "$compose_dir/.env" \
    run --rm --no-deps -T --name "oldap-batch-$source" \
    --entrypoint "$entrypoint" oldap-harvesters "$@"
