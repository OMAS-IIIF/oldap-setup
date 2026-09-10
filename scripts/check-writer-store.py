"""Read-only preflight inside each deployed writer image before reopening writes.

The environment and mounted policy are the same as for the real service. Fail
without printing endpoints/credentials if its library, TLS or durable Redis
configuration is incompatible. No lock is acquired or cleared by this check.
"""

import json
import os
from pathlib import Path

from redis import Redis
from oldaplib.src.mutation_gate import _validate_store


def main():
    """Validate selected policy syntax and acknowledged durable primary storage."""
    try:
        policy = json.loads(Path(os.environ["OLDAP_ARCHIVE_POLICY_FILE"]).read_text())
        if not isinstance(policy, dict):
            raise ValueError("Policy must be an object")
        with Redis.from_url(
            os.environ["OLDAP_STAGING_LOCK_REDIS_URL"],
            socket_connect_timeout=5,
            socket_timeout=10,
        ) as client:
            _validate_store(client)
            if client.execute_command("WAITAOF", 1, 0, 5000)[0] != 1:
                raise ValueError("Durability acknowledgement missing")
            if client.info("persistence").get("aof_last_write_status") != "ok":
                raise ValueError("AOF write status is not healthy")
    except Exception:
        raise SystemExit(
            "Writer store preflight failed; check release, policy, TLS and persistence configuration."
        ) from None
    print("Writer store preflight passed.")


if __name__ == "__main__":
    main()
