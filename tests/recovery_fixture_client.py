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
    print(
        json.dumps(
            {
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
