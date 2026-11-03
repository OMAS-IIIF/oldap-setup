# Weekly production harvesting

The opt-in `oldap-harvest.timer` runs Europeana, then Swisscovery, on Sundays at
05:00 Europe/Zurich. The existing backup remains daily at 03:15. A persistent
timer catches up a missed run after downtime (including re-enabling an existing
timer with an overdue timestamp). A normal application deployment does not start
harvesting or re-enable a deliberately paused timer.

## Install once

First install Swisscovery and deploy the desired standard/OCR image pair. Then,
from the local `oldap-setup` checkout, with VPN/SSH available:

```sh
make install-harvest-schedule-vm
```

Ansible asks for the VM sudo password. No registry publication, image update,
model change, new source or import is performed by the installer itself. The
installer validates both CLIs with `--help` before enabling the timer. It refuses
installation while the backup, weekly service or a Compose harvester is active.
Use an idle maintenance window; do not start ad hoc jobs during installation.
First activation normally waits for Sunday; an existing overdue persistent timer
may immediately catch up. No test email is sent by installation.

Later, `make deploy-vm` maintains these files only when the timer is installed,
preserving mail settings and paused/enabled state. The weekly job always uses
the currently deployed image tags and installed source/writer configuration.

## Files on the VM

| Path | Purpose |
| --- | --- |
| `/etc/systemd/system/oldap-harvest.timer` | Weekly schedule and explicit timezone |
| `/etc/systemd/system/oldap-harvest.service` | Sequential job and journal output |
| `/etc/oldap-harvest.env` | Mail recipient/sender, initialized from the existing backup convention |
| `/opt/oldap/compose/run-weekly-harvest.py` | Run both sources and send per-source reports |
| `/opt/oldap/compose/run-harvester.sh` | Manual/scheduled source launcher |
| `/opt/oldap/compose/harvest-schedule-compose.yml` | Shared lock/script bind mounts |
| `/opt/oldap/compose/run-locked.py` | Kernel lock retained across exec |
| `/etc/systemd/system/oldap-backup.service.d/harvest-lock.conf` | Prepend the same lock to the existing backup command |
| `/srv/storage/oldap-data/job-locks/maintenance.lock` | Shared host/container lock; never delete/replace while jobs run |
| `/srv/storage/oldap-data/oldap-harvesters/scheduled-runs/` | Private timestamped per-source console logs |

The backup script `/usr/local/bin/oldap-backup.sh`, its environment and timer stay
unchanged. The drop-in retains them and wraps only ExecStart. No secrets are copied
into the harvesting mail environment. Service/drop-in replacements retain Ansible
backup copies. Source templates live in `templates/harvesting/`; installation and
routine maintenance share `tasks/harvest-schedule.yml`.

## Locks and manual runs

Each source acquires a blocking flock inside its container on the shared local
filesystem inode before discovery or writes. The backup service waits on the
same lock. If the initiating SSH/docker client disappears, a still-running
container retains its lock. It releases on command/container exit, including
crashes; a leftover lock file is normal. Swisscovery also retains its existing
source-specific nonblocking lock. A separate weekly-cycle lock prevents duplicate
manual invocations of the reporting script. Stable container names prevent a
second launcher from silently duplicating an orphaned run.

Use these entry points so manual work is covered too:

```sh
# Both sources, with email reports:
sudo systemctl start oldap-harvest.service
# One source, console output only:
sudo /opt/oldap/compose/run-harvester.sh europeana
sudo /opt/oldap/compose/run-swisscovery.sh
# Manual backup through its lock wrapper:
sudo systemctl start oldap-backup.service
```

Raw `docker compose run`, the previous ad hoc import scripts and direct execution
of `oldap-backup.sh` bypass the shared lock. Do not use them for normal operation.
The lock coordinates backup/harvesting, not ordinary interactive API edits.
Never move the lock directory to NFS/SMB; installation requires a local supported
filesystem. Commands run as the existing root container/backup user.

Stopping the reporting service is not a guaranteed stop of its Docker workloads.
Inspect `docker ps` and explicitly stop the relevant `oldap-batch-europeana` or
`oldap-batch-swisscovery` container when cancelling a job; do not delete lock files.
Stopping a job may leave a partial import; the next normal run preserves existing
records according to the source's existing policy. No automatic failure retry.

## Email and status

Two short messages use the existing host `mail` transport and the backup's sender
and recipient. Successful summaries say `No new entries added.` or
`XX new entries added.`, followed by created/updated/skipped/seen counters. The
Swisscovery message also includes aggregate PDF/OCR counters. Created refers to
the primary harvested records; PDFs are reported separately.

Nonzero exits (including partial PDF/OCR failures), missing final JSON summaries
and source mismatches never become a zero-new-entries success report. A failed
first harvester or mail command does not prevent the second source from running;
the cycle retains a failed exit status. No raw logs or credentials are emailed.
Transport failure is recorded in the journal; successful `mail` exit only confirms
local acceptance, not delivery to the recipient's inbox. Host crashes/cancellation
can prevent the reporting script from sending its final messages.

```sh
systemctl list-timers oldap-harvest.timer oldap-backup.timer
systemctl status oldap-harvest.service
sudo journalctl -u oldap-harvest.service --since 'last Sunday'
sudo systemctl disable --now oldap-harvest.timer  # pause future runs, not an active job
```

Logs are retained until the operator archives/removes them. To change the weekly
schedule under configuration management, edit the timer template and redeploy.
To change mail addresses, edit `/etc/oldap-harvest.env`; routine updates preserve it.

## Validation

`python3 -m unittest tests.test_harvest_schedule` covers real process/exec locking,
termination release, invalid summaries, no-new/new counters, failure reporting and
continuing after a source or mail failure. Existing Compose and routine-update
regressions also apply. Ansible syntax checks require no production mutation.
