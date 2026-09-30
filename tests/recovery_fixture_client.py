"""Container-side isolated fixture; called only by probe_docker_recovery.py."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import requests
from redis import Redis
from oldaplib.src.mutation_gate import (
    inspect_gate,
    mutation_gate,
    mark_gate_uncertain,
    transaction_opened,
    MutationGateUnavailable,
)
from oldaplib.src.writer_recovery import WriterRecovery
from oldaplib.src.writer_recovery_operator import inventory_digest


def run():
    """Rehearse durable begin, real process fencing, evidence, finish and exact retry."""
    ident = sys.argv[1]
    assert ident.startswith("wr-docker-")
    values = json.loads(Path("/fixture/values.json").read_text())
    base = "http://graphdb:7200"

    def ready():
        for _ in range(150):
            try:
                if (
                    requests.get(base + "/rest/repositories", timeout=2).status_code
                    == 200
                ):
                    return
            except requests.RequestException:
                pass
            time.sleep(1)
        raise RuntimeError("Fixture GraphDB startup timed out")

    ready()
    with open("/fixture/repository.ttl", "rb") as f:
        r = requests.post(
            base + "/rest/repositories",
            files={"config": ("repo.ttl", f, "text/turtle")},
            timeout=30,
        )
    r.raise_for_status()
    endpoint = base + "/repositories/oldap"
    r = requests.post(
        endpoint + "/statements",
        data={
            "update": 'INSERT DATA {GRAPH <urn:test:recovery> {<urn:test:committed> <urn:test:value> "durable"}}'
        },
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(r.text[:1500])

    def url(user, password):
        return f"rediss://{user}:{password}@writer.test:6379/1?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/fixture/redis/ca.crt"

    writer = Redis.from_url(
        url("writer", values["oldap_writer_password"]), decode_responses=True
    )
    api = Redis.from_url(
        url("recovery-api", values["oldap_writer_recovery_password"]),
        decode_responses=True,
    )
    config = {
        "domain": ident,
        "nodes": [
            {
                "name": "fixture",
                "transport": "local",
                "project": ident,
                "writerServices": ["oldap-api", "oldap-tools", "oldap-harvesters"],
            }
        ],
        "databaseNode": "fixture",
        "databaseService": "graphdb",
        "queryEndpoint": endpoint,
        "operatorRedisUrl": url(
            "recovery-operator", values["oldap_writer_operator_password"]
        ),
    }
    conf = Path("/tmp/operator.json")
    conf.write_text(json.dumps(config))
    conf.chmod(0o600)
    recovery = WriterRecovery(api, ident, inventory_digest=inventory_digest(config))
    worker_count = values.get("api_workers", 0)
    if worker_count:
        from concurrent.futures import ThreadPoolExecutor

        # Seed only this newly created disposable repository for real API startup.
        for filename in ("oldap.trig", "shared.trig", "admin.trig"):
            r = requests.post(
                endpoint + "/statements",
                data=Path("/fixture", filename).read_bytes(),
                headers={"Content-Type": "application/trig"},
                timeout=60,
            )
            r.raise_for_status()
        settings = {
            "PYTHONPATH": "/fixture/api:/fixture/lib:/fixture",
            "APP_ENV": "Dev",
            "OLDAP_RECOVERY_FIXTURE": ident,
            "OLDAP_TS_SERVER": base,
            "OLDAP_TS_REPO": "oldap",
            "OLDAP_REDIS_URL": "redis://cache:6379/0",
            "OLDAP_STAGING_LOCK_REDIS_URL": url(
                "writer", values["oldap_writer_password"]
            ),
            "OLDAP_ACCESS_JWT_SECRET": uuid4().hex + uuid4().hex,
            "OLDAP_REFRESH_JWT_SECRET": uuid4().hex + uuid4().hex,
            "UPLOAD_FOLDER": "/tmp/uploads",
            "TMP_FOLDER": "/tmp/oldap-tmp",
        }
        Path("/fixture/api.env").write_text(
            "".join(f"{k}={v}\n" for k, v in settings.items())
        )
        Path("/fixture/api.env").chmod(0o600)

        def docker(*args):
            """Control only the UUID-labelled fixture through the operator socket."""
            return subprocess.check_output(
                ["docker", *args], text=True, timeout=60
            ).strip()

        def start_api():
            """Start current API sources with writer credentials, never operator secrets."""
            return docker(
                "run",
                "-d",
                "--platform",
                "linux/amd64",
                "--name",
                ident + "-writer",
                "--network",
                ident,
                "--network-alias",
                "api",
                "--label",
                "com.docker.compose.project=" + ident,
                "--label",
                "com.docker.compose.service=oldap-api",
                "-v",
                values["fixture_host_path"] + "/api:/fixture/api:ro",
                "-v",
                values["fixture_host_path"] + "/lib:/fixture/lib:ro",
                "-v",
                values["fixture_host_path"]
                + "/recovery_worker_app.py:/fixture/recovery_worker_app.py:ro",
                "-v",
                values["fixture_host_path"] + "/redis/ca.crt:/fixture/redis/ca.crt:ro",
                "--env-file",
                "/fixture/api.env",
                "--workdir",
                "/fixture/api",
                "--entrypoint",
                "python",
                values["operator_image"],
                "-m",
                "gunicorn",
                "recovery_worker_app:app",
                "--chdir",
                "/fixture/api",
                "--bind",
                "0.0.0.0:8000",
                "--workers",
                str(worker_count),
                "--threads",
                "2",
                "--timeout",
                "60",
                "--access-logfile",
                "-",
            )

        def api_ready():
            """Wait for real anonymous authentication and return an in-memory token."""
            for _ in range(90):
                try:
                    r = requests.post(
                        "http://api:8000/admin/auth/unknown", json={}, timeout=3
                    )
                    if r.ok:
                        return r.json()["accessToken"]
                except requests.RequestException:
                    pass
                time.sleep(1)
            raise RuntimeError("Fixture API did not become ready")

        def children():
            """Read namespace-local worker PIDs under the Gunicorn PID-1 master."""
            return set(
                map(
                    int,
                    docker(
                        "exec", ident + "-writer", "cat", "/proc/1/task/1/children"
                    ).split(),
                )
            )

        def all_worker_admissions(token, expected):
            """Require observed gate behavior from every worker, retrying contention."""
            observed = set()

            def probe(_):
                response = requests.post(
                    "http://api:8000/__fixture__/probe",
                    timeout=15,
                    headers={"Authorization": "Bearer " + token, "Connection": "close"},
                )
                # A healthy gate serializes writers too. Retry ordinary
                # contention; every worker must eventually be admitted.
                if expected and response.status_code == 503:
                    assert response.json()["admitted"] is False
                    return None
                assert response.status_code == (
                    200 if expected else 503
                ), response.status_code
                body = response.json()
                assert body["admitted"] is expected
                return body["pid"]

            with ThreadPoolExecutor(max_workers=16) as pool:
                for _ in range(20):
                    observed.update(pool.map(probe, range(16)))
                    observed.discard(None)
                    if len(observed) == worker_count:
                        return observed
            raise AssertionError("Not every worker was observed")

        original_container = start_api()
        token = api_ready()
        old_workers = children()
        assert len(old_workers) == worker_count
        try:
            requests.post(
                "http://api:8000/__fixture__/crash",
                timeout=30,
                headers={"Authorization": "Bearer " + token},
            )
        except requests.RequestException:
            pass
        gate = inspect_gate(writer)
        assert gate and len(gate["transactions"]) == 1
        tx = gate["transactions"][0]
        crashed_pid = gate["pid"]
        assert crashed_pid in old_workers
        for _ in range(60):
            replacement_workers = children()
            if (
                len(replacement_workers) == worker_count
                and crashed_pid not in replacement_workers
            ):
                break
            time.sleep(0.2)
        else:
            raise AssertionError("Gunicorn did not replace the crashed worker")
        assert replacement_workers - old_workers
        all_worker_admissions(token, False)
    else:
        with mutation_gate(client=writer):
            opened = requests.post(endpoint + "/transactions", timeout=10)
            opened.raise_for_status()
            tx = opened.headers["Location"]
            transaction_opened(tx)
            added = requests.put(
                tx,
                params={"action": "ADD"},
                data='<urn:test:uncommitted> <urn:test:value> "pending" .',
                headers={"Content-Type": "application/n-triples"},
                timeout=10,
            )
            added.raise_for_status()
            mark_gate_uncertain()
    operation_id = str(uuid4())
    op = recovery.begin(
        operation_id=operation_id,
        expected_revision=recovery.status()["revision"],
        actor="urn:test:operator",
        reason="Isolated Docker recovery rehearsal",
    )

    def blocked():
        try:
            with mutation_gate(client=writer, wait_seconds=0.1):
                pass
        except MutationGateUnavailable:
            return
        raise AssertionError("Recovery allowed a writer")

    blocked()
    if worker_count:
        all_worker_admissions(token, False)

    def operator(*args):
        r = subprocess.run(
            [
                "python",
                "-m",
                "oldaplib.src.writer_recovery_operator",
                "--config",
                str(conf),
                "--operation",
                operation_id,
                *args,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if r.returncode:
            raise RuntimeError("Operator failed: " + r.stderr[-1500:])
        return json.loads(r.stdout)

    runtime = operator()
    ready()
    blocked()
    assert runtime["startedAt"] != runtime["previousStartedAt"]
    assert any(row["containers"] for row in runtime["removedWriters"])
    if worker_count:
        assert original_container in next(
            row["containers"]
            for row in runtime["removedWriters"]
            if row["service"] == "oldap-api"
        )
        assert (
            subprocess.run(
                ["docker", "inspect", original_container], capture_output=True
            ).returncode
            != 0
        )
        fresh_container = start_api()
        assert fresh_container != original_container
        token = api_ready()
        all_worker_admissions(token, False)
    query = 'ASK {GRAPH <urn:test:recovery> {<urn:test:committed> <urn:test:value> "durable"}}'
    expected = requests.post(
        endpoint,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30,
    ).json()
    assert expected["boolean"] is True
    absent_query = 'ASK {<urn:test:uncommitted> <urn:test:value> "pending"}'
    absent = requests.post(
        endpoint,
        data={"query": absent_query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30,
    ).json()
    assert absent["boolean"] is False
    report = {
        "revision": op["request"]["revision"],
        "operator": "fixture",
        "checks": [
            {"label": "committed-marker", "query": query, "expected": expected},
            {"label": "pending-absent", "query": absent_query, "expected": absent},
        ],
        "transactions": {
            tx: {
                "outcome": "rolled_back",
                "explanation": "The recorded transaction was left uncommitted before the verified database restart; its unique inserted marker is absent.",
                "checks": ["pending-absent"],
            }
        },
        "unregisteredRequests": {
            "outcome": "no_write",
            "explanation": "All fixture mutation requests were issued in the single journaled transaction; no additional requests were issued. The earlier committed marker is preserved after restart.",
            "checks": ["committed-marker"],
        },
    }
    report_path = Path("/tmp/report.json")
    report_path.write_text(json.dumps(report))
    report_path.chmod(0o600)
    evidence = operator("--report", str(report_path))
    assert evidence == operator("--report", str(report_path))
    result = recovery.finish(operation_id=operation_id, actor="urn:test:operator")
    assert result["state"] == "completed" and result == recovery.finish(
        operation_id=operation_id, actor="urn:test:operator"
    )
    with mutation_gate(client=writer):
        pass
    if worker_count:
        all_worker_admissions(token, True)
        committed = requests.post(
            "http://api:8000/__fixture__/commit",
            timeout=20,
            headers={"Authorization": "Bearer " + token},
        )
        committed.raise_for_status()
        check = requests.post(
            endpoint,
            data={
                "query": 'ASK {<urn:test:after-recovery> <urn:test:value> "committed"}'
            },
            headers={"Accept": "application/sparql-results+json"},
            timeout=15,
        )
        assert check.json()["boolean"] is True
    print(
        json.dumps(
            {
                "apiWorkers": worker_count,
                "realAPICommitAfterRecovery": bool(worker_count),
                "realAPIWorkerCrashAndReplacement": bool(worker_count),
                "allWorkersBlockedUntilFinish": bool(worker_count),
                "freshAPIContainerBeforeFinish": bool(worker_count),
                "realGraphDBRestart": True,
                "writerContainerRemoved": True,
                "barrierEnforced": True,
                "committedDataPreserved": True,
                "uncommittedTransactionRolledBack": True,
                "operatorCLI": True,
                "exactEvidenceAndFinishRetry": True,
                "newWriterAllowedAfterFinish": True,
            }
        )
    )


if __name__ == "__main__":
    run()
