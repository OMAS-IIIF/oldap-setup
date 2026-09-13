"""Opt-in full Docker recovery rehearsal with disposable GraphDB/TLS Redis.

Owns UUID-named containers, network and volumes only. Never loads production
credentials or connects to production. Runs the actual amd64 operator CLI image.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from uuid import uuid4

from tests.test_writer_deployment import ROOT, fixture, render

OPERATOR = "oldap-writer-operator:0.7.18-amd64"


def command(*args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return result.stdout


def run(license_file: Path):
    """Create isolated services, invoke the operator protocol and clean owned assets."""
    if not license_file.is_file():
        raise ValueError("Local test license required")
    ident = "wr-docker-" + uuid4().hex[:12]
    names = [ident + "-db", ident + "-redis", ident + "-writer", ident + "-operator"]
    volumes = [ident + "-db-data", ident + "-redis-data"]
    with tempfile.TemporaryDirectory(prefix=ident) as tmp:
        path = Path(tmp)
        path.chmod(0o755)
        cfg = path / "redis"
        cfg.mkdir()
        cfg.chmod(0o755)
        values = fixture()
        values.update(
            oldap_writer_recovery_enabled=True,
            oldap_writer_recovery_password=uuid4().hex + uuid4().hex,
            oldap_writer_operator_password=uuid4().hex + uuid4().hex,
            oldap_writer_recovery_role_iri="urn:test:operator",
            oldap_writer_recovery_inventory_sha256="d" * 64,
        )
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
            "subjectAltName=DNS:writer.test",
            "-keyout",
            str(cfg / "server.key"),
            "-out",
            str(cfg / "server.crt"),
        )
        shutil.copyfile(cfg / "server.crt", cfg / "ca.crt")
        for name in ["redis.conf", "users.acl"]:
            (cfg / name).write_text(
                render(
                    "writer-"
                    + ("redis.conf" if name == "redis.conf" else "users.acl")
                    + ".j2",
                    values,
                )
            )
        (cfg / "password").write_text(values["oldap_writer_password"] + "\n")
        shutil.copyfile(ROOT / "scripts/writer-store.sh", cfg / "writer-store.sh")
        for f in cfg.iterdir():
            f.chmod(0o644)
        (path / "values.json").write_text(json.dumps(values))
        (path / "values.json").chmod(0o600)
        shutil.copyfile(ROOT / "files/oldap-config.ttl", path / "repository.ttl")
        shutil.copyfile(ROOT / "tests/recovery_fixture_client.py", path / "client.py")
        try:
            command("docker", "network", "create", ident)
            for volume in volumes:
                command("docker", "volume", "create", volume)
            common = [
                "-v",
                volumes[1] + ":/data",
                "-v",
                str(cfg) + ":/run/oldap-writer:ro",
            ]
            command(
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                *common,
                "--entrypoint",
                "/bin/sh",
                values["oldap_writer_image"],
                "/run/oldap-writer/writer-store.sh",
                "bootstrap"
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
                values["oldap_writer_image"],
                "-c",
                "chown -R 999:999 /data"
            )
            command(
                "docker",
                "run",
                "-d",
                "--name",
                names[1],
                "--network",
                ident,
                "--network-alias",
                "writer.test",
                "--user",
                "999:999",
                *common,
                "--entrypoint",
                "/bin/sh",
                values["oldap_writer_image"],
                "/run/oldap-writer/writer-store.sh",
                "run"
            )
            labels = ["--label", "com.docker.compose.project=" + ident]
            command(
                "docker",
                "run",
                "-d",
                "--name",
                names[0],
                "--network",
                ident,
                "--network-alias",
                "graphdb",
                *labels,
                "--label",
                "com.docker.compose.service=graphdb",
                "-e",
                "GDB_HEAP_SIZE=512m",
                "-v",
                volumes[0] + ":/opt/graphdb/home",
                "-v",
                str(license_file.resolve())
                + ":/opt/graphdb/home/conf/graphdb.license:ro",
                "ontotext/graphdb:11.3.0"
            )
            command(
                "docker",
                "run",
                "-d",
                "--name",
                names[2],
                "--network",
                ident,
                *labels,
                "--label",
                "com.docker.compose.service=oldap-api",
                "--entrypoint",
                "sh",
                values["oldap_writer_image"],
                "-c",
                "sleep 600"
            )
            result = command(
                "docker",
                "run",
                "--rm",
                "--platform",
                "linux/amd64",
                "--name",
                names[3],
                "--network",
                ident,
                "-v",
                "/var/run/docker.sock:/var/run/docker.sock",
                "-v",
                str(path) + ":/fixture",
                "--entrypoint",
                "python",
                OPERATOR,
                "/fixture/client.py",
                ident,
                timeout=420,
            )
            print(result)
        finally:
            for name in reversed(names):
                subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            for volume in volumes:
                subprocess.run(["docker", "volume", "rm", volume], capture_output=True)
            subprocess.run(["docker", "network", "rm", ident], capture_output=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--license", type=Path, required=True)
    args = parser.parse_args()
    run(args.license)
