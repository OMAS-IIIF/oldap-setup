#!/usr/bin/env python3
"""Exercise real HTTP writes only in the isolated home restore API container.

Run phases in order using RESTORE_WRITE_PHASE. State/credentials stay in a private
container-local file. Output contains checks and fixture identifiers, never tokens.
The fixtures intentionally remain in the disposable clone for inspection.
"""

import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import struct
import time
from urllib.parse import quote, urlsplit
from uuid import uuid4
import zipfile
import zlib

import requests

API = "http://127.0.0.1:8000"
MEDIA = "http://oldap-mediahelper:8000"
STATE = Path("/tmp/oldap-restore-write-state.json")


def png():
    """Build a small valid RGB image without extra fixture dependencies."""

    def chunk(kind, data):
        return (
            struct.pack("!I", len(data))
            + kind
            + data
            + struct.pack("!I", zlib.crc32(kind + data))
        )

    pixels = b"".join(
        b"\x00" + bytes((x + y) % 256 for x in range(384)) for y in range(128)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", 128, 128, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


def run():
    """Run one checkpointed phase; fail immediately on unexpected HTTP results."""
    if os.getenv("OLDAP_MEDIA_INTERNAL_URL") != MEDIA:
        raise RuntimeError("This probe requires the isolated restore configuration")
    os.umask(0o077)
    state = (
        json.loads(STATE.read_text())
        if STATE.exists()
        else {"checks": [], "id": uuid4().hex[:12]}
    )
    session = requests.Session()

    def save():
        STATE.write_text(json.dumps(state, indent=2))

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        state["checks"].append(label)
        save()
        print(label, flush=True)

    def call(method, path, body=None, *, token=None, expected=(200,), **kwargs):
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = "Bearer " + token
        url = path if path.startswith("http:") else API + path
        # Never follow a live URL returned by restored configuration.
        if urlsplit(url).netloc not in (
            "127.0.0.1:8000",
            "oldap-mediahelper:8000",
            "restore-export-proxy:8080",
            "oldap-imageserver:8182",
        ):
            raise ValueError("Non-isolated request target")
        try:
            response = session.request(
                method, url, json=body, headers=headers, timeout=120, **kwargs
            )
        except requests.RequestException as error:
            # Requests exceptions include capability tokens in their URL.
            raise RuntimeError(
                f"{method} {urlsplit(url).path}: {type(error).__name__}"
            ) from None
        if response.status_code not in expected:
            # Server diagnostics may contain data, so retain privately, not stdout.
            Path("/tmp/oldap-restore-write-error.txt").write_text(response.text)
            raise RuntimeError(
                f"{method} {urlsplit(url).path}: HTTP {response.status_code}, expected {expected}"
            )
        return response

    def login(user, password):
        return call(
            "POST", "/admin/auth/" + quote(user, safe=""), {"password": password}
        ).json()["accessToken"]

    admin = login(
        os.environ["OLDAP_AUTH_ADMIN_USER"], os.environ["OLDAP_AUTH_ADMIN_PASSWORD"]
    )
    public = call("POST", "/admin/auth/unknown", {}).json()["accessToken"]
    phase = os.environ["RESTORE_WRITE_PHASE"]
    if phase not in {
        "fixture",
        "zip",
        "validate",
        "confirm",
        "imported",
        "inventory",
        "export",
        "exported",
        "publication",
        "permissions",
        "final",
    }:
        raise ValueError("Unknown restore write phase")
    if phase == "fixture":
        if "actor" in state:
            raise RuntimeError("Fixture already exists; continue with next phase")
        from oldap_api.backend import create_connection
        from oldaplib.src.project import Project

        con = create_connection(
            userId=os.environ["OLDAP_AUTH_ADMIN_USER"],
            credentials=os.environ["OLDAP_AUTH_ADMIN_PASSWORD"],
        )
        project_iri = str(Project.read(con, "fasnacht").projectIri)
        actor = "restoreWriter" + state["id"]
        password = secrets.token_urlsafe(32)
        call(
            "PUT",
            "/admin/user/" + actor,
            {
                "givenName": "Restore",
                "familyName": "Acceptance",
                "email": actor + "@example.invalid",
                "password": password,
                "isActive": True,
                "inProjects": [
                    {"project": project_iri, "permissions": ["ADMIN_CREATE"]}
                ],
                "hasRole": {
                    "fasnacht:ArchiveMediaEditor": "DATA_UPDATE",
                    "fasnacht:BMG-Archivist": "DATA_UPDATE",
                },
            },
            token=admin,
        )
        state.update(actor=actor, password=password)
        save()
        writer = login(actor, password)
        caps = call(
            "GET", "/archive/fasnacht/publication/capabilities", token=writer
        ).json()
        check("Non-administrator editor can publish", caps["canPublish"])
        area = "urn:uuid:e1c03947-4f53-465f-85c5-0296e12bd0cc"
        rows = call(
            "POST",
            "/data/search/fasnacht/class/shared:StagingFolder",
            {
                "includeProperties": ["schema:name", "shared:inStagingArea"],
                "filter": [
                    {
                        "property": "schema:name",
                        "op": "==",
                        "value": "top",
                        "type": "string",
                    }
                ],
                "limit": 100,
            },
            token=admin,
        ).json()
        top = next(r["iri"] for r in rows if area in r.get("shared:inStagingArea", []))
        grants = {
            "fasnacht:ArchiveMediaEditor": "DATA_UPDATE",
            "fasnacht:BMG-Archivist": "DATA_UPDATE",
        }
        folder = call(
            "PUT",
            "/data/fasnacht/shared:StagingFolder",
            {
                "schema:name": "Restore acceptance " + state["id"],
                "shared:inStagingArea": area,
                "shared:inStagingFolder": top,
                "oldap:attachedToRole": grants,
            },
            token=writer,
        ).json()["iri"]
        state.update(area=area, folder=folder)
        save()
        check("Editor creates dedicated staging folder", True)
        call(
            "POST",
            "/data/fasnacht/" + quote(folder, safe=""),
            {"schema:name": "Restore edited " + state["id"]},
            token=writer,
        )
        edited = call(
            "GET", "/data/fasnacht/" + quote(folder, safe=""), token=writer
        ).json()
        check(
            "Editor update persists",
            "Restore edited " + state["id"] in json.dumps(edited),
        )
        call(
            "POST",
            "/data/fasnacht/" + quote(folder, safe=""),
            {"schema:name": "Forbidden change"},
            token=public,
            expected=(403, 404),
        )
        check("Public actor cannot edit private folder", True)
        image = png()
        form = {
            "projectId": "fasnacht",
            "resourceClass": "shared:StagingMediaObject",
            "stagingAreaIri": area,
            "stagingFolderIri": folder,
        }
        uploaded = call(
            "POST",
            MEDIA + "/upload",
            token=writer,
            data=form,
            files={"file": ("restore.png", image, "image/png")},
        ).json()
        state["single"] = uploaded
        save()
        check(
            "Single image upload stores original checksum",
            uploaded["checksum"] == hashlib.sha256(image).hexdigest(),
        )
        call(
            "POST",
            MEDIA + "/upload",
            token=public,
            data=form,
            files={"file": ("denied.png", image, "image/png")},
            expected=(403,),
        )
        check("Public actor cannot upload", True)
    else:
        writer = login(state["actor"], state["password"])
    if phase == "zip":
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("restore-zip.png", png())
            archive.writestr(
                "restore-notes.txt", "Restore test: Zürich, Straße, école.\n".encode()
            )
        payload = output.getvalue()
        if "import_id" in state:
            job = call("GET", "/imports/" + state["import_id"], token=writer).json()
            upload = call(
                "POST",
                "/imports/" + state["import_id"] + "/upload-capability",
                {"expectedStateVersion": job["stateVersion"]},
                token=writer,
            ).json()
        else:
            created = call(
                "POST",
                "/imports",
                {
                    "projectShortName": "fasnacht",
                    "stagingAreaIri": state["area"],
                    "targetRootFolderIri": state["folder"],
                    "originalFileName": "restore.zip",
                    "compressedSizeBytes": len(payload),
                },
                token=writer,
                expected=(201,),
            ).json()
            state["import_id"] = created["job"]["importId"]
            save()
            upload = created["upload"]
        # Capability details remain private; only its schema keys are diagnostic.
        state["upload_keys"] = list(upload)
        save()
        url = upload.get("url") or upload.get("uploadUrl")
        url = (
            MEDIA
            + urlsplit(url).path
            + ("?" + urlsplit(url).query if urlsplit(url).query else "")
        )
        headers = upload.get("headers", {})
        headers.update(
            {
                "Authorization": "Bearer " + upload["bearerToken"],
                "Content-Type": "application/zip",
                "X-Upload-Request-Id": str(uuid4()),
            }
        )
        call("PUT", url, data=payload, headers=headers, expected=(200, 201))
        check("ZIP stored through upload capability", True)
    if phase in ("validate", "imported"):
        wanted = "READY" if phase == "validate" else "IMPORTED"
        deadline = time.monotonic() + 180
        while True:
            job = call("GET", "/imports/" + state["import_id"], token=writer).json()
            if job["state"] == wanted:
                break
            if (
                job["state"] in ("INVALID", "FAILED", "CANCELLED")
                or time.monotonic() > deadline
            ):
                Path("/tmp/oldap-restore-write-error.txt").write_text(json.dumps(job))
                raise RuntimeError(
                    "Import did not reach " + wanted + ": " + job["state"]
                )
            time.sleep(1)
        state["import_job"] = job
        save()
        check("ZIP worker reaches " + wanted, True)
    if phase == "confirm":
        result = call(
            "POST",
            "/imports/" + state["import_id"] + "/confirm",
            {"expectedStateVersion": state["import_job"]["stateVersion"]},
            token=writer,
            expected=(202,),
        ).json()
        check("ZIP confirmation accepted", result["state"] == "IMPORTING")
    if phase == "inventory":
        rows = call(
            "POST",
            "/data/search/fasnacht/class/shared:StagingMediaObject",
            {
                "includeProperties": ["shared:originalName", "shared:assetId"],
                "filter": [
                    {
                        "property": "shared:inStagingFolder",
                        "op": "==",
                        "value": state["folder"],
                        "type": "iri",
                    }
                ],
                "limit": 100,
            },
            token=writer,
        ).json()
        imported = [
            r
            for r in rows
            if any(
                n in ("restore-zip.png", "restore-notes.txt")
                for n in r.get("shared:originalName", [])
            )
        ]
        check(
            "Exactly two ZIP resources after worker restart",
            len(imported) == 2 and len({r["iri"] for r in imported}) == 2,
        )
        state["imported_iris"] = sorted(r["iri"] for r in imported)
        save()
        job = call("GET", "/imports/" + state["import_id"], token=writer).json()
        call(
            "POST",
            "/imports/" + state["import_id"] + "/confirm",
            {"expectedStateVersion": job["stateVersion"]},
            token=writer,
            expected=(409,),
        )
        check("Completed import rejects another confirmation", True)
    if phase == "export":
        result = call(
            "POST",
            "/exports",
            {
                "projectShortName": "fasnacht",
                "kind": "STAGING_FOLDER",
                "selectionIri": state["folder"],
            },
            token=writer,
            expected=(202,),
        ).json()
        state["export_id"] = result["exportId"]
        save()
        check("Staging export queued", True)
    if phase == "exported":
        deadline = time.monotonic() + 180
        while True:
            job = call("GET", "/exports/" + state["export_id"], token=writer).json()
            if job["state"] == "READY":
                break
            if job["state"] == "FAILED" or time.monotonic() > deadline:
                Path("/tmp/oldap-restore-write-error.txt").write_text(json.dumps(job))
                raise RuntimeError("Export did not reach READY: " + job["state"])
            time.sleep(1)
        download = call(
            "POST",
            "/exports/" + state["export_id"] + "/download-capability",
            {},
            token=writer,
        ).json()
        state["download_keys"] = list(download)
        save()
        url = download.get("url") or download.get("downloadUrl")
        parsed = urlsplit(url)
        url = (
            "http://restore-export-proxy:8080"
            + parsed.path
            + ("?" + parsed.query if parsed.query else "")
        )
        response = call("GET", url, headers=download.get("headers", {}))
        bare_url = url.split("?", 1)[0]
        call(
            "GET",
            bare_url,
            expected=(401,),
            headers={"X-Oldap-Internal-Path": "/etc/passwd"},
        )
        check("Export rejects absent capability and spoofed internal path", True)
        partial = call("GET", url, headers={"Range": "bytes=0-15"}, expected=(206,))
        check(
            "Export range download matches complete ZIP",
            partial.content == response.content[:16],
        )
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            check("Export ZIP CRC checks pass", archive.testzip() is None)
            hashes = [
                hashlib.sha256(archive.read(n)).hexdigest()
                for n in archive.namelist()
                if not n.endswith("/")
            ]
            check(
                "Export contains uploaded image bytes",
                hashlib.sha256(png()).hexdigest() in hashes,
            )
            check(
                "Export contains UTF-8 ZIP text bytes",
                hashlib.sha256(
                    "Restore test: Zürich, Straße, école.\n".encode()
                ).hexdigest()
                in hashes,
            )
            state["export_entries"] = len(archive.namelist())
            save()
        call("GET", "/exports/" + state["export_id"], token=public, expected=(403, 404))
        check("Public actor cannot access private export", True)
    if phase == "publication":
        grants = {
            "fasnacht:ArchiveMediaEditor": "DATA_UPDATE",
            "fasnacht:BMG-Archivist": "DATA_UPDATE",
        }
        root = call(
            "PUT",
            "/data/fasnacht/fasnacht:ArchiveObject",
            {
                "schema:name": ["Restore publication " + state["id"] + "@en"],
                "dcterms:type": "http://fasnacht.digital/ns/ObjectTaxonomy#Kunst",
                "fasnacht:publicationStatus": "http://fasnacht.digital/ns/PublicationStatus#InProgress",
                "oldap:attachedToRole": grants,
            },
            token=writer,
        ).json()["iri"]
        state["publication_root"] = root
        save()
        media_iri = state["single"]["iri"]
        call(
            "POST",
            "/data/fasnacht/" + quote(media_iri, safe="") + "/transform",
            {
                "targetClass": "fasnacht:ArchiveMediaObject",
                "preserveClass": "shared:MediaObject",
                "expectedSourceClass": "shared:StagingMediaObject",
                "properties": {
                    "schema:name": ["Restore archive image " + state["id"] + "@en"],
                    "fasnacht:contributingAgent": "fasnacht:EuropeanaProvider",
                    "dcterms:rights": "http://fasnacht.digital/ns/CreativeCommons#CC_BY-SA",
                    "fasnacht:publicationStatus": "http://fasnacht.digital/ns/PublicationStatus#InProgress",
                    "fasnacht:archiveMediaObjectOf": root,
                },
            },
            token=writer,
        )
        check("Editor transforms uploaded staging image into archive medium", True)
        request = {"resourceIri": root, "permission": "DATA_VIEW"}
        call(
            "POST",
            "/archive/fasnacht/publication/preview",
            request,
            token=public,
            expected=(403, 404),
        )
        call(
            "GET",
            "/data/fasnacht/" + quote(media_iri, safe=""),
            token=public,
            expected=(403, 404),
        )
        check("Public actor cannot publish or read private draft", True)
        review = call(
            "POST", "/archive/fasnacht/publication/preview", request, token=writer
        ).json()
        check(
            "Publication review covers root and linked uploaded medium",
            len(review["resources"]) == 2,
        )
        operation = str(uuid4())
        state["publication_operation"] = operation
        save()
        applied = {**request, "revision": review["revision"]}
        result = call(
            "POST",
            "/archive/fasnacht/publication/apply",
            applied,
            token=writer,
            headers={"Idempotency-Key": operation},
        ).json()
        replay = call(
            "POST",
            "/archive/fasnacht/publication/apply",
            applied,
            token=writer,
            headers={"Idempotency-Key": operation},
        ).json()
        check("Publication retry returns identical receipt", result == replay)
        receipt = call(
            "GET", "/archive/fasnacht/publication/operations/" + operation, token=writer
        ).json()
        state["publication_receipt_keys"] = list(receipt)
        save()
        for iri in (root, media_iri):
            resource = call(
                "GET", "/data/fasnacht/" + quote(iri, safe=""), token=public
            ).json()
            check(
                "Published resource is readable with published status",
                "Published" in json.dumps(resource),
            )
        state["publication_result"] = result
        save()
    if phase == "permissions":
        from oldap_api.backend import create_connection
        from oldaplib.src.project import Project

        con = create_connection(
            userId=os.environ["OLDAP_AUTH_ADMIN_USER"],
            credentials=os.environ["OLDAP_AUTH_ADMIN_PASSWORD"],
        )
        viewer_name = "restoreViewer" + state["id"]
        viewer_password = secrets.token_urlsafe(32)
        reader_role = "fasnacht:RestoreReader" + state["id"]
        call(
            "PUT",
            "/admin/role/fasnacht/RestoreReader" + state["id"],
            {"label": ["Restore acceptance reader@en"]},
            token=admin,
            expected=(200, 409),
        )
        # User hasRole annotations are defaults for new resources, not a ceiling
        # on existing grants. Use a separate reader role and explicit resource ACL.
        payload = {
            "givenName": "Restore",
            "familyName": "Viewer",
            "email": viewer_name + "@example.invalid",
            "password": viewer_password,
            "isActive": True,
            "inProjects": [
                {
                    "project": str(Project.read(con, "fasnacht").projectIri),
                    "permissions": [],
                }
            ],
            "hasRole": {reader_role: "DATA_VIEW"},
        }
        created = call(
            "PUT",
            "/admin/user/" + viewer_name,
            payload,
            token=admin,
            expected=(200, 409),
        )
        if created.status_code == 409:
            call(
                "POST",
                "/admin/user/" + viewer_name,
                {"password": viewer_password, "hasRole": {reader_role: "DATA_VIEW"}},
                token=admin,
            )
        call(
            "POST",
            "/data/fasnacht/" + quote(state["folder"], safe=""),
            {
                "schema:name": "Restore edited " + state["id"],
                "oldap:attachedToRole": {"add": {reader_role: "DATA_VIEW"}},
            },
            token=admin,
        )
        viewer = login(viewer_name, viewer_password)
        call("GET", "/data/fasnacht/" + quote(state["folder"], safe=""), token=viewer)
        check("Reader role can read the private test folder", True)
        call(
            "POST",
            "/data/fasnacht/" + quote(state["folder"], safe=""),
            {"schema:name": "Forbidden viewer edit"},
            token=viewer,
            expected=(403, 404),
        )
        unchanged = call(
            "GET", "/data/fasnacht/" + quote(state["folder"], safe=""), token=admin
        ).json()
        check(
            "Reader resource grant cannot update",
            "Forbidden viewer edit" not in json.dumps(unchanged),
        )
        call(
            "POST",
            "/archive/fasnacht/publication/preview",
            {"resourceIri": state["publication_root"], "permission": "DATA_VIEW"},
            token=viewer,
            expected=(403, 404),
        )
        check("Reader role cannot publish", True)
    if phase == "final":
        rows = call(
            "POST",
            "/data/search/fasnacht/class/shared:StagingMediaObject",
            {
                "includeProperties": ["shared:originalName"],
                "filter": [
                    {
                        "property": "shared:inStagingFolder",
                        "op": "==",
                        "value": state["folder"],
                        "type": "iri",
                    }
                ],
                "limit": 100,
            },
            token=writer,
        ).json()
        current = sorted(
            r["iri"]
            for r in rows
            if any(
                n in ("restore-zip.png", "restore-notes.txt")
                for n in r.get("shared:originalName", [])
            )
        )
        check(
            "Imported resource identities remain unchanged after further worker polls",
            current == state["imported_iris"],
        )
        receipt = call(
            "GET",
            "/archive/fasnacht/publication/operations/"
            + state["publication_operation"],
            token=writer,
        ).json()
        check(
            "Publication receipt remains unchanged after worker restart",
            receipt == state["publication_result"],
        )
        media_token = call(
            "GET",
            "/data/mediaobject/iri/" + quote(state["single"]["iri"], safe=""),
            token=public,
        ).json()["token"]
        image_url = "http://oldap-imageserver:8182/iiif/3/" + state["single"]["assetId"]
        info = call("GET", image_url + "/info.json?token=" + media_token).json()
        check(
            "Newly published upload is available through signed IIIF",
            info["width"] == 128 and info["height"] == 128,
        )
        image = call(
            "GET", image_url + "/full/!64,64/0/default.jpg?token=" + media_token
        ).content
        check(
            "Newly published image renders as JPEG", image.startswith(b"\xff\xd8\xff")
        )
        report = {
            key: state[key]
            for key in (
                "id",
                "folder",
                "import_id",
                "export_id",
                "imported_iris",
                "publication_operation",
                "publication_result",
                "export_entries",
            )
        }
        report.update(status="passed", checks=list(dict.fromkeys(state["checks"])))
        Path("/tmp/oldap-restore-write-results.json").write_text(
            json.dumps(report, indent=2)
        )
    print(
        json.dumps(
            {
                "phase": phase,
                "checks_passed": len(state["checks"]),
                "fixture": state["id"],
            }
        )
    )


if __name__ == "__main__":
    # Phases share checkpoint state and must not overwrite one another.
    with open("/tmp/oldap-restore-write.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run()
