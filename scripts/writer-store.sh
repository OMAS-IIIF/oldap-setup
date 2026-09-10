#!/bin/sh
# Startup refuses a missing AOF store. Bootstrap is a separate, one-shot Ansible
# operation permitted only for a new, empty installation with no provision marker.
set -eu
case "${1:-run}" in
  bootstrap)
    test -z "$(ls -A /data)" || { echo 'Writer bootstrap requires empty storage' >&2; exit 1; }
    redis-server --bind 127.0.0.1 --port 6399 --dir /data --appendonly yes \
      --appendfsync always --save '' --daemonize yes --pidfile /tmp/bootstrap.pid
    trap 'redis-cli -p 6399 shutdown nosave >/dev/null 2>&1 || true' EXIT INT TERM
    attempts=0
    until redis-cli -p 6399 ping 2>/dev/null | grep -qx PONG; do
      attempts=$((attempts + 1))
      test "$attempts" -lt 50 || { echo 'Bootstrap Redis did not start' >&2; exit 1; }
      sleep 0.1
    done
    redis-cli -p 6399 shutdown nosave
    trap - EXIT INT TERM
    test -s /data/appendonlydir/appendonly.aof.manifest
    ;;
  health)
    export REDISCLI_AUTH="$(cat /run/oldap-writer/password)"
    cli() {
      redis-cli --tls --cacert /run/oldap-writer/ca.crt --sni "$WRITER_HOST" \
        -h "$WRITER_HOST" -p "$WRITER_PORT" --user writer --raw "$@"
    }
    cli PING | grep -qx PONG
    state="$(cli INFO persistence | tr -d '\r')"
    echo "$state" | grep -qx 'aof_enabled:1'
    echo "$state" | grep -qx 'aof_last_write_status:ok'
    test "$(cli WAITAOF 1 0 5000 | head -1)" = 1
    ;;
  run)
    test -s /data/appendonlydir/appendonly.aof.manifest || {
      echo 'Writer AOF is missing. Stop all writers and follow recovery procedure.' >&2; exit 1;
    }
    exec redis-server /run/oldap-writer/redis.conf
    ;;
  *) echo 'Expected bootstrap or run' >&2; exit 2 ;;
esac
