#!/usr/bin/env python3
"""Prepare an isolated HOME restore from Borg-extracted tar files, without starting it.

Run as root on api.home.org. Inputs remain unchanged. Extracted data, rewritten
Compose configuration and disposable caches stay below a new rehearsal root.
The base stack admits six services; the explicit workers phase adds only the
two ZIP workers and an internal export-only proxy. No host ports or live volumes are reused. Configuration contains secrets and is written mode 0600.
"""

import argparse
import copy
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import socket
import subprocess
import tarfile

PROJECT = "oldap-restore-20261106"
ALLOWED = {
    "api": (
        "srv/storage/oldap-jena-home-20261102",
        "srv/storage/oldap-data/oldap-api",
        "srv/storage/caddy",
        "opt/oldap/compose",
    ),
    "media": (
        "data/media",
        "data/oldap-import-records",
        "data/oldap-ingest",
        "data/oldap-mobile-uploads",
        "data/oldap-exports",
        "opt/oldap-mediaserver/compose",
    ),
}


def validate_members(members, role):
    """Fail closed on traversal, links, devices and unexpected snapshot paths."""
    for item in members:
        path = PurePosixPath(item.name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not (item.isfile() or item.isdir())
        ):
            raise ValueError("Unsafe archive member")
        if not any(
            str(path) == prefix or str(path).startswith(prefix + "/")
            for prefix in ALLOWED[role]
        ):
            raise ValueError("Unexpected archive member prefix")


def extract(root):
    """Verify both tar hashes and all headers before extracting into a new tree."""
    incoming = root / "incoming"
    manifest = json.loads((incoming / "manifest.json").read_text())
    if manifest.get("status") != "offline-compared":
        raise ValueError("Unaccepted source manifest")
    for role in ("api", "media"):
        archive = incoming / (role + ".tar")
        if archive.is_symlink() or archive.stat().st_size != manifest[role]["bytes"]:
            raise ValueError("Archive size/type mismatch")
        with archive.open("rb") as stream:
            if (
                hashlib.file_digest(stream, "sha256").hexdigest()
                != manifest[role]["sha256"]
            ):
                raise ValueError("Archive digest mismatch")
        with tarfile.open(archive) as stream:
            validate_members(stream.getmembers(), role)
    tree = root / "tree"
    tree.mkdir(mode=0o755, exist_ok=False)
    for role in ("api", "media"):
        subprocess.run(
            [
                "tar",
                "--acls",
                "--xattrs",
                "--same-owner",
                "-xpf",
                str(incoming / (role + ".tar")),
                "-C",
                str(tree),
            ],
            check=True,
        )
    (root / "extracted.json").write_text(json.dumps(manifest, indent=2) + "\n")


def read_compose(directory):
    """Resolve only archived Compose inputs; never print their credentials."""
    environment = {k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")}
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            "Archived Compose resolution failed (diagnostics suppressed)"
        )
    return json.loads(result.stdout)


def isolated_service(original, root, tree, *, allowed_root=None):
    """Keep runtime settings but replace all host/network/storage identities.

    By default binds must remain in the extracted source tree. A separately
    prepared candidate may explicitly admit its broader private rehearsal root;
    symlinks outside that selected boundary remain forbidden.
    """
    bind_root = tree if allowed_root is None else allowed_root
    if not bind_root.resolve().is_relative_to(root.resolve()):
        raise ValueError("Bind boundary must remain inside the rehearsal root")
    fields = (
        "image",
        "entrypoint",
        "command",
        "user",
        "working_dir",
        "environment",
        "healthcheck",
        "read_only",
        "tmpfs",
        "cap_drop",
        "cap_add",
        "security_opt",
    )
    service = {k: copy.deepcopy(original[k]) for k in fields if k in original}
    allowed_caps = {"CHOWN", "DAC_OVERRIDE", "FOWNER", "KILL", "SETGID", "SETUID"}
    if not set(service.get("cap_add", [])) <= allowed_caps:
        raise ValueError("Unexpected restore container capability")
    service.update(
        restart="no", networks=["default"], mem_limit="512m", memswap_limit="512m"
    )
    service["volumes"] = []
    for mount in original.get("volumes", []):
        mount = copy.deepcopy(mount)
        if mount["type"] == "bind":
            source = Path(mount["source"])
            # Relative env-file mounts can already have been resolved under tree.
            if not source.is_relative_to(bind_root):
                source = tree / str(source).lstrip("/")
            if (
                not source.resolve().is_relative_to(bind_root.resolve())
                or not source.exists()
            ):
                raise ValueError("Mount is absent from restored tree")
            mount["source"] = str(source)
            mount["bind"] = {"create_host_path": False}
        elif mount["type"] == "volume" and mount["target"] == "/var/cache/sipi":
            cache = root / "runtime/sipi-cache"
            cache.mkdir(parents=True, exist_ok=True)
            cache.chmod(0o777)
            mount = {
                "type": "bind",
                "source": str(cache),
                "target": "/var/cache/sipi",
                "bind": {"create_host_path": False},
            }
        else:
            raise ValueError("Unexpected storage dependency")
        service["volumes"].append(mount)
    return service


def compose(root, project=PROJECT):
    """Generate a private, explicit six-service stack from restored configurations."""
    tree = root / "tree"
    if not (root / "extracted.json").exists():
        raise ValueError("Extract/verification must complete first")
    api = read_compose(tree / "opt/oldap/compose")["services"]
    media = read_compose(tree / "opt/oldap-mediaserver/compose")["services"]
    services = {
        name: isolated_service(api[name], root, tree)
        for name in ("oldap-jena", "oldap-jena-identity", "oldap-api", "redis")
    }
    for old, new in [
        ("mediaserver", "oldap-mediahelper"),
        ("imageserver", "oldap-imageserver"),
    ]:
        services[new] = isolated_service(media[old], root, tree)
    backend = services["oldap-jena"]
    backend["networks"] = {"default": {"aliases": ["oldap-api"]}}
    backend.update(mem_limit="2048m", memswap_limit="2048m")
    backend["environment"].update(
        JAVA_HEAP_MB="1024", JAVA_TOOL_OPTIONS="-XX:MaxDirectMemorySize=256m"
    )
    for name in ("oldap-api", "oldap-jena-identity"):
        services[name].pop("networks")
        services[name]["network_mode"] = "service:oldap-jena"
        services[name]["depends_on"] = {"oldap-jena": {"condition": "service_started"}}
    services["oldap-jena-identity"].update(mem_limit="128m", memswap_limit="128m")
    services["redis"].update(mem_limit="256m", memswap_limit="256m")
    services["oldap-api"]["depends_on"].update(
        {
            "oldap-jena-identity": {"condition": "service_healthy"},
            "redis": {"condition": "service_started"},
        }
    )
    env = services["oldap-api"]["environment"]
    env.update(
        OLDAP_MEDIA_INTERNAL_URL="http://oldap-mediahelper:8000",
        OLDAP_MEDIA_INGEST_URL="http://oldap-mediahelper:8000",
        OLDAP_MEDIA_EXPORT_URL="http://oldap-mediahelper:8000",
        OLDAP_MAIL_HOST="disabled.invalid",
        OLDAP_MAIL_USERNAME="",
        OLDAP_MAIL_PASSWORD="",
    )
    for key in (
        "OLDAP_PASSWORD_RESET_EMAIL_BACKEND",
        "OLDAP_IMPORT_EMAIL_BACKEND",
        "OLDAP_EXPORT_EMAIL_BACKEND",
    ):
        env[key] = "console"
    for name in ("oldap-mediahelper", "oldap-imageserver"):
        services[name]["environment"]["OLDAP_API_URL"] = "http://oldap-api:8000"
        services[name]["environment"]["OLDAP_IMPORT_CALLBACK_RECONCILE_SECONDS"] = "0"
    services["oldap-mediahelper"]["environment"].update(
        MEDIA_BASE_URL="http://oldap-mediahelper:8000/",
        IIIF_BASE_URL="http://oldap-imageserver:8182/iiif/3/",
    )
    # Never use mutable tags during the actual rehearsal. Resolve locally loaded
    # images to content IDs before launch; retain requested references as evidence.
    snapshot = json.loads((root / "extracted.json").read_text())
    origins = {
        "oldap-jena": ("api", "compose-oldap-jena-1"),
        "oldap-jena-identity": ("api", "compose-oldap-jena-identity-1"),
        "oldap-api": ("api", "oldap-api"),
        "redis": ("api", "redis"),
        "oldap-mediahelper": ("media", "oldap-mediahelper"),
        "oldap-imageserver": ("media", "oldap-imageserver"),
    }
    images = {}
    for name, service in services.items():
        ref = service["image"]
        selected = ref
        # New snapshots identify the image actually running at backup time.
        # Never resolve their mutable Compose tags again during restoration.
        if "images" in snapshot:
            host, container = origins[name]
            selected = snapshot["images"][host][container]["image_id"]
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", selected):
                raise ValueError("Invalid recorded image identity")
        image = json.loads(
            subprocess.check_output(["docker", "image", "inspect", selected])
        )[0]
        service["image"] = image["Id"]
        service["pull_policy"] = "never"
        images[name] = {"requested": ref, "selected": selected, "id": image["Id"]}
    configuration = {
        "name": project,
        "services": services,
        "networks": {
            "default": {
                "internal": True,
                "driver": "bridge",
                "driver_opts": {
                    "com.docker.network.bridge.gateway_mode_ipv4": "isolated"
                },
            }
        },
    }
    target = root / "compose.json"
    with target.open("x") as stream:
        json.dump(configuration, stream, indent=2)
    (root / "images.json").write_text(json.dumps(images, indent=2) + "\n")
    print("Prepared isolated stack; no services started.")


def workers(root, project=PROJECT):
    """Add only ZIP workers to an existing isolated stack; never start them.

    Inspect restored job states before launch. Workers can reconcile retained
    terminal jobs; this is allowed only inside the disposable restored tree.
    The read-only rehearsal configuration stays available as compose.json.
    """
    if (root / "compose-workers.json").exists():
        raise FileExistsError(
            "Worker configuration already exists; retain it before preparing another"
        )
    tree = root / "tree"
    configuration = json.loads((root / "compose.json").read_text())
    if configuration["name"] != project:
        raise ValueError("Restore project mismatch")
    result = subprocess.run(
        ["docker", "compose", "--profile", "*", "config", "--format", "json"],
        cwd=tree / "opt/oldap-mediaserver/compose",
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")},
    )
    if result.returncode:
        raise RuntimeError("Archived worker configuration could not be resolved")
    media = json.loads(result.stdout)["services"]
    snapshot = json.loads((root / "extracted.json").read_text())
    for kind in ("ingest", "export"):
        name = "oldap-" + kind + "-worker"
        service = isolated_service(media[kind + "-worker"], root, tree)
        identity = snapshot["images"]["media"][name]["image_id"]
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", identity):
            raise ValueError("Invalid recorded worker image identity")
        installed = json.loads(
            subprocess.check_output(["docker", "image", "inspect", identity])
        )[0]
        if installed["Id"] != identity:
            raise ValueError("Worker image identity mismatch")
        service.update(image=identity, pull_policy="never")
        service["environment"]["OLDAP_API_URL"] = "http://oldap-api:8000"
        service["environment"]["OLDAP_" + kind.upper() + "_WORKER_ID"] = (
            project + "-" + kind
        )
        configuration["services"][name] = service
    # Export bytes are served by Caddy, not Flask. Retain the exact archived
    # export route, changing only its private helper hostname and listener.
    archived = (tree / "opt/oldap-mediaserver/compose/Caddyfile").read_text()
    start = archived.index("    @export_archive ")
    end = archived.index("    @status ", start)
    route = archived[start:end].replace("mediaserver:8000", "oldap-mediahelper:8000")
    proxy_dir = root / "runtime/export-proxy"
    proxy_dir.mkdir(exist_ok=True)
    proxy_file = proxy_dir / "Caddyfile"
    proxy_file.write_text(
        "{\n    admin off\n    auto_https off\n}\n:8080 {\n"
        + route
        + '\n    respond "not found" 404\n}\n'
    )
    identity = snapshot["images"]["media"]["oldap-media-caddy"]["image_id"]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", identity):
        raise ValueError("Invalid recorded export proxy image")
    subprocess.run(
        ["docker", "image", "inspect", identity], check=True, stdout=subprocess.DEVNULL
    )
    configuration["services"]["restore-export-proxy"] = {
        "image": identity,
        "pull_policy": "never",
        "restart": "no",
        "networks": ["default"],
        "read_only": True,
        "cap_drop": ["ALL"],
        # The recorded Caddy binary has this file capability even on port 8080.
        "cap_add": ["NET_BIND_SERVICE"],
        "security_opt": ["no-new-privileges:true"],
        "mem_limit": "128m",
        "memswap_limit": "128m",
        "tmpfs": ["/config:rw,nosuid,nodev,size=8m", "/tmp:rw,nosuid,nodev,size=8m"],
        "command": [
            "caddy",
            "run",
            "--config",
            "/etc/caddy/Caddyfile",
            "--adapter",
            "caddyfile",
        ],
        "volumes": [
            {
                "type": "bind",
                "source": str(proxy_file),
                "target": "/etc/caddy/Caddyfile",
                "read_only": True,
            },
            {
                "type": "bind",
                "source": str(tree / "data/oldap-exports"),
                "target": "/data/exports",
                "read_only": True,
            },
        ],
    }
    with (root / "compose-workers.json").open("x") as stream:
        json.dump(configuration, stream, indent=2)
    print(
        "Prepared two isolated ZIP workers and private export delivery; no services started."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["extract", "compose", "workers"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--project", default=PROJECT)
    args = parser.parse_args()
    if socket.gethostname().split(".")[0] != "api" or os.geteuid() != 0:
        raise SystemExit("Run as root on the home API VM only")
    if args.root.parent != Path("/srv/storage") or not args.root.name.startswith(
        "oldap-restore-rehearsal-"
    ):
        raise SystemExit("Unexpected rehearsal directory")
    if args.root.resolve() != args.root or (args.root / "incoming").is_symlink():
        raise SystemExit("Rehearsal paths must not redirect outside the root")
    if not re.fullmatch(r"oldap-restore-[a-z0-9-]+", args.project):
        raise SystemExit("Unexpected rehearsal project name")
    os.umask(0o077)
    if args.phase == "extract":
        extract(args.root)
    elif args.phase == "compose":
        compose(args.root, args.project)
    else:
        workers(args.root, args.project)


if __name__ == "__main__":
    main()
