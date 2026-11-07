"""Reject archives and mounts that could escape the isolated restore root."""

import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "restore", Path(__file__).parents[1] / "scripts/prepare-home-restore.py"
)
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class RestoreBoundaryTests(unittest.TestCase):
    def test_rejects_archive_traversal_links_devices_and_wrong_roots(self):
        for name, kind in [
            ("/etc/passwd", tarfile.REGTYPE),
            ("data/media/../../etc/passwd", tarfile.REGTYPE),
            ("data/media/link", tarfile.SYMTYPE),
            ("data/media/hard", tarfile.LNKTYPE),
            ("data/media/device", tarfile.CHRTYPE),
            ("opt/other", tarfile.REGTYPE),
        ]:
            with self.subTest(name=name):
                item = tarfile.TarInfo(name)
                item.type = kind
                with self.assertRaises(ValueError):
                    restore.validate_members([item], "media")
        restore.validate_members([tarfile.TarInfo("data/media/example.jp2")], "media")

    def test_live_paths_are_rebased_and_runtime_connections_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tree = root / "tree"
            (tree / "data/media").mkdir(parents=True)
            source = {
                "image": "test",
                "container_name": "live",
                "ports": ["80:80"],
                "network_mode": "host",
                "depends_on": {"live-worker": {}},
                "volumes": [
                    {"type": "bind", "source": "/data/media", "target": "/data/images"}
                ],
            }
            service = restore.isolated_service(source, root, tree)
            self.assertEqual(service["volumes"][0]["source"], str(tree / "data/media"))
            self.assertEqual(service["restart"], "no")
            for key in ("container_name", "ports", "network_mode", "depends_on"):
                self.assertNotIn(key, service)

    def test_missing_or_redirected_mounts_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tree = root / "tree"
            tree.mkdir()
            source = {
                "image": "test",
                "volumes": [{"type": "bind", "source": "/data", "target": "/data"}],
            }
            with self.assertRaises(ValueError):
                restore.isolated_service(source, root, tree)
            (tree / "data").symlink_to(root)
            with self.assertRaises(ValueError):
                restore.isolated_service(source, root, tree)

    def test_parser_capabilities_survive_but_privileged_capabilities_fail(self):
        """The isolated parser needs its UID switch; SYS_ADMIN must never pass."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tree = root / "tree"
            tree.mkdir()
            caps = ["CHOWN", "DAC_OVERRIDE", "FOWNER", "KILL", "SETGID", "SETUID"]
            service = restore.isolated_service(
                {"cap_drop": ["ALL"], "cap_add": caps}, root, tree
            )
            self.assertEqual(service["cap_add"], caps)
            self.assertEqual(service["cap_drop"], ["ALL"])
            with self.assertRaises(ValueError):
                restore.isolated_service({"cap_add": ["SYS_ADMIN"]}, root, tree)


class RestoreComparisonTests(unittest.TestCase):
    def test_only_keyword_identifiers_are_expanded(self):
        spec = importlib.util.spec_from_file_location(
            "acceptance", Path(__file__).parents[1] / "scripts/check-home-restore.py"
        )
        acceptance = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(acceptance)
        source = [
            {
                "fasnacht:storyKeywords": ["L-StoryKeywords:Example"],
                "schema:abstract": "L-StoryKeywords:Example",
            }
        ]
        expanded = acceptance.canonical_stories(source)
        self.assertEqual(
            expanded[0]["fasnacht:storyKeywords"],
            ["http://fasnacht.digital/ns/StoryKeywords#Example"],
        )
        self.assertEqual(expanded[0]["schema:abstract"], "L-StoryKeywords:Example")
        self.assertEqual(
            source[0]["fasnacht:storyKeywords"], ["L-StoryKeywords:Example"]
        )


class RestoreImageTests(unittest.TestCase):
    def test_recorded_image_ids_override_mutable_compose_tags(self):
        """A changed local tag must never change a new snapshot's restored image."""
        import json
        from unittest.mock import patch

        identity = "sha256:" + "a" * 64
        api_names = ("oldap-jena", "oldap-jena-identity", "oldap-api", "redis")

        def service():
            return {"image": "example:mutable", "environment": {}}

        api = {"services": {name: service() for name in api_names}}
        media = {
            "services": {name: service() for name in ("mediaserver", "imageserver")}
        }
        snapshot = {
            "images": {
                "api": {
                    name: {"image_id": identity}
                    for name in (
                        "compose-oldap-jena-1",
                        "compose-oldap-jena-identity-1",
                        "oldap-api",
                        "redis",
                    )
                },
                "media": {
                    name: {"image_id": identity}
                    for name in ("oldap-mediahelper", "oldap-imageserver")
                },
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tree").mkdir()
            (root / "extracted.json").write_text(json.dumps(snapshot))
            with patch.object(
                restore, "read_compose", side_effect=[api, media]
            ), patch.object(
                restore.subprocess,
                "check_output",
                return_value=json.dumps([{"Id": identity}]).encode(),
            ) as inspect:
                restore.compose(root, "oldap-restore-image-test")
            self.assertEqual(inspect.call_count, 6)
            self.assertTrue(
                all(call.args[0][-1] == identity for call in inspect.call_args_list)
            )
            result = json.loads((root / "compose.json").read_text())
            self.assertEqual(result["name"], "oldap-restore-image-test")
            self.assertTrue(
                all(s["image"] == identity for s in result["services"].values())
            )


class RestoreWorkerTests(unittest.TestCase):
    def test_workers_keep_recorded_images_and_private_export_delivery(self):
        """Worker restore keeps parser rights and cannot introduce live mounts/ports."""
        import json
        from types import SimpleNamespace
        from unittest.mock import patch

        identity = "sha256:" + "b" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tree = root / "tree"
            directory = tree / "opt/oldap-mediaserver/compose"
            directory.mkdir(parents=True)
            (tree / "data/oldap-exports").mkdir(parents=True)
            (root / "runtime").mkdir()
            (directory / "Caddyfile").write_text(
                "site {\n    @export_archive path /exports/*\n"
                "    handle @export_archive {\n        reverse_proxy mediaserver:8000\n    }\n"
                "    @status path /status\n}\n"
            )
            (root / "compose.json").write_text(
                json.dumps({"name": "oldap-restore-unit", "services": {}})
            )
            origins = (
                "oldap-ingest-worker",
                "oldap-export-worker",
                "oldap-media-caddy",
            )
            (root / "extracted.json").write_text(
                json.dumps(
                    {
                        "images": {
                            "media": {name: {"image_id": identity} for name in origins}
                        }
                    }
                )
            )
            media = {
                "services": {
                    name: {
                        "image": "mutable:tag",
                        "environment": {},
                        "ports": ["8000:8000"],
                        "restart": "always",
                        "network_mode": "host",
                    }
                    for name in ("ingest-worker", "export-worker")
                }
            }
            media["services"]["ingest-worker"]["cap_add"] = ["SETUID", "SETGID"]
            result = SimpleNamespace(returncode=0, stdout=json.dumps(media))
            with patch.object(
                restore.subprocess, "run", return_value=result
            ), patch.object(
                restore.subprocess,
                "check_output",
                return_value=json.dumps([{"Id": identity}]).encode(),
            ):
                restore.workers(root, "oldap-restore-unit")
            config = json.loads((root / "compose-workers.json").read_text())
            for service in config["services"].values():
                self.assertEqual(service["image"], identity)
                self.assertEqual(service["restart"], "no")
                self.assertNotIn("ports", service)
                self.assertNotIn("network_mode", service)
            ingest = config["services"]["oldap-ingest-worker"]
            self.assertEqual(ingest["cap_add"], ["SETUID", "SETGID"])
            self.assertEqual(
                ingest["environment"]["OLDAP_API_URL"], "http://oldap-api:8000"
            )
            proxy = config["services"]["restore-export-proxy"]
            self.assertTrue(all(mount["read_only"] for mount in proxy["volumes"]))
            self.assertTrue(
                all(
                    Path(mount["source"]).is_relative_to(root)
                    for mount in proxy["volumes"]
                )
            )
            proxy_file = root / "runtime/export-proxy/Caddyfile"
            before = proxy_file.read_text()
            self.assertIn("oldap-mediahelper:8000", before)
            self.assertNotIn("site {", before)
            with self.assertRaises(FileExistsError):
                restore.workers(root, "oldap-restore-unit")
            self.assertEqual(proxy_file.read_text(), before)


class RestoreRestartTests(unittest.TestCase):
    def test_owned_claim_drains_before_restart(self):
        """A log burst still triggers TERM and restart only after normal exit."""
        import contextlib
        import io
        import json
        from unittest.mock import MagicMock, patch

        spec = importlib.util.spec_from_file_location(
            "restart",
            Path(__file__).parents[1] / "scripts/restart-home-restore-ingest.py",
        )
        restart = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(restart)
        initial = {
            "Config": {"Labels": {"com.docker.compose.project": restart.PROJECT}},
            "State": {"Running": True},
        }
        final = {"State": {"OOMKilled": False, "FinishedAt": "2026-11-06T22:53:36Z"}}
        follower = MagicMock()
        follower.stdout = io.StringIO(
            "previous event\ningest_claimed importId=owned-job\n"
        )
        with patch.object(
            restart.subprocess,
            "check_output",
            side_effect=[
                json.dumps([initial]),
                "owned-job\n",
                "0\n",
                json.dumps([final]),
                "outcome=IMPORTED\n",
            ],
        ), patch.object(
            restart.subprocess, "Popen", return_value=follower
        ), patch.object(
            restart.subprocess, "run"
        ) as command, patch.object(
            restart.threading, "Timer"
        ) as timer, contextlib.redirect_stdout(
            io.StringIO()
        ):
            restart.main()
        self.assertEqual(
            command.call_args_list[0].args[0],
            ["docker", "kill", "--signal=TERM", restart.WORKER],
        )
        self.assertEqual(
            command.call_args_list[1].args[0], ["docker", "start", restart.WORKER]
        )
        timer.return_value.start.assert_called_once()
        self.assertTrue(timer.return_value.cancel.called)
