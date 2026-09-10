"""Foreground entry points for reviewed local macOS LaunchAgents.

This is a development-laptop runtime, not the production deployment. It runs no
shell, reloader, daemonization or child worker pool. Launchd owns the whole process
lifetime. All configuration paths come from private operator-owned LaunchAgents.
"""

import argparse
import os
from pathlib import Path
import shlex


def start_api(environment: Path) -> None:
    """Load the existing private dotenv and serve a single threaded API process."""
    from dotenv import load_dotenv

    load_dotenv(environment, override=True)
    os.environ.update(
        {
            "OLDAP_TS_SERVER": "http://localhost:7200",
            "OLDAP_TS_REPO": "oldap",
            "OLDAP_API_PORT": "8000",
            "OLDAP_IIIF_SERVER": "http://localhost:8182",
            "OLDAP_UPLOAD_SERVER": "http://localhost:8080",
            "OLDAP_REDIS_URL": "redis://localhost:6379/0",
            "APP_ENV": "Dev",
        }
    )
    from oldap_api import create_app

    app = create_app()
    app.run(host="127.0.0.1", port=8000, debug=False, use_reloader=False, threaded=True)


def start_redis(binary: Path, configuration: Path) -> None:
    """Refuse missing AOF storage before Redis can initialize an empty writer store.

    Redis itself validates manifest/checksums, with aof-load-truncated=no required.
    This entry point deliberately offers no bootstrap/reset command.
    """
    entries = [
        shlex.split(line, comments=True)
        for line in configuration.read_text().splitlines()
    ]
    config = {entry[0]: entry[1:] for entry in entries if entry}
    required = {
        "appendonly": ["yes"],
        "appendfsync": ["always"],
        "aof-load-truncated": ["no"],
        "maxmemory-policy": ["noeviction"],
        "daemonize": ["no"],
    }
    if (
        any(config.get(key) != value for key, value in required.items())
        or "include" in config
    ):
        raise ValueError(
            "Writer Redis requires explicit durable foreground configuration."
        )
    directory = Path(config["dir"][0])
    manifest = (
        directory
        / config.get("appenddirname", ["appendonlydir"])[0]
        / (config.get("appendfilename", ["appendonly.aof"])[0] + ".manifest")
    )
    if (
        not directory.is_absolute()
        or not manifest.is_file()
        or manifest.stat().st_size == 0
    ):
        raise ValueError(
            "Writer AOF is missing; coordinated operator recovery is required."
        )
    os.execv(str(binary), [str(binary), str(configuration)])


def main() -> None:
    """Only the two fixed service entry points are exposed to the offline operator."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="service", required=True)
    api = sub.add_parser("api")
    api.add_argument("--environment", type=Path, required=True)
    redis = sub.add_parser("redis")
    redis.add_argument("--binary", type=Path, required=True)
    redis.add_argument("--configuration", type=Path, required=True)
    args = parser.parse_args()
    if args.service == "api":
        start_api(args.environment)
    else:
        start_redis(args.binary, args.configuration)


if __name__ == "__main__":
    main()
