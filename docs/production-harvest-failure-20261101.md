# Production harvesting failure — investigation 2026-11-07

## Confirmed cause

The November 1 05:00 Europe/Zurich run exited after five seconds. Both provider
logs show argparse rejecting the invocation because `--config` is absent. They
failed before harvesting began; the source lock wrapper did start successfully.
The deployed Compose definitions do contain the correct provider-specific
commands. The launcher overrides the entrypoint using `docker compose run
--entrypoint`; Compose drops the default command when this option is supplied.
The scheduled runner passes only the provider name, so no replacement arguments
reach either CLI.

An isolated local reproduction used the already installed API image with network
mode `none`, entrypoint `/bin/echo` and command `--config /nonexistent-probe.toml
--write-oldap`. Ordinary `compose run` prints all three arguments. Overriding the
entrypoint with the same `/bin/echo` prints nothing. Neither invocation loads
application code or mounts production files. Both disposable containers exited.

The Jena branch's `scripts/run-harvester.sh` still contains the same CLI override.
Existing launcher tests mock the Docker invocation or replace `run` with `config`;
they verify overlay selection but do not detect this runtime argument behavior.

Required correction: retain the resolved provider-specific default argument list
when no user override was supplied. Explicit manual arguments must still replace
that entire list. Preserve both the shared maintenance lock and Swisscovery's
separate lock. Test the actual Compose run semantics for both sources, GraphDB
and Jena selection, scheduled defaults and explicit overrides without contacting
production. No launcher or production configuration was changed by this diagnosis.

## Independent mail failure

Both notification attempts failed with `nullmailer-inject: nullmailer-queue
failed: 1`; the scheduler correctly recorded failure and attempted the second
provider. This is a local queue-injection failure, not evidence of an SMTP server
rejecting the message. The root cause is not yet established.

Current read-only checks: nullmailer service active/success; about 18 GiB available
on /var; executable setuid mail (4755), queue/tmp owned by mail (0750), trigger
0622; executable filesystem is not mounted nosuid. These current observations do
not establish November 1's conditions or successful delivery. No mail was sent,
queue modified, service restarted or failed state reset. An explicitly authorized
bounded notification test and additional diagnostics remain necessary.

## Correction to rollback package coverage

Provider-specific inventory also found the installed Swisscovery overlay selects
`lrosenth/oldap-harvesters:0.1.13-ocr`, image config ID
`sha256:5e5a2610717bb599e44206481b55bd424ee2a8d3e86353e87650a3bccb16c0b9`.
The initial preparation package enumerated the base Compose selection, which did
not activate that overlay. Its verified archives remain valid but the batch set
is **not complete**: retain this OCR image too, and include provider-specific
configuration/secret/model bind inputs outside /opt/oldap. Enumerate the actual
launcher overlays, not only `--profile '*'` on the base selection. The previous
statement that production uses only one harvester image is superseded.

## Operational boundary

The weekly timer remains enabled; its next configured Sunday 05:00 run precedes
the intended Sunday-night migration. Without a launcher correction the scheduled
default invocation is expected to fail again. This investigation neither starts
harvesting nor changes that schedule. Keep the defect separate from migration
regressions: it already exists on the running GraphDB system.

## Correction and acceptance — 2026-11-07 evening

`run-harvester.sh` now resolves the selected Compose stack's `command` as a list
when no manual arguments are supplied, then passes that list explicitly to
`compose run`. Resolution enables all profiles because the harvester is profiled;
otherwise it can disappear from `config` output. Expanded configuration stays in
memory and is never logged. Explicit arguments still replace the whole default
command. Both maintenance locks and the backend/policy overlay selection remain.

Seven existing schedule tests and a real Docker runtime test pass. The latter
covers 12 combinations: GraphDB/Jena, Europeana/Swisscovery, and default/help/
explicit overrides, including argument whitespace and profiled services. The
fixture has no network and cannot import application data. The original live
launcher checksum was checked against the retained copy before atomic replacement
with backup. Both actual provider `--help` invocations pass on production. New
launcher SHA-256: `39db43969b5d10745f214a664e13eb69e59d3e937832d69c30753b03a6db0138`.
No full harvest was manually started; the normal next timer is November 8 05:00 CET.

Mail revalidation: a diagnostic message succeeds with the original 0077 umask.
The installed weekly reporter then handled synthetic success and failure results;
only its harvester subprocesses were replaced by fixtures. Both real notification
commands returned zero. The owner confirmed receipt of all three clearly marked
test messages. Do not claim umask caused the historical error: it was ruled out
as a reproducible current cause. No mail permissions/configuration were loosened;
the historical queue-injection cause remains unknown, while current end-to-end
notification delivery is accepted.

Retention now enumerates the actual Europeana and Swisscovery overlay selections,
not only the base stack. It includes read-only provider configuration, secrets,
OCR model and the separate `0.1.13-ocr` image. A regression test distinguishes base
versus OCR selection and excludes writable live report directories. The immutable
supplement `production-rollback-harvest-20261107` accompanies the earlier package;
its source tar comparison, transfer hashes, image load/re-export and office
receiver evidence are recorded in `jena-production-retention-results.json`.
