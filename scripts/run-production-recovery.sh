#!/bin/sh
# Run manually on the production VM as root, outside the managed Compose stack.
# This is a destructive runtime fence (containers, not data), NOT a status command.
# Supply an immutable locally loaded amd64 operator image ID and the API operation UUID.
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: sudo $0 sha256:IMAGE_ID OPERATION_UUID [REPORT_FILENAME]" >&2
    exit 2
fi
[ "$(id -u)" = 0 ] || { echo 'Run as root on the production VM.' >&2; exit 1; }
[ "$(hostname -s)" = dhlab-oldap ] || { echo 'Wrong host; refusing recovery.' >&2; exit 1; }
printf '%s' "$1" | grep -Eq '^sha256:[a-f0-9]{64}$' || exit 2
printf '%s' "$2" | grep -Eq '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' || exit 2
operator_dir=/etc/oldap/writer-operator
[ ! -L "$operator_dir" ] && [ -d "$operator_dir" ] || exit 1
[ "$(stat -c '%u:%a' "$operator_dir")" = 0:700 ] || exit 1
for name in operator.json ca.crt; do
    [ ! -L "$operator_dir/$name" ] && [ -f "$operator_dir/$name" ] || exit 1
    [ "$(stat -c '%u:%a' "$operator_dir/$name")" = 0:600 ] || exit 1
done
image=$1
operation=$2
if [ "$#" = 3 ]; then
    printf '%s' "$3" | grep -Eq '^[a-zA-Z0-9][a-zA-Z0-9_.-]*\.json$' || exit 2
    [ ! -L "$operator_dir/$3" ] && [ -f "$operator_dir/$3" ] || exit 1
    [ "$(stat -c '%u:%a' "$operator_dir/$3")" = 0:600 ] || exit 1
    set -- --report "/run/oldap-operator/$3"
else
    set --
fi
# Fixed name prevents concurrent operator containers. Do not add Compose labels:
# the controller must never remove its own execution environment during fencing.
exec docker --host unix:///var/run/docker.sock run --rm --pull never \
    --name oldap-recovery-operator --network compose_default \
    --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --cap-drop ALL --security-opt no-new-privileges \
    --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
    --mount "type=bind,src=$operator_dir,dst=/run/oldap-operator,readonly" \
    "$image" --config /run/oldap-operator/operator.json --operation "$operation" "$@"
