"""Create NEW private production credentials locally; never overwrite or deploy.

Run with an absolute output directory outside Git. Files are owner-only. Vault
input is deliberately plaintext until the operator encrypts it interactively;
no password is printed or supplied to a subprocess command line.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess


def prepare(destination: Path):
    """Generate independent ACL secrets, TLS CA/server and fixed topology evidence."""
    if not destination.is_absolute():
        raise ValueError("Use an absolute private directory outside Git")
    if any((p / ".git").exists() for p in (destination, *destination.parents)):
        raise ValueError("Private output must be outside a Git worktree")
    os.umask(0o077)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)

    def write(name, value):
        (destination / name).write_text(value)

    def openssl(*args):
        subprocess.run(
            ["openssl", *args], cwd=destination, check=True, capture_output=True
        )

    passwords = {
        name: secrets.token_hex(32) for name in ["writer", "recovery", "operator"]
    }
    write(
        "writer-secrets.yml",
        "".join(
            f'vault_oldap_writer_{"password" if name == "writer" else name + "_password"}: "{value}"\n'
            for name, value in passwords.items()
        ),
    )
    openssl(
        "req",
        "-x509",
        "-newkey",
        "rsa:3072",
        "-nodes",
        "-sha256",
        "-days",
        "3650",
        "-keyout",
        "ca.key",
        "-out",
        "ca.crt",
        "-subj",
        "/CN=OLDAP production writer CA",
        "-addext",
        "basicConstraints=critical,CA:TRUE",
        "-addext",
        "keyUsage=critical,keyCertSign,cRLSign",
    )
    openssl(
        "req",
        "-new",
        "-newkey",
        "rsa:3072",
        "-nodes",
        "-keyout",
        "server.key",
        "-out",
        "server.csr",
        "-subj",
        "/CN=archive-writer.internal",
    )
    write(
        "server.ext",
        "basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:archive-writer.internal\n",
    )
    openssl(
        "x509",
        "-req",
        "-in",
        "server.csr",
        "-CA",
        "ca.crt",
        "-CAkey",
        "ca.key",
        "-CAcreateserial",
        "-out",
        "server.crt",
        "-days",
        "365",
        "-sha256",
        "-extfile",
        "server.ext",
    )
    openssl(
        "verify",
        "-CAfile",
        "ca.crt",
        "-verify_hostname",
        "archive-writer.internal",
        "server.crt",
    )
    topology = {
        "domain": "oldap-production",
        "nodes": [
            {
                "name": "dhlab-oldap",
                "transport": "local",
                "project": "compose",
                "writerServices": ["oldap-api", "oldap-tools", "oldap-harvesters"],
            }
        ],
        "databaseNode": "dhlab-oldap",
        "databaseService": "graphdb",
        "queryEndpoint": "http://graphdb:7200/repositories/oldap",
    }
    # Must match writer_recovery.encoded; checked against the library before use.
    digest = hashlib.sha256(
        json.dumps(topology, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    config = {
        **topology,
        "operatorRedisUrl": "rediss://recovery-operator:"
        + passwords["operator"]
        + "@archive-writer.internal:6379/1?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/run/oldap-operator/ca.crt",
    }
    write("operator.json", json.dumps(config, indent=2) + "\n")
    policy = {
        "projects": {
            "fasnacht": {
                "enabled": True,
                "structureEditorRoleIris": [
                    "http://fasnacht.digital/ns/ArchiveStructureEditor"
                ],
                "archiveEditorRoleIris": [
                    "http://fasnacht.digital/ns/ArchiveMediaEditor"
                ],
                "cataloguedMediaClassIris": [
                    "http://fasnacht.digital/ns/ArchiveMediaObject"
                ],
                "preparationNotePropertyIri": "https://schema.org/comment",
                "grantEditorRolesOnCreation": True,
            }
        }
    }
    write("archive-policy.json", json.dumps(policy, indent=2) + "\n")
    write(
        "preparation.json",
        json.dumps(
            {
                "preparedAt": datetime.now(timezone.utc).isoformat(),
                "inventoryDigest": digest,
                "status": "local_preparation_only_not_deployed",
                "serverCertificateDays": 365,
            },
            indent=2,
        )
        + "\n",
    )
    print(
        "Private files created. Certificate chain/hostname verified. No deployment performed."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args().output)
