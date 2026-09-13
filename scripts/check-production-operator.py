"""Read-only production operator installation check; never fence or release writers.

Runs inside the reviewed operator image with its root-only configuration and Docker
socket mounted. Verifies TLS/storage, the reviewed inventory and the maintenance
state. Errors deliberately omit credentials and endpoint details.
"""

import json
import sys
from urllib.parse import urlparse


def main():
    """Verify deployment prerequisites without acquiring or changing any lock."""
    from redis import Redis
    from oldaplib.src.mutation_gate import _validate_store
    from oldaplib.src.writer_recovery_operator import (
        DockerDomain,
        inventory_digest,
        protected_json,
    )

    try:
        config = protected_json("/run/oldap-operator/operator.json")
        assert config["domain"] == "oldap-production"
        assert inventory_digest(config) == sys.argv[1]
        url = urlparse(config["operatorRedisUrl"])
        assert (url.scheme, url.hostname, url.port, url.username) == (
            "rediss",
            "archive-writer.internal",
            6379,
            "recovery-operator",
        )
        with Redis.from_url(
            config["operatorRedisUrl"], socket_connect_timeout=5, socket_timeout=10
        ) as client:
            assert client.ping()
            _validate_store(client)
            assert client.info("persistence")["aof_last_write_status"] == "ok"
            assert client.get("oldap-api:staging:mutation") is None
            assert client.get("oldap-api:staging:recovery:barrier") is None
        domain = DockerDomain(config)
        for node in config["nodes"]:
            for service in node["writerServices"]:
                for container in domain.containers(node, service):
                    assert (
                        domain.run(
                            node, "inspect", "--format", "{{.State.Running}}", container
                        )
                        == "false"
                    )
        database = domain.containers(domain.database_node, config["databaseService"])
        assert len(database) == 1
        assert (
            domain.run(
                domain.database_node,
                "inspect",
                "--format",
                "{{.State.Running}}",
                database[0],
            )
            == "true"
        )
    except Exception:
        raise SystemExit(
            "Operator installation check failed; keep maintenance active. No recovery was performed."
        ) from None
    print(
        json.dumps(
            {
                "inventoryVerified": True,
                "operatorTLSAndStorageVerified": True,
                "dockerAccessVerified": True,
                "writersStopped": True,
                "graphdbRunning": True,
                "noWriterLockOrRecoveryBarrier": True,
                "recoveryExecuted": False,
            }
        )
    )


if __name__ == "__main__":
    main()
