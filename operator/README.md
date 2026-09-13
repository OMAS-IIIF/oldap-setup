# Offline production recovery operator

This administrative image is separate from the API and from the Compose services
it removes. It embeds oldaplib from the pinned API 0.2.23 image and the Docker CLI
from a pinned upstream image. The Docker socket confers host administration; never
mount it in application containers or expose this launcher to web requests.

Build for the observed x86_64 production host:

```sh
docker build --platform linux/amd64 -f operator/Dockerfile -t oldap-writer-operator:0.7.18-amd64 .
```

Local verification on 2026-09-11: CLI/module help, Docker client/server handshake
(29.8.0/29.6.1), seven writer deployment/recovery tests, and shell syntax passed.
Image ID: sha256:e9d06b435b1d42b0ac4ca4839b4f320364b3ed915767027b2c75ffc69850a63c.
Full isolated Docker fencing/reconciliation/release rehearsal now passes with
GraphDB 11.3.0 and pinned TLS/AOF Redis; see rehearsal-2026-09-11.json.
It remains unpublished. The same image has now been transferred to production.
Docker Desktop reports the manifest ID above; the VM's classic image store uses
config ID `sha256:7319daf2b708a16043adb02e2dcb1ef5967b3cf5950da10a4372763e09616dac`.
This ID was read from the local Docker export manifest and verified against the
VM. Architecture, OS, complete image configuration and RootFS layer digests match.
The operator Docker CLI successfully contacted the VM daemon (29.8.0/29.6.2).
Root configuration/launcher installation is complete; the target read-only checker passed all fields. Temporary user-owned staging files were removed.

## Private configuration preparation

`scripts/prepare-production-writer.py --output ABSOLUTE_PATH` creates a NEW owner-only
directory outside Git; existing destinations are refused, not rotated. It generates
three independent 64-hex Redis passwords, a ten-year private CA and a one-year
server certificate for archive-writer.internal. It checks chain/hostname and writes
operator inventory plus archive policy. Configured policy is intended for eventual
activation; never point a running API at it before coordinated migration.

Prepared local directory: `/Users/rosenth/ProgDev/OLDAP/auth/writer-production`.
All files are mode 0600, directory 0700. `deployment-vars.yml` additionally contains
real local paths and the library-verified inventory digest; activation and compatible
releases are enabled; bootstrap is false after successful first provisioning. It is not loaded by normal Ansible commands.

Encrypt the Redis secret variables interactively before deployment:

```sh
ansible-vault encrypt /Users/rosenth/ProgDev/OLDAP/auth/writer-production/writer-secrets.yml
```

Use the existing deployment vault password; no password file is generated. Later
Ansible must load both the existing auth vault and this new vault; these files do
not replace one another. Private TLS keys/operator.json remain owner-only private
files and require protected backup/transfer. Keep ca.key on the control machine;
never transfer it to API, Redis or the operator. Record certificate expiry and
renew before expiry through the coordinated deployment procedure.

## Eventual VM installation and invocation

Only after separate deployment/acceptance authorization:
- Install only operator.json and ca.crt in root-owned `/etc/oldap/writer-operator`
  (directory 0700, files 0600). Do NOT copy the whole private generation directory.
- Put reconciliation JSON reports there with the same ownership/mode.
- Install `scripts/run-production-recovery.sh` outside all containers.
- Load the reviewed amd64 image; network compose_default must exist.
- Begin recovery through the authorized API/UI to obtain its operation UUID.
- Invoke the launcher with immutable image ID and UUID; optionally a report filename.

The launcher refuses other hostnames, mutable image tags, unprotected config files
and unsafe report names. A fixed container name prevents concurrent invocations.
It does not release locks: the backend's verified finish step does that. Root-owned
config must match the digest configured in the API. An interrupted controller may
leave a durable controller record; follow writer-recovery.md, never delete gates.

Production backup/restore, writer provisioning and archive migration are complete.
Outstanding: coordinated application rollout and public/API acceptance. The user encrypted writer-secrets.yml; the Vault
header and mode 0600 were verified without decrypting it.


Reproduce the isolated test (local license required, never a production repository):

```sh
python -m tests.probe_docker_recovery --license /private/local-test/graphdb.license
```

The fixture creates UUID-named containers/network/volumes, opens a real journaled
transaction without committing it, marks the writer uncertain, invokes the actual
operator CLI to fence/restart, observes absence of its pending marker and persistence
of the committed baseline, records evidence and finishes/retries recovery. Fixture
resources are removed on success/failure. The license is mounted read-only only into
the disposable GraphDB, never copied into Git or an image. API begin/finish uses the
backend directly; no production UI/HTTP or VM reboot acceptance is claimed.

## Prepared production installation

`~/oldap-operator-install` on the API VM is a user-only staging directory (0700,
files 0600) containing operator.json, public CA, launcher, read-only checker,
expected inventory digest and checksums. Private CA/server keys are excluded.
Run `sudo bash "$HOME/oldap-operator-install/install-production-operator.sh"`.
It refuses configuration changes to existing differing files, installs root-only
configuration in `/etc/oldap/writer-operator` and the launcher at
`/usr/local/sbin/oldap-writer-recovery`. It then runs read-only verification of TLS,
durability, inventory, Docker access and maintenance state. It never calls the
recovery protocol, restarts GraphDB or releases a lock. If verification fails,
installed files may remain; keep maintenance active and inspect the failure.

The eventual recovery launcher still requires the VM's immutable config image ID
and an operation UUID obtained through the authorized recovery API. Installation
is not an actual production recovery drill. Remove the user-owned staging copies
of operator.json/ca.crt after confirmed installation; retain the protected master
copy on the control machine.

Production installation completed on 2026-09-11: all seven read-only result fields
passed (recoveryExecuted=false). User-home staging directory was removed after
confirmation. The root-owned installation and private local master copies remain.
Restage the bundle before any reviewed reinstallation; the staging path above no
longer exists. No production recovery operation was initiated.
