"""Fault injection on the real API app, mounted only in disposable test containers.

Never package or deploy these routes. They intentionally kill the serving worker
inside a journaled uncommitted GraphDB transaction in the isolated fixture.
"""

import os
import signal
from pathlib import Path
import oldap_api
import oldaplib

from oldap_api import create_app
from oldap_api.authentication import require_auth, authenticated_connection
from oldaplib.src.mutation_gate import mutation_gate, MutationGateUnavailable

if not os.environ.get("OLDAP_RECOVERY_FIXTURE", "").startswith("wr-docker-"):
    raise RuntimeError("Disposable recovery fixture identity required")
if os.environ.get("OLDAP_TS_SERVER") != "http://graphdb:7200":
    raise RuntimeError("Only the isolated GraphDB alias is allowed")

# Gunicorn prepends its working directory to sys.path. Refuse to accidentally
# test the older API bundled in the dependency image instead of mounted sources.
if Path(oldap_api.__file__).resolve().parent != Path("/fixture/api/oldap_api"):
    raise RuntimeError(
        f"Current mounted API source is required; got {oldap_api.__file__}"
    )
if Path(oldaplib.__file__).resolve().parent != Path("/fixture/lib/oldaplib"):
    raise RuntimeError("Current mounted library source is required")

app = create_app()
app.debug = False


@app.post("/__fixture__/crash")
@require_auth
def crash_writer():
    """Die after a real library transaction is journaled and updated, before commit."""
    with mutation_gate(wait_seconds=0):
        con = authenticated_connection()
        con.transaction_start()
        con.transaction_update(
            'INSERT DATA { <urn:test:uncommitted> <urn:test:value> "pending" }'
        )
        os.kill(os.getpid(), signal.SIGKILL)
    raise AssertionError("SIGKILL must not return")


@app.post("/__fixture__/probe")
@require_auth
def probe_writer():
    """Expose this worker's actual gate admission, without issuing RDF writes."""
    try:
        with mutation_gate(wait_seconds=0):
            return {"pid": os.getpid(), "admitted": True}
    except MutationGateUnavailable:
        return {"pid": os.getpid(), "admitted": False}, 503


@app.post("/__fixture__/commit")
@require_auth
def commit_after_recovery():
    """Prove a fresh API worker can commit a real transaction after release."""
    with mutation_gate(wait_seconds=0):
        con = authenticated_connection()
        con.transaction_start()
        con.transaction_update(
            'INSERT DATA { <urn:test:after-recovery> <urn:test:value> "committed" }'
        )
        con.transaction_commit()
    return {"committed": True}
