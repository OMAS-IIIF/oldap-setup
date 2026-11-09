# Scheduled backup SSH failure — 2026-11-09

## Cause and impact

Snapshot `20261109T021500Z-ccfc87ee` failed at 03:15 CET while inventorying the
media host, before any application stop or snapshot directory creation. All
fourteen application containers remained running. The deliberately durable
maintenance lock remained held and prevented competing harvest/backup work.

At 03:03:54 CET the media host journal records an Ansible `copy` operation from
`/var/ansible` replacing `/root/.ssh/authorized_keys`. The dedicated backup key
was absent afterwards. The owner's confirmation excludes a manual user change.
The responsible central configuration repository is not identified here.

Earlier access tests allowed GSSAPI. An interactive diagnostic authenticated with
Kerberos; explicitly forcing public-key authentication reproduced the failure.
Thus earlier successful access was insufficient evidence of ticket-independent
operation. No private key was exposed or regenerated.

## Correction

- Use `/root/.ssh/authorized_keys2`, already allowed by the effective sshd policy,
  for the existing source-address-restricted backup key. Leave the centrally
  managed primary file and sshd configuration unchanged. The installer checks
  that the secondary path is supported before writing it.
- Force `GSSAPIAuthentication=no` and `PreferredAuthentications=publickey` in
  both the controller inventory and its direct SSH acceptance check. Existing
  dedicated identity, strict host pinning, batch mode and restrictions remain.
- Add a privileged media connection check **before** acquiring maintenance.
  A later failure after lock acquisition still retains ownership for recovery.
- Include the secondary authorization file in the media snapshot roots.
- The installer's `--tags backup-ssh` path repairs and checks access without
  executing install-only timer assertions or changing the running schedule.

The targeted installer completed with only authorization/inventory changes.
The updated snapshot play is installed in `/opt/oldap-backup-controller`.
The failed run's exact lock unit was stopped only after confirming its pre-stop
failure and all running services; its ready marker disappeared normally. Never
unlink the shared flock inode to recover a held lock.

## Validation and remaining work

- Effective SSH policy and public-key fingerprint verified; source remains
  `131.152.238.105`, with forwarding/PTY disabled by `restrict`.
- Direct key-only login and Ansible modules on both hosts pass.
- A separate systemd unit, with no usable Kerberos ticket, ran both-host modules.
- A real deliberately invalid identity failed at the new preflight and created
  neither a maintenance lock nor a stopped service. Its private log is
  `/srv/storage/oldap-backup-runs/ssh-preflight-acceptance-20261109.log`.
- Two snapshot tests pass, covering success, failure before lock, failure while
  acquiring ownership and failure during capture. Both changed plays pass syntax.

A fresh full-size retry and office restore verification are pending the owner's
choice of interruption time. Observe the next central-management/nightly cycle;
we have not executed or altered that separate management system. If its policy
later changes the secondary key path, coordinate the key with the host managers
instead of repeatedly editing centrally owned configuration.
