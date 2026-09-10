"""Render and validate the real owner/consumer deployment contracts without SSH."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]


def render(name: str, values: dict) -> str:
    """Render a deployment template with the Ansible filters it uses."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(ROOT / "templates"),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
    )
    env.filters["to_json"] = json.dumps
    env.filters["hash"] = lambda value, algorithm: hashlib.new(
        algorithm, str(value).encode()
    ).hexdigest()
    return env.get_template(name).render(**values)


def fixture() -> dict:
    """Return non-secret two-host inputs; no actual inventory is changed."""
    return {
        "oldap_writer_enabled": True,
        "oldap_writer_compatible_releases": True,
        "oldap_writer_owner": "owner",
        "oldap_writer_domain": "test-domain",
        "oldap_writer_members": ["owner", "consumer"],
        "oldap_writer_graphdb_url": "https://graphdb.test",
        "oldap_writer_repository": "oldap",
        "oldap_writer_ts_user": "",
        "oldap_writer_ts_password": "",
        "oldap_writer_hostname": "writer.test",
        "oldap_writer_port": 6379,
        "oldap_writer_password": "a" * 64,
        "oldap_writer_image": yaml.safe_load((ROOT / "group_vars/all.yml").read_text())[
            "oldap_writer_image"
        ],
        "oldap_writer_publish_address": "10.20.0.2",
        "oldap_writer_ca_file": "/fixture/ca.crt",
        "oldap_writer_policy_file": "/fixture/policy.json",
        "oldap_writer_data_dir": "/fixture/data",
        "oldap_writer_config_dir": "/fixture/config",
        "oldap_writer_client_dir": "/fixture/client",
        "writer_service_revision": "test-revision",
        "writer_client_files": {
            "results": [{"checksum": "policy"}, {"checksum": "ca"}]
        },
        "oldap_writer_url": "rediss://writer:"
        + "a" * 64
        + "@writer.test:6379/1?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/run/oldap-writer-client/ca.crt",
    }


class WriterDeploymentTest(unittest.TestCase):
    """Exercise generated configurations and actual Ansible assertions."""

    def test_owner_and_consumer_share_endpoint_without_duplicate_service(self):
        configs = [
            yaml.safe_load(
                render(
                    "writer-compose.yml.j2", {**fixture(), "inventory_hostname": host}
                )
            )
            for host in ("owner", "consumer")
        ]
        self.assertIn("archive-writer", configs[0]["services"])
        self.assertNotIn("archive-writer", configs[1]["services"])
        for service in ("oldap-api", "oldap-tools", "oldap-harvesters"):
            a, b = (config["services"][service]["environment"] for config in configs)
            self.assertEqual(a, b)
            self.assertTrue(a["OLDAP_STAGING_LOCK_REDIS_URL"].startswith("rediss://"))
        self.assertEqual(
            configs[0]["services"]["archive-writer"]["ports"], ["10.20.0.2:6379:6379"]
        )

    def test_single_host_does_not_publish_a_port(self):
        config = yaml.safe_load(
            render(
                "writer-compose.yml.j2",
                {
                    **fixture(),
                    "inventory_hostname": "owner",
                    "oldap_writer_publish_address": "",
                },
            )
        )
        self.assertNotIn("ports", config["services"]["archive-writer"])

    def test_inventory_validation_accepts_shared_topology_and_rejects_split_brain(self):
        for mismatch, expected in [(False, 0), (True, 2)]:
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory(
                prefix="wr01-inventory-"
            ) as directory:
                path = Path(directory)
                values = fixture()
                overrides = {"oldap_writer_owner": "consumer"} if mismatch else {}
                inventory = {
                    "all": {
                        "vars": values,
                        "hosts": {
                            "owner": {"ansible_connection": "local"},
                            "consumer": {"ansible_connection": "local", **overrides},
                        },
                    }
                }
                (path / "inventory.yml").write_text(yaml.safe_dump(inventory))
                (path / "check.yml").write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "owner",
                                "gather_facts": False,
                                "tasks": [
                                    {
                                        "ansible.builtin.import_tasks": str(
                                            ROOT / "tasks/writer-preflight.yml"
                                        )
                                    }
                                ],
                            }
                        ]
                    )
                )
                run = subprocess.run(
                    [
                        "ansible-playbook",
                        "-i",
                        str(path / "inventory.yml"),
                        str(path / "check.yml"),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)

    def test_bootstrap_never_reinitializes_a_previously_provisioned_store(self):
        tasks = yaml.safe_load((ROOT / "tasks/writer-store.yml").read_text())
        owner = next(
            task
            for task in tasks
            if task["name"] == "Provision the one designated writer owner"
        )
        guard = next(
            task
            for task in owner["block"]
            if task["name"] == "Refuse missing state except explicit first bootstrap"
        )
        for aof, marker, bootstrap, expected in [
            (False, False, False, 2),
            (False, False, True, 0),
            (False, True, True, 2),
            (True, True, False, 0),
        ]:
            with self.subTest(
                aof=aof, marker=marker, bootstrap=bootstrap
            ), tempfile.TemporaryDirectory(prefix="wr01-state-") as directory:
                path = Path(directory) / "guard.yml"
                path.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "gather_facts": False,
                                "vars": {
                                    "writer_aof": {"stat": {"exists": aof}},
                                    "writer_provisioned": {"stat": {"exists": marker}},
                                    "oldap_writer_bootstrap": bootstrap,
                                },
                                "tasks": [guard],
                            }
                        ]
                    )
                )
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", "-c", "local", str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode, expected, result.stdout + result.stderr
                )

    def test_compose_accepts_both_overlays(self):
        base = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        # Supply only disposable placeholders for required Compose interpolation.
        import re

        required = set(
            re.findall(r"\$\{([A-Z0-9_]+)", (ROOT / "docker-compose.yml").read_text())
        )
        env = {**os.environ, **{key: "fixture" for key in required}}
        for key in (
            "CADDY_DATA",
            "CADDY_CONF",
            "GRAPHDB_HOME",
            "GRAPHDB_INIT",
            "REDIS_DATA",
            "OLDAP_DATA",
            "OLDAP_HARVESTERS_CONFIG",
            "OLDAP_HARVESTERS_SECRETS",
            "OLDAP_HARVESTERS_LOGS",
        ):
            env[key] = "/fixture/" + key.lower()
        for host in ("owner", "consumer"):
            with self.subTest(host=host), tempfile.TemporaryDirectory(
                prefix="wr01-compose-"
            ) as directory:
                path = Path(directory)
                # The real base plus overlay are validated without starting any service.
                (path / "base.yml").write_text(yaml.safe_dump(base))
                (path / "writer.yml").write_text(
                    render(
                        "writer-compose.yml.j2",
                        {**fixture(), "inventory_hostname": host},
                    )
                )
                result = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(path / "base.yml"),
                        "-f",
                        str(path / "writer.yml"),
                        "config",
                        "--quiet",
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
