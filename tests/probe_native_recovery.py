"""Real WR-04 native/GraphDB acceptance on UUID-owned disposable services only.

Requires macOS GUI launchd, local GraphDB distribution/runtime, redis-server and
editable oldaplib. Never reads application secrets or addresses its data/services.
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import plistlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import requests
from redis import Redis
from oldaplib.src.writer_recovery import WriterRecovery
from oldaplib.src.writer_recovery_operator import inventory_digest, prepare_evidence
from oldaplib.src.writer_recovery_macos import LaunchdDomain

WORKER = """import json, pathlib, sys, time, requests
from redis import Redis
from oldaplib.src.mutation_gate import mutation_gate, transaction_opened, transaction_closed, mark_gate_uncertain
root, name, endpoint, sock = sys.argv[1:]
root = pathlib.Path(root)
client = Redis(unix_socket_path=sock, decode_responses=True)
while True:
    job = root / (name + '.job')
    if not job.exists():
        time.sleep(.05)
        continue
    task = json.loads(job.read_text())
    job.unlink()
    with mutation_gate(client=client, wait_seconds=10):
        (root / (name + '.entered')).write_text(str(time.monotonic()))
        response = requests.post(endpoint + '/transactions', timeout=10)
        response.raise_for_status()
        tx = response.headers['Location']
        if task['mode'] != 'unregistered':
            transaction_opened(tx)
        data = '<urn:wr04:' + task['id'] + '> <urn:wr04:p> "present" .'
        requests.put(tx, params={'action':'ADD'}, data=data, headers={'Content-Type':'application/n-triples'}, timeout=10).raise_for_status()
        time.sleep(task.get('hold', 0))
        mode = task['mode']
        if mode in ('commit', 'commit_lost'):
            requests.put(tx, params={'action':'COMMIT'}, timeout=10).raise_for_status()
        elif mode in ('abort', 'abort_lost'):
            requests.delete(tx, timeout=10).raise_for_status()
        if mode in ('commit', 'abort'):
            transaction_closed(tx)
        else:
            mark_gate_uncertain()
            (root / (name + '.paused')).write_text(tx)
            while True: time.sleep(1)
    (root / (name + '.done')).write_text(str(time.monotonic()))
"""


def wait(check, seconds=60):
    """Bound readiness waits; retain the underlying failure for probe diagnosis."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            result = check()
            if result:
                return result
        except (requests.RequestException, ConnectionError, ValueError):
            pass
        time.sleep(0.2)
    raise RuntimeError("Fixture did not reach the expected state")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(
    dist: Path,
    license_file: Path,
    restore: Path | None = None,
    expected_counts: Path | None = None,
):
    """Exercise actual transaction outcomes and native fencing, without injected proof."""
    if not license_file.is_file():
        raise ValueError("A local test GraphDB license is required")
    result = {"graphdb": "11.3.1", "runtime": "native macOS launchd", "checks": {}}
    services = []
    redis = None
    with tempfile.TemporaryDirectory(prefix="wr04-native-") as directory:
        root = Path(directory)
        uid = uuid4().hex
        port = free_port()
        endpoint = f"http://127.0.0.1:{port}/repositories/wr04"
        sock = str(root / "redis.sock")
        redis = subprocess.Popen(
            [
                shutil.which("redis-server"),
                "--port",
                "0",
                "--unixsocket",
                sock,
                "--dir",
                directory,
                "--appendonly",
                "yes",
                "--appendfsync",
                "always",
                "--save",
                "",
                "--maxmemory-policy",
                "noeviction",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        client = Redis(unix_socket_path=sock, decode_responses=True)
        for _ in range(100):
            try:
                if client.ping():
                    break
            except Exception:
                time.sleep(0.1)
        worker = root / "worker.py"
        worker.write_text(WORKER)
        java = dist.parent / "runtime/Contents/Home/bin/java"
        home = root / "graphdb"
        home.mkdir()
        (home / "conf").mkdir()
        shutil.copy2(license_file, home / "conf/graphdb.license")

        def add_service(name, args):
            label = f"org.oldap.wr04-{uid}-{name}"
            path = root / (label + ".plist")
            path.write_bytes(
                plistlib.dumps(
                    {
                        "Label": label,
                        "ProgramArguments": args,
                        "RunAtLoad": True,
                        "KeepAlive": True,
                        "AbandonProcessGroup": False,
                        "ExitTimeOut": 10,
                        "StandardOutPath": str(root / (name + ".log")),
                        "StandardErrorPath": str(root / (name + ".log")),
                    }
                )
            )
            path.chmod(0o600)
            item = {
                "label": label,
                "plist": str(path),
                "sha256": sha256(path.read_bytes()).hexdigest(),
            }
            services.append(item)
            LaunchdDomain.run("bootstrap", f"gui/{os.getuid()}", str(path))

        try:
            add_service(
                "database",
                [
                    str(java),
                    "-Xms128m",
                    "-Xmx1g",
                    "-Djava.awt.headless=true",
                    f"-Dgraphdb.dist={dist}",
                    f"-Dgraphdb.home={home}",
                    f"-Dgraphdb.connector.port={port}",
                    "-cp",
                    str(dist / "lib/*"),
                    "com.ontotext.graphdb.server.GraphDBWorkbench",
                ],
            )
            wait(
                lambda: requests.get(
                    f"http://127.0.0.1:{port}/rest/repositories", timeout=2
                ).status_code
                == 200
            )
            ttl = (
                (Path(__file__).parents[1] / "files/oldap-config.ttl")
                .read_text()
                .replace('rep:repositoryID "oldap"', 'rep:repositoryID "wr04"')
                .replace('"10000000"', '"100000"')
            )
            requests.post(
                f"http://127.0.0.1:{port}/rest/repositories",
                files={"config": ("config.ttl", ttl)},
                timeout=30,
            ).raise_for_status()
            for name in ("one", "two"):
                add_service(
                    name, [sys.executable, str(worker), directory, name, endpoint, sock]
                )
            config = {
                "domain": "fixture-" + uid,
                "runtime": "macos-launchd-v1",
                "nativeServices": services,
                "databaseService": services[0]["label"],
                "queryEndpoint": endpoint,
            }
            recovery = WriterRecovery(
                client, config["domain"], inventory_digest=inventory_digest(config)
            )

            def task(name, mode, hold=0):
                for suffix in ("entered", "done", "paused"):
                    (root / (name + "." + suffix)).unlink(missing_ok=True)
                ident = uuid4().hex
                (root / (name + ".job")).write_text(
                    json.dumps({"id": ident, "mode": mode, "hold": hold})
                )
                return ident

            def ask(ident):
                query = f'ASK {{ <urn:wr04:{ident}> <urn:wr04:p> "present" }}'
                response = requests.post(
                    endpoint,
                    data={"query": query},
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=5,
                )
                response.raise_for_status()
                return query, response.json()

            first = task("one", "commit", 2)
            wait(lambda: (root / "one.entered").exists())
            result["checks"]["reader_available_during_writer"] = (
                ask(first)[1]["boolean"] is False
            )
            second = task("two", "commit")
            wait(lambda: (root / "one.done").exists() and (root / "two.done").exists())
            result["checks"]["independent_writers_serialize"] = (
                float((root / "two.entered").read_text())
                >= float((root / "one.entered").read_text()) + 1.8
            )
            result["checks"]["confirmed_commit_releases"] = (
                recovery.status()["state"] == "free"
                and ask(first)[1]["boolean"]
                and ask(second)[1]["boolean"]
            )
            aborted = task("one", "abort")
            wait(lambda: (root / "one.done").exists())
            result["checks"]["confirmed_abort_releases"] = (
                recovery.status()["state"] == "free" and not ask(aborted)[1]["boolean"]
            )
            for mode, expected in [
                ("unregistered", False),
                ("commit_lost", True),
                ("abort_lost", False),
                ("crash", False),
            ]:
                ident = task("one", mode)
                wait(lambda: (root / "one.paused").exists())
                if mode == "crash":
                    native = LaunchdDomain(config)
                    service = services[1]
                    before_crash = native.identity(service)
                    native.run(
                        "kill", "SIGKILL", f'gui/{os.getuid()}/{service["label"]}'
                    )
                    wait(lambda: native.identity(service) != before_crash)
                    result["checks"]["crashed_writer_owner_retained"] = (
                        recovery.status()["state"] != "free"
                    )
                opid = str(uuid4())
                operation = recovery.begin(
                    operation_id=opid,
                    expected_revision=recovery.status()["revision"],
                    actor="urn:fixture:operator",
                    reason="Reconcile isolated native runtime fault",
                )
                prepare_evidence(client, config, opid)
                wait(lambda: ask(ident)[1]["boolean"] is expected)
                query, observed = ask(ident)
                conclusion = {
                    "outcome": "committed" if expected else "rolled_back",
                    "explanation": "The isolated unique probe triple was checked after all old processes exited.",
                    "checks": ["triple"],
                }
                report = {
                    "revision": operation["request"]["revision"],
                    "operator": "fixture",
                    "checks": [
                        {"label": "triple", "query": query, "expected": observed}
                    ],
                    "transactions": {
                        url: conclusion for url in operation["owner"]["transactions"]
                    },
                    "unregisteredRequests": conclusion,
                }
                prepare_evidence(client, config, opid, report=report)
                recovery.finish(operation_id=opid, actor="urn:fixture:operator")
                recovery.finish(operation_id=opid, actor="urn:fixture:operator")
                result["checks"][mode + "_fenced_reconciled_released"] = (
                    recovery.status()["state"] == "free"
                )
                successor = task("two", "commit")
                wait(lambda: (root / "two.done").exists())
                assert ask(successor)[1]["boolean"]
            if restore:
                assert expected_counts
                response = requests.post(
                    f"http://127.0.0.1:{port}/rest/repositories",
                    files={
                        "config": (
                            "restore.ttl",
                            ttl.replace('"wr04"', '"wr04-restore"'),
                        )
                    },
                    timeout=30,
                )
                response.raise_for_status()
                restored = f"http://127.0.0.1:{port}/repositories/wr04-restore"
                response = requests.post(
                    restored + "/statements",
                    data=restore.read_bytes(),
                    headers={"Content-Type": "application/trig"},
                    timeout=60,
                )
                response.raise_for_status()
                response = requests.post(
                    restored,
                    data={
                        "query": "SELECT ?g (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g",
                        "infer": "false",
                    },
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=30,
                )
                response.raise_for_status()
                restored_counts = {
                    row["g"]["value"]: int(row["n"]["value"])
                    for row in response.json()["results"]["bindings"]
                }
                live_counts = json.loads(expected_counts.read_text())[
                    "afterGraphCounts"
                ]
                nonadmin = lambda counts: {
                    key: value
                    for key, value in counts.items()
                    if key != "http://oldap.org/base#admin"
                }
                result["checks"]["local_backup_restore_nonadmin_counts_match_live"] = (
                    nonadmin(restored_counts) == nonadmin(live_counts)
                )
            assert all(result["checks"].values()), result
        except Exception:
            for file in root.rglob("*.log"):
                print(
                    file.name,
                    "\n".join(
                        line
                        for line in file.read_text().splitlines()
                        if not line.startswith("\t")
                    )[-4500:],
                    file=sys.stderr,
                )
            raise
        finally:
            for item in services:
                subprocess.run(
                    ["/bin/launchctl", "bootout", f'gui/{os.getuid()}/{item["label"]}'],
                    capture_output=True,
                )
            if redis:
                redis.terminate()
                redis.wait(timeout=10)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graphdb-dist", type=Path, required=True)
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--expected-counts", type=Path)
    parser.add_argument("--license", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.graphdb_dist, args.license, args.restore, args.expected_counts)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
