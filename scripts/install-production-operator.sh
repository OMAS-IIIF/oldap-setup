#!/usr/bin/env bash
# Install only reviewed operator configuration, never the private CA/server keys.
# The staged bundle includes SHA256SUMS and expected-inventory.txt, no Vault input.
set -euo pipefail
[[ $(id -u) == 0 && $(hostname -s) == dhlab-oldap ]] || exit 1
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
(cd "$stage" && sha256sum --check --status SHA256SUMS)
image=sha256:7319daf2b708a16043adb02e2dcb1ef5967b3cf5950da10a4372763e09616dac
[[ $(docker image inspect "$image" --format '{{.Architecture}}') == amd64 ]]
[[ ! -L /etc/oldap && ! -L /etc/oldap/writer-operator ]]
install -d -o root -g root -m 0755 /etc/oldap
install -d -o root -g root -m 0700 /etc/oldap/writer-operator
for file in operator.json ca.crt; do
  [[ ! -L "/etc/oldap/writer-operator/$file" ]]
  if [[ -e "/etc/oldap/writer-operator/$file" ]]; then
    cmp -s "$stage/$file" "/etc/oldap/writer-operator/$file" || {
      echo 'Existing configuration differs; explicit rotation review required.' >&2; exit 1;
    }
  fi
  install -o root -g root -m 0600 "$stage/$file" "/etc/oldap/writer-operator/$file"
done
install -o root -g root -m 0600 "$stage/check-production-operator.py" /etc/oldap/writer-operator/check-production-operator.py
install -o root -g root -m 0755 "$stage/run-production-recovery.sh" /usr/local/sbin/oldap-writer-recovery
inventory=$(cat "$stage/expected-inventory.txt")
[[ $inventory =~ ^[a-f0-9]{64}$ ]]
docker --host unix:///var/run/docker.sock run --rm --pull never \
  --name oldap-operator-installation-check --network compose_default \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL --security-opt no-new-privileges \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  --mount type=bind,src=/etc/oldap/writer-operator,dst=/run/oldap-operator,readonly \
  --entrypoint python "$image" /run/oldap-operator/check-production-operator.py "$inventory"
echo 'Operator installed and read-only checks passed. No recovery or restart executed.'
