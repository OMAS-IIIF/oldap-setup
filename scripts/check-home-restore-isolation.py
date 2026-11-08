#!/usr/bin/env python3
"""Audit running home restore boundaries without dumping container credentials."""

import argparse
import json
import re
from pathlib import Path
import subprocess

PROJECT = "oldap-restore-20261106"
ROOT = Path("/srv/storage/oldap-restore-rehearsal-20261106")
EXPECTED = {
    "oldap-jena",
    "oldap-api",
    "oldap-jena-identity",
    "redis",
    "oldap-mediahelper",
    "oldap-imageserver",
}


def run(root=ROOT, project=PROJECT, workers=False, backend="jena"):
    """Check actual container mounts, network isolation, limits and disabled jobs."""
    if root.parent != Path("/srv/storage") or not root.name.startswith(
        "oldap-restore-rehearsal-"
    ):
        raise ValueError("Unexpected rehearsal directory")
    if root.resolve() != root or not re.fullmatch(r"oldap-restore-[a-z0-9-]+", project):
        raise ValueError("Unexpected rehearsal root/project")
    ids = subprocess.check_output(
        [
            "docker",
            "ps",
            "-aq",
            "--filter",
            "label=com.docker.compose.project=" + project,
        ],
        text=True,
    ).split()
    containers = json.loads(subprocess.check_output(["docker", "inspect", *ids]))
    by_service = {
        c["Config"]["Labels"]["com.docker.compose.service"]: c for c in containers
    }
    source_services = (EXPECTED - {"oldap-jena", "oldap-jena-identity"}) | {"graphdb", "archive-writer"}
    expected = (source_services if backend == "graphdb" else EXPECTED) | (
        {"oldap-ingest-worker", "oldap-export-worker", "restore-export-proxy"}
        if workers
        else set()
    )
    assert set(by_service) == expected
    network = json.loads(
        subprocess.check_output(["docker", "network", "inspect", project + "_default"])
    )[0]
    assert network["Internal"] and not network["EnableIPv6"]
    assert (
        network["Options"]["com.docker.network.bridge.gateway_mode_ipv4"] == "isolated"
    )
    bridge = network["Options"].get(
        "com.docker.network.bridge.name", "br-" + network["Id"][:12]
    )
    addresses = json.loads(
        subprocess.check_output(["ip", "-j", "address", "show", "dev", bridge])
    )
    assert not any(
        a["family"] == "inet" or a.get("scope") == "global"
        for row in addresses
        for a in row.get("addr_info", [])
    )
    owner = by_service["oldap-jena"]["Id"] if backend == "jena" else None
    for name, c in by_service.items():
        assert c["State"]["Running"], name + " is not running"
        host = c["HostConfig"]
        assert host["RestartPolicy"]["Name"] == "no" and not host["Privileged"]
        assert not host["PortBindings"] and not host["PublishAllPorts"]
        assert 0 < host["Memory"] <= 2 * 1024**3
        for mount in c["Mounts"]:
            # Docker represents /tmp tmpfs separately from host bind mounts.
            if mount["Type"] == "tmpfs":
                continue
            assert mount["Type"] == "bind" and Path(
                mount["Source"]
            ).resolve().is_relative_to(root.resolve())
        if backend == "jena" and name in ("oldap-api", "oldap-jena-identity"):
            assert host["NetworkMode"] == "container:" + owner
        else:
            assert set(c["NetworkSettings"]["Networks"]) == {project + "_default"}
    env = dict(v.split("=", 1) for v in by_service["oldap-api"]["Config"]["Env"])
    assert all(
        env[k] == "console"
        for k in (
            "OLDAP_PASSWORD_RESET_EMAIL_BACKEND",
            "OLDAP_IMPORT_EMAIL_BACKEND",
            "OLDAP_EXPORT_EMAIL_BACKEND",
        )
    )
    if workers:
        for name in ("oldap-ingest-worker", "oldap-export-worker"):
            worker_env = dict(
                v.split("=", 1) for v in by_service[name]["Config"]["Env"]
            )
            assert worker_env["OLDAP_API_URL"] == "http://oldap-api:8000"
        caps = by_service["oldap-ingest-worker"]["HostConfig"]["CapAdd"]
        assert {c.removeprefix("CAP_") for c in caps} == {
            "CHOWN",
            "DAC_OVERRIDE",
            "FOWNER",
            "KILL",
            "SETGID",
            "SETUID",
        }
    helper = dict(
        v.split("=", 1) for v in by_service["oldap-mediahelper"]["Config"]["Env"]
    )
    assert helper["OLDAP_IMPORT_CALLBACK_RECONCILE_SECONDS"] == "0"
    gateways = [v["Gateway"] for v in network["IPAM"]["Config"] if v.get("Gateway")]
    targets = [("192.168.1.230", 80), ("192.168.1.223", 80), ("1.1.1.1", 443)] + [
        (g, 80) for g in gateways
    ]
    probe = (
        """import socket,json
results=[]
for host,port in """
        + repr(targets)
        + """:
 try:
  connection=socket.create_connection((host,port),timeout=1); connection.close(); reachable=True
 except OSError: reachable=False
 results.append({'host':host,'port':port,'reachable':reachable})
print(json.dumps(results))
"""
    )
    result = subprocess.run(
        ["docker", "exec", "-i", by_service["oldap-api"]["Id"], "python", "-"],
        input=probe,
        text=True,
        capture_output=True,
        check=True,
    )
    connectivity = json.loads(result.stdout)
    assert not any(item["reachable"] for item in connectivity)
    return {
        "status": "passed",
        "services": sorted(expected),
        "no_published_ports": True,
        "all_mounts_in_restore_root": True,
        "isolated_bridge_has_no_host_address": True,
        "workers_absent": not workers,
        "zip_workers_only": workers,
        "mail_and_callback_jobs_disabled": True,
        "connectivity": connectivity,
        "memory_caps_bytes": {
            name: c["HostConfig"]["Memory"] for name, c in by_service.items()
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--project", default=PROJECT)
    parser.add_argument(
        "--workers",
        action="store_true",
        help="Expect exactly the two isolated ZIP workers",
    )
    parser.add_argument("--backend", choices=["jena", "graphdb"], default="jena")
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.project, args.workers, args.backend), indent=2))
