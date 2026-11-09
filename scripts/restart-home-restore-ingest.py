#!/usr/bin/env python3
"""Drain and restart only the isolated ingest worker when it claims the test job.

Start on api.home.org before confirming the fixture import. This sends SIGTERM,
waits for the normal exit (never SIGKILL), records timestamps, then restarts the
same container. It does not alter job state, lease duration or production workers.
"""

import json
import subprocess
import threading
from datetime import datetime, timezone

PROJECT = "oldap-restore-staged-03"
WORKER = PROJECT + "-oldap-ingest-worker-1"
API = PROJECT + "-oldap-api-1"


def main():
    """Observe the real claim log, request graceful shutdown, and retain evidence."""
    info = json.loads(subprocess.check_output(["docker", "inspect", WORKER]))[0]
    assert info["Config"]["Labels"]["com.docker.compose.project"] == PROJECT
    assert info["State"]["Running"]
    job = subprocess.check_output(
        [
            "docker",
            "exec",
            API,
            "python",
            "-c",
            "import json;print(json.load(open('/tmp/oldap-restore-write-state.json'))['import_id'])",
        ],
        text=True,
    ).strip()
    now = lambda: datetime.now(timezone.utc).isoformat()
    since = now()
    follower = subprocess.Popen(
        ["docker", "logs", "--follow", "--since", since, WORKER],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    report = {"project": PROJECT, "import_id": job, "observing_since": since}
    print("Waiting for the owned import claim", flush=True)
    # Bound log observation without mixing select() with Python's buffered reader.
    observation_timeout = threading.Timer(180, follower.terminate)
    observation_timeout.start()
    try:
        for line in follower.stdout:
            if "ingest_claimed importId=" + job not in line:
                continue
            observation_timeout.cancel()
            report["claim_log"] = line.strip()
            report["signal_requested_at"] = now()
            subprocess.run(
                ["docker", "kill", "--signal=TERM", WORKER],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            report["signal_returned_at"] = now()
            code = subprocess.check_output(
                ["docker", "wait", WORKER], text=True, timeout=180
            ).strip()
            report["exit_code"] = int(code)
            final = json.loads(subprocess.check_output(["docker", "inspect", WORKER]))[
                0
            ]
            report["oom_killed"] = final["State"]["OOMKilled"]
            report["finished_at"] = final["State"]["FinishedAt"]
            report["worker_logs"] = subprocess.check_output(
                ["docker", "logs", "--since", since, WORKER],
                stderr=subprocess.STDOUT,
                text=True,
            ).splitlines()
            assert code == "0" and not report["oom_killed"]
            subprocess.run(
                ["docker", "start", WORKER], check=True, stdout=subprocess.DEVNULL
            )
            report["restarted_at"] = now()
            print(json.dumps(report, indent=2), flush=True)
            return
        raise RuntimeError("Worker log ended before the expected claim")
    finally:
        observation_timeout.cancel()
        follower.terminate()
        follower.wait(timeout=5)


if __name__ == "__main__":
    main()
