"""Regression checks for the production authentication deployment contract."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INVENTORY = REPOSITORY_ROOT / "inventory.ini"
PLAYBOOK = REPOSITORY_ROOT / "oldap-deploy.yml"


def _production_host() -> dict[str, object]:
    """Resolve production inventory variables through Ansible itself."""
    with tempfile.TemporaryDirectory(prefix="oldap-setup-ansible-") as local_temp:
        environment = os.environ.copy()
        environment["ANSIBLE_LOCAL_TEMP"] = local_temp
        result = subprocess.run(
            [
                "ansible-inventory",
                "-i",
                str(INVENTORY),
                "--host",
                "dhlab-oldap",
            ],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    return json.loads(result.stdout)


class ProductionAuthenticationConfigTest(unittest.TestCase):
    """Keep the production browser and API token contract deployable together."""

    def test_api_cors_covers_every_production_frontend(self) -> None:
        """Every public frontend origin must receive API CORS responses."""
        host = _production_host()
        origins = set(str(host["oldap_auth_allowed_origins"]).split(","))

        self.assertEqual(
            origins,
            {
                "https://app.oldap.org",
                "https://fasnacht.oldap.org",
                "https://fasnacht.digital",
            },
        )

    def test_cross_site_fasnacht_refresh_uses_secure_none_cookie(self) -> None:
        """fasnacht.digital must be able to send the api.oldap.org cookie."""
        host = _production_host()

        self.assertIs(host["oldap_refresh_cookie_secure"], True)
        self.assertEqual(host["oldap_refresh_cookie_samesite"], "None")

    def test_playbook_default_uses_split_token_api_release(self) -> None:
        """Direct playbook runs must not select the legacy JWT-only API."""
        content = PLAYBOOK.read_text(encoding="utf-8")
        match = re.search(
            r'^\s*oldap_api_tag:\s*["\']v(\d+)\.(\d+)\.(\d+)["\']',
            content,
            re.MULTILINE,
        )

        self.assertIsNotNone(match, "oldap_api_tag must be an explicit SemVer tag")
        version = tuple(int(part) for part in match.groups())
        self.assertGreaterEqual(version, (0, 2, 10))

    def test_production_cutover_requires_refresh_capable_browser_client(self) -> None:
        """The playbook must reject the published legacy browser client."""
        content = PLAYBOOK.read_text(encoding="utf-8")

        self.assertIn("Validate production browser refresh compatibility", content)
        self.assertIn("is version('0.2.4', '>=')", content)
        self.assertIn("Validate production cross-site refresh cookie", content)
        self.assertIn("oldap_refresh_cookie_secure | bool", content)
        self.assertIn("when: inventory_hostname in groups['oldap_prod']", content)


if __name__ == "__main__":
    unittest.main()
