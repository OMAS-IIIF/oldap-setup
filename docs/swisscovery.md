# Swisscovery CPU OCR deployment

The regular harvester release builds two images from the same checkout:
`lrosenth/oldap-harvesters:<version>` and `<version>-ocr`. The OCR variant is
currently published for Linux amd64 (production), with an isolated Python 3.12,
Kraken and CPU-only PyTorch runtime. The model is an explicit persistent input,
not a dependency downloaded during harvesting.

## First installation on the existing production VM

Publish a **new** harvester version with `make docker-build` in
`oldap-harvesters`; do not overwrite the already released 0.1.12 tag.
Create a private installation input file (for example
`~/ProgDev/OLDAP/auth/swisscovery-production.yml`):

```yaml
swisscovery_config_source: /users/staff/gkw/rosenth/swisscovery-production-full-2026-10-25/harvesters-swisscovery.toml
swisscovery_model_source: /users/staff/gkw/rosenth/swisscovery-production-full-2026-10-25/german_print.mlmodel
swisscovery_model_sha256: 542970897c3d4d4283e536d3270d86a91708ea2bff9b2bed97a1d5c7f6a569fe
```

These are paths **on the VM**. Use the approved configuration: it retains all
23 queries, existing source/provider identities, publication permissions and the
mounted OLDAP password file. For future inputs, obtain and verify the model hash
independently. Stop old ad hoc launchers before switching to this workflow.

Run from `oldap-setup`:

```sh
make install-swisscovery-vm
```

The installer copies approved inputs into
`/srv/storage/oldap-data/oldap-harvesters/swisscovery`, without overwriting existing
config/model files on repeated installation. It verifies the model checksum,
pulls the matching OCR release, checks the installed writer store, imports the
OCR runtime, loads the model and validates the configuration. It backs up `.env`
and selects only the verified harvester version. It does not restart services,
import records, render credentials or create a scheduler. Existing input changes
are a separate maintenance operation with the batch stopped.

## Start a batch on the VM

```sh
sudo /opt/oldap/compose/run-swisscovery.sh
```

The launcher combines the installed base Compose file, writer overlay and the
Swisscovery override. **Do not add `swisscovery-compose.yml` to `.env`'s ordinary
COMPOSE_FILE**: Europeana keeps its existing defaults. All credentials and writer
policy come from the installed configuration. The batch uses at most two CPUs and
5 GiB RAM; the harvester keeps its existing 64 MiB / 100-page PDF admission limits.
Compatible stored text is reused, and the 44 explicitly approved prior records
are retained even when excluded from new automatic selection. No records are
removed by this workflow.

The default command performs selection, catalog import, PDF enrichment and OCR
with layout evidence. JSONL selection/media reports append under `reports/` in
the persistent directory. Redirect console output to a dated operator log when
running unattended. Arguments after the launcher **replace** the complete Compose
command (for example `--help`); they do not append extra flags to the import.

## Overlap prevention

Every normal launch acquires a nonblocking `flock` on the same persistent
`locks/harvest.lock` before starting the CLI. A concurrent launch exits **75**
without querying or writing; errors have their ordinary nonzero exit codes. The
lock spans discovery, writes, PDF processing and OCR. `--no-fork` replaces flock
with the CLI as PID 1, so normal exit and container termination release the kernel
lock. The lock file may remain: **never delete or replace it while jobs run**.

This is a single-VM lock on a local Linux filesystem. Do not move the lock bind
onto NFS/SMB or macOS file sharing without verifying locking semantics. Ad hoc
launchers, `--entrypoint` overrides and jobs on other hosts bypass this batch lock.
Retire the old `launch_cli.py` for regular operation. OLDAP writer coordination
remains independently active for all database writes.

The optional [weekly harvesting installer](harvest-schedule.md) adds a Sunday
05:00 timer, per-source email reports and a shared backup/harvesting lock. The
Swisscovery installer alone does not install a timer. Once scheduling is installed,
this launcher delegates to the shared-lock launcher for manual runs too.

## Routine updates and rollback

After first installation, `make deploy-vm` detects the Swisscovery overlay,
refreshes the launcher/overlay and pulls and checks `<new-version>-ocr` before
persisting release tags. A missing/broken OCR image blocks version selection.
The update never starts harvesting; an already running container finishes using
its original image. Subsequent runs use the new selected version. The installed
config, model, reports and lock directory remain unchanged.

To roll back, choose a previously verified version for which **both** standard
and OCR images exist, using the normal release-update workflow. The initial
ad hoc `oldap-harvesters-ocr:0.1.12-cpu` is not a registry release pair.

## Verification

Run the Compose/configuration tests with an environment containing PyYAML and
Jinja2. The optional live test uses two different container names against one
Linux Docker volume, rejects overlap and verifies reacquisition after TERM/KILL:

```sh
python -m unittest tests.test_swisscovery_deployment tests.test_routine_update
SWISSCOVERY_LOCK_TEST_IMAGE=oldap-harvesters:swisscovery-ocr-check \
  python -m unittest tests.test_swisscovery_lock
```

The lock test does not contact OLDAP or external providers. On macOS it uses a
Docker volume deliberately: host file-sharing mounts need not preserve Linux
flock semantics across independent containers.
