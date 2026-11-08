# Autonomous Jena backup controller — 2026-11-08

The production API VM now has an installed, **inactive** Jena backup controller.
The existing GraphDB backup and harvest schedules remain active and unchanged.
No source snapshot, service interruption or Jena activation occurred in this step.

## Execution and trust boundary

`oldap-jena-backup-controller-install.yml` installs Python venv support and an
isolated `ansible-core==2.20.5` controller at `/opt/oldap-backup-controller`.
Its inventory executes API tasks locally as root and media tasks through a
separate root SSH identity. It needs no development Mac, interactive login,
forwarded SSH agent or stored sudo password for normal operation.

The private key `/root/.ssh/oldap_jena_backup` is generated on the API VM and was
never fetched by the installer. Only its public key is installed on the media VM.
The authorization uses `restrict,from="API_SOURCE_ADDRESS"`: no PTY, forwarding or
user rc, and only connections originating from the API VM. This is still root
command execution, required for the reviewed drain, snapshot and recovery tasks;
it is not a forced-command read-only key. The installer requires the existing
SSH policy to permit public-key root access and does not loosen that policy.

The media host key is read through the established operator connection and pinned
in `/root/.ssh/oldap_jena_backup_known_hosts`. Strict checking and explicit key
selection are mandatory. If either VM's address or host key changes, review and
update this trust deliberately; never bypass checking to make a restore work.

The installed workflow is the same shared producer tested on home. Production
snapshots additionally retain the controller directory and its dedicated SSH
identity/trust files, along with runtime, provider inputs and unit configuration.
These are secret-bearing snapshots; the production off-host encryption/key
recovery policy remains part of receiver acceptance. Logs of the currently
running backup stay outside its own archive to avoid archiving a changing file.

## Service and notifications

- `oldap-jena-backup.service` runs as root with umask 0077 and uses the existing
  `/etc/oldap-harvest.env` sender/recipient settings and host mail transport.
- `oldap-jena-backup.timer` is installed but disabled/inactive. Its future schedule
  is 03:15 Europe/Zurich. `Persistent=false` avoids an unplanned daytime pause
  after a missed nighttime invocation; receiver freshness monitoring must report
  missed snapshots.
- `scripts/run-jena-backup.py` keeps logs under
  `/srv/storage/oldap-backup-runs`, serializes controller invocations and runs the
  installed playbook. The playbook separately owns the harvest/backup lock.
- SUCCESS requires process exit zero **and** a matching completed publication
  marker with both archive identities. Missing/invalid publication or execution
  failure sends FAILURE. A failed mail submission also makes the job fail.
  Emails contain only a status, snapshot ID, hostname and private log path; never
  raw logs, credentials or application records.
- No automatic failure retry is configured. A failed snapshot can intentionally
  retain its maintenance lock until the operator has recovered the stack.

Two explicit `[TEST - no backup]` messages exercised the installed mail path;
the owner confirmed delivery of SUCCESS and FAILURE. Unit tests also cover
process exceptions, nonzero exit, missing/corrupt completion markers and mail
failure. These notification tests did not invoke a backup.

## Acceptance performed

- The API-root controller successfully executes harmless Ansible modules on both
  VMs with its installed inventory and dedicated key.
- On the still-active GraphDB source, the real producer refuses execution before
  lock acquisition or snapshot directory creation. No service was stopped.
- Installed service/timer definitions pass `systemd-analyze verify`.
- Seventy-six production tests pass; the backup reporter's three tests were
  repeated after making journal status report mail failures as overall failures.
- All fourteen application container IDs, images and start times match the
  earlier production preload evidence. The source remains unchanged.
- The source-only controller bundle is retained and rehashed on the office Mac;
  it contains no generated private SSH key. See the results JSON for its current
  version, hash and key fingerprint.

## Activation and recovery

Do not enable the new timer while GraphDB is still the active backend. Keep the
old timer paused after the coordinated cutover, validate the first real Jena
snapshot and its office receiver/Borg recovery, then replace the scheduled job.
The old/new timers must not both be enabled for routine use. A successful home
snapshot or notification test is not a first production Jena snapshot.

For an approved manual Jena backup after cutover, use
`systemctl start oldap-jena-backup.service` and inspect its result and mail.
On failure, inspect the private run log and the matching
`oldap-jena-backup-lock-SNAPSHOT_ID` before retrying. Recover services first; then
explicitly release the retained lock unit. Do not delete the shared lock file.

A controller-host restoration requires the same supported Python/OS environment,
restored or reinstalled controller code/venv, its dedicated SSH identity, verified
media host trust and the matching source-IP-restricted authorization on media.
Keep schedules disabled until those checks and a full matched snapshot succeed.
Office repository encryption and exported-key fixture recovery now pass; the owner
confirmed independent key custody in Apple Passwords. See
[the receiver checkpoint](production-backup-receiver.md). Complete pair pulling,
freshness/notification/retention integration and the first real production Jena
backup remain open.
