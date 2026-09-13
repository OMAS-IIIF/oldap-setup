"""Opt-in rehearsal against a disposable restore of the approved production backup.

Run as python -m tests.probe_archive_migration from oldap-setup. Uses the local
GraphDB test license, isolated internal Docker network and UUID-owned volumes.
It never contacts production; only the restored fixture admin password changes.
Backup and reports remain outside Git in sibling BACKUP. Always removes fixtures.
"""

import sys, subprocess, tempfile, pathlib, shutil, json, time, os
from uuid import uuid4
from tests.test_writer_deployment import fixture, render
from tests.probe_docker_recovery import command

root = pathlib.Path(__file__).resolve().parents[2]
ident = "archive-migration-" + uuid4().hex[:10]
names = [ident + "-db", ident + "-redis", ident + "-cache", ident + "-client"]
volumes = [ident + "-db", ident + "-redis"]
with tempfile.TemporaryDirectory(prefix=ident) as tmp:
    p = pathlib.Path(tmp)
    p.chmod(0o755)
    cfg = p / "redis"
    cfg.mkdir()
    cfg.chmod(0o755)
    values = fixture()
    values.update(oldap_writer_recovery_enabled=False)
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
    for filename, template in [
        ("redis.conf", "writer-redis.conf.j2"),
        ("users.acl", "writer-users.acl.j2"),
    ]:
        (cfg / filename).write_text(render(template, values))
    (cfg / "password").write_text(values["oldap_writer_password"] + "\n")
    shutil.copyfile(
        root / "oldap-setup/scripts/writer-store.sh", cfg / "writer-store.sh"
    )
    for f in cfg.iterdir():
        f.chmod(0o644)
    for name in [
        "apply_migration.py",
        "migration_checks.py",
        "prepare_permissions.py",
        "permission-plan-2026-09-11.json",
    ]:
        shutil.copyfile(root / "FasnachtsPage/docs/production-rollout" / name, p / name)
    shutil.copyfile(
        root / "oldaplib/oldaplib/ontologies/shared.trig", p / "shared.trig"
    )
    shutil.copyfile(
        root / "auth/writer-production/archive-policy.json", p / "archive-policy.json"
    )
    shutil.copyfile(
        root / "oldap-setup/tests/archive_migration_fixture_client.py", p / "client.py"
    )
    backup = root / "BACKUP/oldap-production-pre-migration-2026-09-11_01-42-41.tar"
    shutil.copyfile(backup, p / "backup.tar")
    license = (
        pathlib.Path.home() / "Library/Application Support/GraphDB/work/graphdb.license"
    )
    try:
        command("docker", "network", "create", "--internal", ident)
        for v in volumes:
            command("docker", "volume", "create", v)
        common = ["-v", volumes[1] + ":/data", "-v", str(cfg) + ":/run/oldap-writer:ro"]
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
            "sh",
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
        command(
            "docker",
            "run",
            "-d",
            "--name",
            names[2],
            "--network",
            ident,
            "--network-alias",
            "cache",
            "redis:7-alpine",
        )
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
            "-e",
            "GDB_HEAP_SIZE=1g",
            "-v",
            volumes[0] + ":/opt/graphdb/home",
            "-v",
            str(license) + ":/opt/graphdb/home/conf/graphdb.license:ro",
            "-v",
            str(backup) + ":/restore/backup.tar:ro",
            "ontotext/graphdb:11.3.0",
        )
        command(
            "docker",
            "run",
            "-d",
            "--name",
            names[3],
            "--hostname",
            names[3],
            "-e",
            "OLDAP_MIGRATION_FIXTURE=" + ident,
            "--platform",
            "linux/amd64",
            "--network",
            ident,
            "-v",
            str(p) + ":/fixture",
            "-v",
            str(cfg) + ":/run/oldap-writer-client:ro",
            "--entrypoint",
            "python",
            "oldap-writer-operator:0.7.18-amd64",
            "/fixture/client.py",
        )
        for i in range(240):
            state = command(
                "docker", "inspect", "--format", "{{.State.Running}}", names[3]
            ).strip()
            if state == "false":
                break
            time.sleep(2)
        else:
            raise RuntimeError("Rehearsal timeout")
        print(command("docker", "logs", names[3]), flush=True)
        err = subprocess.run(
            ["docker", "logs", names[3]], capture_output=True, text=True
        ).stderr
        print(err[-7000:], flush=True)
        code = command(
            "docker", "inspect", "--format", "{{.State.ExitCode}}", names[3]
        ).strip()
        if code != "0":
            raise RuntimeError("Client failed " + code)
        report = json.loads((p / "result.json").read_text())
        (root / "BACKUP/production-migration-rehearsal.json").write_text(
            json.dumps(report, indent=2)
        )
        (root / "BACKUP/production-migration-rehearsal.json").chmod(0o600)
    finally:
        for n in reversed(names):
            subprocess.run(["docker", "rm", "-f", n], capture_output=True)
        for v in volumes:
            subprocess.run(["docker", "volume", "rm", v], capture_output=True)
        subprocess.run(["docker", "network", "rm", ident], capture_output=True)
