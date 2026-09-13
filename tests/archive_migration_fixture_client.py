"""Container-only client for the isolated archive migration rehearsal.

Restores the mounted backup, replaces the fixture administrator password with a
random value, then runs migration twice using isolated cache and TLS writer Redis.
Never run directly against an existing database.
"""

import requests, time, subprocess, json, os, secrets, bcrypt
from pathlib import Path

# An explicit fixture marker prevents accidental direct execution on an API host.
import socket

fixture = os.environ.get("OLDAP_MIGRATION_FIXTURE", "")
if (
    not fixture.startswith("archive-migration-")
    or socket.gethostname() != fixture + "-client"
):
    raise RuntimeError("Run only through the isolated fixture harness")
base = "http://graphdb:7200"
for i in range(90):
    try:
        r = requests.get(base + "/rest/repositories", timeout=3)
        if r.ok:
            break
    except requests.RequestException:
        pass
    time.sleep(2)
else:
    raise RuntimeError("GraphDB unavailable")
# Backup is mounted only in the DB container; use its internal endpoint with
# streamed bytes from a shared fixture backup copied by the harness.
with open("/fixture/backup.tar", "rb") as f:
    r = requests.post(
        base + "/rest/recovery/restore",
        files=[
            ("params", (None, '{"restoreSystemData":true}', "application/json")),
            ("file", ("backup.tar", f, "application/x-tar")),
        ],
        timeout=180,
    )
if not r.ok:
    print(r.text[:1000], flush=True)
r.raise_for_status()
password = secrets.token_hex(24)
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
query = """PREFIX oldap:<http://oldap.org/base#>
DELETE {GRAPH oldap:admin {?u oldap:credentials ?old}}
INSERT {GRAPH oldap:admin {?u oldap:credentials "HASH"}}
WHERE {GRAPH oldap:admin {?u oldap:userId ?id; oldap:credentials ?old. FILTER(STR(?id)="rosenth")}}""".replace(
    "HASH", hashed
)
r = requests.post(
    base + "/repositories/oldap/statements", data={"update": query}, timeout=60
)
r.raise_for_status()
os.environ.update(
    OLDAP_TS_SERVER=base,
    OLDAP_TS_REPO="oldap",
    OLDAP_TS_USER="",
    OLDAP_TS_PASSWORD="",
    OLDAP_AUTH_ADMIN_USER="rosenth",
    OLDAP_AUTH_ADMIN_PASSWORD=password,
    OLDAP_REDIS_URL="redis://cache:6379",
    OLDAP_WRITER_DOMAIN="oldap-production",
    OLDAP_ARCHIVE_POLICY_FILE="/fixture/archive-policy.json",
    OLDAP_STAGING_LOCK_REDIS_URL="rediss://writer:"
    + "a" * 64
    + "@writer.test:6379/1?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/run/oldap-writer-client/ca.crt",
)
from apply_migration import run

print(
    "Restored production snapshot; applying migration in isolated fixture.", flush=True
)
result = run("/fixture/permission-plan-2026-09-11.json")
print(json.dumps(result), flush=True)
retry = run("/fixture/permission-plan-2026-09-11.json")
print("Exact retry passed.", flush=True)
Path("/fixture/result.json").write_text(
    json.dumps({"first": result, "retry": retry, "isolated": True})
)
