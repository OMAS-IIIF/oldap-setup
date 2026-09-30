"""Exercise bounded worker inputs, real Compose interpolation and update scope."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ApiWorkersTest(unittest.TestCase):
    def test_compose_defaults_and_explicit_limits(self):
        text = (ROOT / "docker-compose.yml").read_text()
        defaults = yaml.safe_load((ROOT / "group_vars/all.yml").read_text())
        self.assertEqual(
            (defaults["oldap_api_workers"], defaults["oldap_api_threads"]), (4, 2)
        )
        for workers, threads in [(None, None), (2, 4), (4, 4)]:
            env = {k: "/tmp/worker-fixture" for k in re.findall(r"\$\{([A-Z_]+)", text)}
            env.pop("OLDAP_API_WORKERS")
            env.pop("OLDAP_API_THREADS")
            if workers is not None:
                env.update(
                    OLDAP_API_WORKERS=str(workers), OLDAP_API_THREADS=str(threads)
                )
            with tempfile.TemporaryDirectory() as directory:
                empty = Path(directory) / ".env"
                empty.write_text("")
                result = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "--env-file",
                        str(empty),
                        "-f",
                        str(ROOT / "docker-compose.yml"),
                        "config",
                        "--format",
                        "json",
                    ],
                    env={**os.environ, **env},
                    capture_output=True,
                    text=True,
                    check=True,
                )
            args = json.loads(result.stdout)["services"]["oldap-api"]["environment"][
                "GUNICORN_CMD_ARGS"
            ]
            self.assertIn(f"--workers={workers or 4} --threads={threads or 2}", args)

    def test_ansible_accepts_only_bounded_integer_inputs(self):
        for workers, threads, valid in [
            (2, 4, True),
            (8, 16, True),
            (0, 4, False),
            (9, 4, False),
            (2, 17, False),
            (True, 4, False),
            ("2 --preload", 4, False),
            (2.5, 4, False),
        ]:
            with self.subTest(
                workers=workers, threads=threads
            ), tempfile.TemporaryDirectory() as directory:
                play = Path(directory) / "test.yml"
                play.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "gather_facts": False,
                                "vars": {
                                    "oldap_api_workers": workers,
                                    "oldap_api_threads": threads,
                                },
                                "tasks": [
                                    {
                                        "ansible.builtin.import_tasks": str(
                                            ROOT / "tasks/api-worker-preflight.yml"
                                        )
                                    }
                                ],
                            }
                        ]
                    )
                )
                run = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", "-c", "local", str(play)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode == 0, valid, run.stdout + run.stderr)

    def test_existing_deployment_refuses_unsupported_compose_and_preserves_secrets(
        self,
    ):
        play = yaml.safe_load((ROOT / "oldap-api-workers.yml").read_text())[0]
        tasks = play["tasks"]
        guard = next(
            i
            for i, t in enumerate(tasks)
            if "Require the installed Compose" in t["name"]
        )
        persist = next(
            i for i, t in enumerate(tasks) if "ansible.builtin.lineinfile" in t
        )
        self.assertLess(guard, persist)
        self.assertEqual(
            set(play["vars"]["worker_settings"]),
            {"OLDAP_API_WORKERS", "OLDAP_API_THREADS"},
        )
        start = next(
            t["community.docker.docker_compose_v2"]
            for t in tasks
            if "community.docker.docker_compose_v2" in t
        )
        self.assertEqual(start["services"], ["oldap-api"])
        self.assertFalse(start["dependencies"])
        self.assertEqual(start["pull"], "never")
        # Evaluate the actual assertion through Ansible for supported and legacy files.
        for args, valid in [
            (
                "--workers=2 --threads=4 --bind=0.0.0.0:8000 --timeout=60 --access-logfile=- --error-logfile=-",
                True,
            ),
            ("", False),
        ]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "test.yml"
                vars = {
                    "oldap_api_workers": 2,
                    "oldap_api_threads": 4,
                    "worker_compose": {
                        "stdout": json.dumps(
                            {
                                "services": {
                                    "oldap-api": {
                                        "environment": {"GUNICORN_CMD_ARGS": args}
                                    }
                                }
                            }
                        )
                    },
                }
                path.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "gather_facts": False,
                                "vars": vars,
                                "tasks": [tasks[guard]],
                            }
                        ]
                    )
                )
                run = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", "-c", "local", str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode == 0, valid, run.stdout + run.stderr)
