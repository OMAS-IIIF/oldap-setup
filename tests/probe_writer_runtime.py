"""Explicit Docker integration probe for WR-01/02, isolated from application services.

Run with a Python environment containing redis, requests/Jinja/PyYAML and the
checked oldaplib. Uses UUID-named containers/volume and disposable TLS material;
never reads production credentials or flushes an existing cache. Results can be
saved with --output. Docker and openssl must be available.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import yaml
from urllib.parse import urlencode
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError
from oldaplib.src.mutation_gate import (
    mutation_gate,
    inspect_gate,
    MutationGateUnavailable,
    recover_gate,
    mark_gate_uncertain,
)
from oldaplib.src.writer_recovery import WriterRecovery, encoded, evidence_key
from tests.test_writer_deployment import ROOT, fixture, render


def command(*args, **kwargs):
    """Execute checked fixture commands without exposing credentials."""
    result = subprocess.run(args, capture_output=True, text=True, **kwargs)
    if result.returncode:
        print(result.stdout, result.stderr, file=sys.stderr)
        result.check_returncode()
    return result


def wait_ready(client):
    """Bound fixture startup; TLS/auth/configuration failures remain failures."""
    for _ in range(100):
        try:
            if client.ping():
                return
        except RedisError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Fixture Redis did not become ready")


def run():
    """Verify durable exclusivity, actual ACL/TLS, restart and missing-state refusal."""
    ident = "wr01-" + uuid4().hex[:12]
    volume, name, cache = ident + "-data", ident + "-writer", ident + "-cache"
    report = {}
    child = None
    image = fixture()["oldap_writer_image"]
    with tempfile.TemporaryDirectory(prefix="wr01-runtime-") as directory:
        path = Path(directory)
        path.chmod(0o755)
        cfg = path / "config"
        cfg.mkdir()
        cfg.chmod(0o755)
        # A disposable self-signed test CA/server certificate with validated SANs.
        command(
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=writer.test",
            "-addext",
            "subjectAltName=DNS:writer.test,DNS:localhost",
            "-keyout",
            str(cfg / "server.key"),
            "-out",
            str(cfg / "server.crt"),
        )
        shutil.copy2(cfg / "server.crt", cfg / "ca.crt")
        values = fixture()
        values["oldap_writer_password"] = uuid4().hex + uuid4().hex
        values.update(
            oldap_writer_recovery_enabled=True,
            oldap_writer_recovery_password=uuid4().hex + uuid4().hex,
            oldap_writer_operator_password=uuid4().hex + uuid4().hex,
            oldap_writer_recovery_role_iri="urn:fixture:operator-role",
            oldap_writer_recovery_inventory_sha256="d" * 64,
        )
        (cfg / "redis.conf").write_text(render("writer-redis.conf.j2", values))
        (cfg / "users.acl").write_text(render("writer-users.acl.j2", values))
        (cfg / "password").write_text(values["oldap_writer_password"] + "\n")
        shutil.copy2(ROOT / "scripts/writer-store.sh", cfg / "writer-store.sh")
        # Fixture mount is readable by UID 999; production tasks use 0400/0700 and chown.
        for file in cfg.iterdir():
            file.chmod(0o644)
        command("docker", "volume", "create", volume)
        common = ["-v", volume + ":/data", "-v", str(cfg) + ":/run/oldap-writer:ro"]
        try:
            command(
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                *common,
                "--entrypoint",
                "/bin/sh",
                image,
                "/run/oldap-writer/writer-store.sh",
                "bootstrap",
            )
            command(
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                *common,
                "--entrypoint",
                "/bin/sh",
                image,
                "-c",
                "chown -R 999:999 /data",
            )
            writer = yaml.safe_load(
                render(
                    "writer-compose.yml.j2", {**values, "inventory_hostname": "owner"}
                )
            )["services"]["archive-writer"]
            writer.update(
                container_name=name,
                ports=["127.0.0.1::6379"],
                volumes=[volume + ":/data", str(cfg) + ":/run/oldap-writer:ro"],
            )
            compose_path = path / "compose.yml"
            compose_path.write_text(
                yaml.safe_dump(
                    {
                        "services": {"archive-writer": writer},
                        "volumes": {volume: {"external": True}},
                    }
                )
            )

            def launch():
                return command(
                    "docker",
                    "compose",
                    "-p",
                    ident,
                    "-f",
                    str(compose_path),
                    "up",
                    "-d",
                    "--wait",
                    "--wait-timeout",
                    "40",
                )

            launch()
            first_id = command("docker", "inspect", "--format", "{{.Id}}", name).stdout
            launch()
            assert (
                command("docker", "inspect", "--format", "{{.Id}}", name).stdout
                == first_id
            )
            report["repeatedComposeDeploymentIdempotent"] = True
            port = json.loads(command("docker", "inspect", name).stdout)[0][
                "NetworkSettings"
            ]["Ports"]["6379/tcp"][0]["HostPort"]
            url = (
                f"rediss://writer:{values['oldap_writer_password']}@localhost:{port}/1?"
                + urlencode(
                    {
                        "ssl_cert_reqs": "required",
                        "ssl_check_hostname": "true",
                        "ssl_ca_certs": str(cfg / "ca.crt"),
                    }
                )
            )
            client = Redis.from_url(url, decode_responses=True, socket_timeout=5)
            wait_ready(client)
            command(
                "docker",
                "exec",
                name,
                "/bin/sh",
                "/run/oldap-writer/writer-store.sh",
                "health",
            )
            report["tlsHealthPassed"] = True
            for bad_url in (
                url.replace("@localhost:", "@127.0.0.1:"),
                url.replace(values["oldap_writer_password"], "b" * 64),
            ):
                try:
                    Redis.from_url(bad_url, socket_timeout=1).ping()
                except RedisError:
                    pass
                else:
                    raise AssertionError("Invalid hostname or credential accepted")
            report["invalidHostnameAndCredentialDenied"] = True
            try:
                client.flushall()
            except RedisError:
                report["destructiveAclDenied"] = True
            else:
                raise AssertionError("Writer ACL permits FLUSHALL")
            try:
                Redis(host="localhost", port=int(port), socket_timeout=1).ping()
            except RedisError:
                report["plaintextDenied"] = True
            else:
                raise AssertionError("Plaintext Redis accepted")
            # A separate Python process owns the gate, never touching GraphDB.
            env = {
                **os.environ,
                "OLDAP_STAGING_LOCK_REDIS_URL": url,
                "WR01_READY": str(path / "ready"),
            }
            code = """import os,time
from pathlib import Path
from oldaplib.src.mutation_gate import mutation_gate
with mutation_gate():
 Path(os.environ['WR01_READY']).write_text('ready')
 time.sleep(120)
"""
            child = subprocess.Popen(
                [sys.executable, "-c", code],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            for _ in range(100):
                if (path / "ready").exists():
                    break
                if child.poll() is not None:
                    raise RuntimeError("Fixture writer failed")
                time.sleep(0.1)
            assert (path / "ready").exists()
            before = inspect_gate(client)
            try:
                with mutation_gate(client=client, wait_seconds=0.2):
                    raise AssertionError("Two owners admitted")
            except MutationGateUnavailable:
                report["independentWriterBlocked"] = True
            # Clear an owned separate cache container only, then verify gate unchanged.
            command(
                "docker",
                "run",
                "-d",
                "--name",
                cache,
                image,
                "redis-server",
                "--save",
                "",
            )
            command("docker", "exec", cache, "redis-cli", "SET", "fixture", "cache")
            command("docker", "exec", cache, "redis-cli", "FLUSHDB")
            assert inspect_gate(client) == before
            report["cacheClearPreservesOwner"] = True
            child.kill()
            child.wait()
            child = None
            command("docker", "restart", name)
            new_port = json.loads(command("docker", "inspect", name).stdout)[0][
                "NetworkSettings"
            ]["Ports"]["6379/tcp"][0]["HostPort"]
            url = url.replace(":" + port + "/", ":" + new_port + "/")
            client = Redis.from_url(url, decode_responses=True, socket_timeout=5)
            wait_ready(client)
            assert inspect_gate(client) == before
            report["killedWriterOwnershipSurvivesRedisRestart"] = True
            recover_gate(
                client,
                expected_token=before["token"],
                writer_terminated=True,
                outcomes_reconciled=True,
                confirm_transaction_ended=lambda _: False,
            )
            # Empty transaction list is known: the owned fixture never contacted GraphDB.
            with mutation_gate(client=client):
                pass
            assert inspect_gate(client) is None
            report["controlledFixtureRecoveryPassed"] = True
            # Exercise the recovery protocol and actual pinned Redis ACLs. This
            # fixture never opens a GraphDB transaction; injected test evidence
            # validates transport/permissions, not the runtime-controller proof.
            api = Redis.from_url(
                url.replace(
                    "writer:" + values["oldap_writer_password"],
                    "recovery-api:" + values["oldap_writer_recovery_password"],
                ),
                decode_responses=True,
                socket_timeout=5,
            )
            operator = Redis.from_url(
                url.replace(
                    "writer:" + values["oldap_writer_password"],
                    "recovery-operator:" + values["oldap_writer_operator_password"],
                ),
                decode_responses=True,
                socket_timeout=5,
            )
            recovery = WriterRecovery(api, "fixture", inventory_digest="d" * 64)
            operation_id = str(uuid4())
            with mutation_gate(client=client):
                mark_gate_uncertain()
            operation = recovery.begin(
                operation_id=operation_id,
                expected_revision=recovery.status()["revision"],
                actor="urn:fixture:operator",
                reason="Validate disposable Redis protocol",
            )
            try:
                api.eval(
                    "return redis.call('SET',KEYS[1],ARGV[1])",
                    1,
                    evidence_key(operation_id),
                    "forged",
                )
            except RedisError:
                report["recoveryApiCannotForgeEvidence"] = True
            else:
                raise AssertionError("API can manufacture operator evidence")
            operator.set(
                evidence_key(operation_id),
                encoded(
                    {
                        "version": 1,
                        "method": "docker-domain-restart-v1",
                        "domain": "fixture",
                        "inventoryDigest": "d" * 64,
                        "operationId": operation_id,
                        "revision": operation["request"]["revision"],
                        "runtime": {"fixtureOnly": True},
                        "reconciliation": {"noDatabaseUsed": True},
                    }
                ),
            )
            completed = recovery.finish(
                operation_id=operation_id, actor="urn:fixture:operator"
            )
            assert completed["state"] == "completed" and inspect_gate(client) is None
            assert (
                recovery.finish(operation_id=operation_id, actor="urn:fixture:operator")
                == completed
            )
            report["auditedRecoveryAndExactRetryPassed"] = True
            api.close()
            operator.close()
            # Container recreation retains the same volume; ordinary creation is idempotent.
            command("docker", "rm", "-f", name)
            launch()
            report["containerRecreatedWithRetainedVolume"] = True
            # A fresh missing AOF volume must fail, even without a stale owner.
            missing = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    str(cfg) + ":/run/oldap-writer:ro",
                    "--entrypoint",
                    "/bin/sh",
                    image,
                    "/run/oldap-writer/writer-store.sh",
                    "run",
                ],
                capture_output=True,
                text=True,
            )
            assert missing.returncode != 0 and "Writer AOF is missing" in missing.stderr
            report["missingStorageRefused"] = True
            # Verify the rendered forwarding rules in an owned Linux network namespace.
            firewall = cfg / "firewall.sh"
            firewall.write_text(
                render(
                    "writer-firewall.sh.j2",
                    {
                        **values,
                        "oldap_writer_interface": "eth0",
                        "oldap_writer_allowed_sources": ["10.20.0.3/32"],
                    },
                )
            )
            firewall.chmod(0o644)
            check = command(
                "docker",
                "run",
                "--rm",
                "--cap-add",
                "NET_ADMIN",
                "-v",
                str(cfg) + ":/fixture:ro",
                "--entrypoint",
                "/bin/sh",
                image,
                "-c",
                "apk add --no-cache iptables >/dev/null && sh /fixture/firewall.sh && sh /fixture/firewall.sh && iptables -S DOCKER-USER",
            )
            assert check.stdout.count("-j OLDAP-WRITER") == 1
            report["linuxFirewallRepeatedApplyPassed"] = True

        finally:
            if sys.exc_info()[0] is not None:
                logs = subprocess.run(
                    ["docker", "logs", "--tail", "20", name],
                    capture_output=True,
                    text=True,
                )
                print(logs.stdout, logs.stderr, file=sys.stderr)
            if child is not None:
                child.kill()
                child.wait()
            for container in (name, cache):
                subprocess.run(
                    ["docker", "rm", "-f", container],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if (path / "compose.yml").exists():
                command(
                    "docker",
                    "compose",
                    "-p",
                    ident,
                    "-f",
                    str(path / "compose.yml"),
                    "down",
                )
            command("docker", "volume", "rm", volume)
    report["ownedFixturesRemoved"] = True
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
