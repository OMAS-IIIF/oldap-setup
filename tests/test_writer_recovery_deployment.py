"""Recovery opt-in credentials, inventory binding and API-only distribution."""

import subprocess
import tempfile
from pathlib import Path
import unittest
import yaml
from tests.test_writer_deployment import ROOT, fixture, render


def recovery_fixture():
    return {
        **fixture(),
        "oldap_writer_recovery_enabled": True,
        "oldap_writer_recovery_password": "b" * 64,
        "oldap_writer_operator_password": "c" * 64,
        "oldap_writer_recovery_role_iri": "urn:oldap:roles:WriterRecoveryOperator",
        "oldap_writer_recovery_inventory_sha256": "d" * 64,
    }


class RecoveryDeploymentTest(unittest.TestCase):
    def test_only_api_receives_recovery_secret_and_no_service_gets_operator_secret(
        self,
    ):
        config = render(
            "writer-compose.yml.j2",
            {**recovery_fixture(), "inventory_hostname": "owner"},
        )
        services = yaml.safe_load(config)["services"]
        self.assertIn(
            "recovery-api:" + "b" * 64,
            services["oldap-api"]["environment"]["OLDAP_WRITER_RECOVERY_REDIS_URL"],
        )
        self.assertNotIn("c" * 64, config)
        for service in ("oldap-tools", "oldap-harvesters"):
            self.assertNotIn(
                "OLDAP_WRITER_RECOVERY_REDIS_URL", services[service]["environment"]
            )
        defaults = yaml.safe_load((ROOT / "group_vars/all.yml").read_text())
        self.assertIs(defaults["oldap_writer_recovery_enabled"], False)

    def test_preflight_rejects_credential_reuse_and_inventory_mismatch(self):
        for mismatch in (None, "secret", "inventory"):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory(
                prefix="wr02-preflight-"
            ) as directory:
                values = recovery_fixture()
                if mismatch == "secret":
                    values["oldap_writer_operator_password"] = values[
                        "oldap_writer_password"
                    ]
                override = (
                    {"oldap_writer_recovery_inventory_sha256": "e" * 64}
                    if mismatch == "inventory"
                    else {}
                )
                path = Path(directory)
                (path / "inventory.yml").write_text(
                    yaml.safe_dump(
                        {
                            "all": {
                                "vars": values,
                                "hosts": {
                                    "owner": {"ansible_connection": "local"},
                                    "consumer": {
                                        "ansible_connection": "local",
                                        **override,
                                    },
                                },
                            }
                        }
                    )
                )
                (path / "test.yml").write_text(
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
                result = subprocess.run(
                    [
                        "ansible-playbook",
                        "-i",
                        str(path / "inventory.yml"),
                        str(path / "test.yml"),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0 if mismatch is None else 2,
                    result.stdout + result.stderr,
                )
