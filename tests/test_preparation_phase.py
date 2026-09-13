"""Regression checks for the deployment preparation/start boundary."""

from pathlib import Path
import unittest
import os
import shutil
import subprocess
import tempfile
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]


class PreparationPhaseTests(unittest.TestCase):
    """Verify unsafe services fail closed and ordinary stack startup is skipped."""

    def test_service_guard(self):
        tasks = yaml.safe_load((ROOT / "tasks/require-stopped-writers.yml").read_text())
        env = jinja2.Environment()
        env.filters["difference"] = lambda a, b: [x for x in a if x not in b]
        checks = tasks[1]["ansible.builtin.assert"]["that"]
        for services, allowed in [
            (["graphdb", "redis", "archive-writer"], True),
            (["graphdb", "oldap-api"], False),
            (["graphdb", "oldap-harvesters"], False),
            (["graphdb", "oldap-tools"], False),
            (["graphdb", "graphdb-init"], False),
            (["graphdb", "new-writer"], False),
            (["redis"], False),
        ]:
            with self.subTest(services=services):
                self.assertEqual(
                    all(
                        env.compile_expression(c)(
                            preparation_running_services={"stdout_lines": services}
                        )
                        for c in checks
                    ),
                    allowed,
                )
        fmt = tasks[0]["ansible.builtin.command"]["argv"][-1]
        self.assertEqual(
            env.from_string(fmt).render(), '{{.Label "com.docker.compose.service"}}'
        )

    @unittest.skipUnless(shutil.which("ansible-playbook"), "Ansible CLI required")
    def test_guard_through_ansible(self):
        """Exercise Ansible's escaping and argv transport, not just plain Jinja."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docker = root / "docker"
            docker.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "assert sys.argv[1:] == "
                + repr(
                    [
                        "ps",
                        "--filter",
                        "label=com.docker.compose.project=compose",
                        "--format",
                        '{{.Label "com.docker.compose.service"}}',
                    ]
                )
                + "\nprint(os.environ['TEST_RUNNING_SERVICES'])\n"
            )
            docker.chmod(0o755)
            play = root / "check.yml"
            play.write_text(
                yaml.safe_dump(
                    [
                        {
                            "hosts": "localhost",
                            "gather_facts": False,
                            "vars": {"compose_dir": "/opt/oldap/compose"},
                            "tasks": [
                                {
                                    "ansible.builtin.include_tasks": str(
                                        ROOT / "tasks/require-stopped-writers.yml"
                                    )
                                }
                            ],
                        }
                    ]
                )
            )
            for services, allowed in [
                ("graphdb\nredis", True),
                ("graphdb\noldap-api", False),
            ]:
                with self.subTest(services=services):
                    env = dict(
                        os.environ,
                        PATH=str(root) + os.pathsep + os.environ["PATH"],
                        TEST_RUNNING_SERVICES=services,
                    )
                    result = subprocess.run(
                        [
                            "ansible-playbook",
                            "-i",
                            "localhost,",
                            "-c",
                            "local",
                            str(play),
                        ],
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    self.assertEqual(
                        result.returncode == 0, allowed, result.stdout + result.stderr
                    )
                    self.assertNotIn("non-zero return code", result.stdout)

    def test_start_boundary(self):
        play = yaml.safe_load((ROOT / "oldap-deploy.yml").read_text())[0]
        tasks = {t["name"]: t for t in play["tasks"]}
        for name in [
            "Bring stack up (pull images, create/update containers)",
            "Provision Docker host during ordinary deployment only",
        ]:
            self.assertIn("oldap_deploy_phase == 'deploy'", tasks[name]["when"])
        activation = tasks["Start prepared applications after verified migration"]
        options = activation["community.docker.docker_compose_v2"]
        self.assertEqual(
            options["services"], ["oldap-api", "oldap-app", "fasnachts-page"]
        )
        self.assertFalse(options["dependencies"])
        self.assertFalse(options["remove_orphans"])
        self.assertEqual(activation["when"], "oldap_deploy_phase == 'activate'")
        for name in [
            "Wait for the deployed OLDAP API health endpoint",
            "Verify ZIP export service account authentication",
        ]:
            self.assertIn(
                "oldap_deploy_phase in ['deploy', 'activate']", tasks[name]["when"]
            )
        self.assertIn("ansible.builtin.command", tasks["Show running containers"])
        self.assertEqual(
            play["pre_tasks"][1]["ansible.builtin.include_tasks"],
            "tasks/require-stopped-writers.yml",
        )
        self.assertEqual(
            play["tasks"][-1]["ansible.builtin.include_tasks"],
            "tasks/require-stopped-writers.yml",
        )


if __name__ == "__main__":
    unittest.main()
