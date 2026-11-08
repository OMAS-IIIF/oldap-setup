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
# Consolidated releases supply complete, provider-specific Compose selections.
# They already contain the pinned image/backend/policy and do not need legacy
# overlays. Values are literal paths, never shell code. Keep old installs working.
case "$source" in
    europeana) batch_key=OLDAP_EUROPEANA_COMPOSE_FILE ;;
    swisscovery) batch_key=OLDAP_SWISSCOVERY_COMPOSE_FILE ;;
esac
batch_selection=$(sed -n "s/^$batch_key=//p" "$compose_dir/.env")
if [ -n "$batch_selection" ]; then
    files=""
    previous_ifs=$IFS
    IFS=:
    set -f
    for file in $batch_selection; do
        case "$file" in /*) ;; *) file="$compose_dir/$file" ;; esac
        if [ ! -f "$file" ]; then
            echo "Missing explicit batch Compose input; no job started" >&2
            exit 2
        fi
        files="${files:+$files:}$file"
    done
    set +f
    IFS=$previous_ifs
fi
# Scheduling is optional on home. Its shared maintenance lock remains mandatory
# when installed, and the Swisscovery-specific flock remains in its own overlay.
if [ -f "$compose_dir/harvest-schedule-compose.yml" ]; then
    files="$files:$compose_dir/harvest-schedule-compose.yml"
    entrypoint="python /run/oldap-batch/run-locked.py /run/oldap-batch/locks/maintenance.lock $command"
else
    entrypoint="$command"
fi
export COMPOSE_FILE="$files"
# Compose run --entrypoint discards the service command. Resolve defaults from
# the selected stack and pass them explicitly, preserving argument boundaries.
# Expanded configuration contains secrets: keep it in memory and never log it.
if [ "$#" -eq 0 ]; then
    exec python3 - "$compose_dir" "$source" "$entrypoint" <<'PYTHON'
import json
import os
import subprocess
import sys

folder, provider, entrypoint = sys.argv[1:]
base = ['docker', 'compose', '--project-directory', folder, '--env-file', folder + '/.env']
resolved = subprocess.run(base + ['--profile', '*', 'config', '--format', 'json'], capture_output=True, text=True)
if resolved.returncode:
    raise SystemExit('Cannot resolve harvester configuration; no job started')
command = json.loads(resolved.stdout)['services']['oldap-harvesters'].get('command')
if not isinstance(command, list) or not command or not all(isinstance(arg, str) for arg in command):
    raise SystemExit('Harvester requires a nonempty Compose command list; no job started')
os.execvp('docker', base + ['run', '--rm', '--no-deps', '-T', '--name', 'oldap-batch-' + provider,
                          '--entrypoint', entrypoint, 'oldap-harvesters', *command])
PYTHON
fi
exec docker compose --project-directory "$compose_dir" --env-file "$compose_dir/.env" \
    run --rm --no-deps -T --name "oldap-batch-$source" \
    --entrypoint "$entrypoint" oldap-harvesters "$@"
