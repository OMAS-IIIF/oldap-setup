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
ENV_TEMPLATE = REPOSITORY_ROOT / "templates" / "oldap.env.j2"
COMPOSE_FILE = REPOSITORY_ROOT / "docker-compose.yml"


def _inventory_host(hostname: str) -> dict[str, object]:
    """Resolve one host's inventory variables through Ansible itself."""
    with tempfile.TemporaryDirectory(prefix="oldap-setup-ansible-") as local_temp:
        environment = os.environ.copy()
        environment["ANSIBLE_LOCAL_TEMP"] = local_temp
        result = subprocess.run(
            [
                "ansible-inventory",
                "-i",
                str(INVENTORY),
                "--host",
                hostname,
            ],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    return json.loads(result.stdout)


def _production_host() -> dict[str, object]:
    """Resolve production inventory variables through Ansible itself."""
    return _inventory_host("dhlab-oldap")


def _home_host() -> dict[str, object]:
    """Resolve home test inventory variables through Ansible itself."""
    return _inventory_host("home")


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

    def test_password_reset_uses_fasnacht_frontend_and_unibas_relay(self) -> None:
        """Production reset links and mail must use the verified deployment path."""
        host = _production_host()

        self.assertEqual(
            host["oldap_password_reset_frontend_url"],
            "https://fasnacht.digital",
        )
        self.assertEqual(host["oldap_password_reset_email_backend"], "smtp")
        self.assertEqual(host["oldap_mail_host"], "smtp.unibas.ch")
        self.assertEqual(host["oldap_mail_port"], 25)
        self.assertEqual(host["oldap_mail_from"], "lukas.rosenthaler@unibas.ch")
        self.assertIs(host["oldap_mail_use_tls"], True)

    def test_smtp_settings_reach_api_container(self) -> None:
        """The rendered environment and Compose service must carry SMTP settings."""
        template = ENV_TEMPLATE.read_text(encoding="utf-8")
        compose = COMPOSE_FILE.read_text(encoding="utf-8")

        for variable in (
            "OLDAP_MAIL_HOST",
            "OLDAP_MAIL_PORT",
            "OLDAP_MAIL_FROM",
            "OLDAP_MAIL_USERNAME",
            "OLDAP_MAIL_PASSWORD",
            "OLDAP_MAIL_USE_TLS",
        ):
            self.assertIn(f"{variable}=", template)
            self.assertIn(f"{variable}:", compose)

    def test_zip_import_contract_reaches_api_container(self) -> None:
        """All import trust boundaries and service settings must be deployed."""
        host = _production_host()
        template = ENV_TEMPLATE.read_text(encoding="utf-8")
        compose = COMPOSE_FILE.read_text(encoding="utf-8")

        self.assertEqual(host["oldap_public_app_url"], "https://fasnacht.digital")
        self.assertEqual(host["oldap_media_ingest_url"], "https://media.oldap.org")
        self.assertEqual(host["oldap_media_internal_url"], "https://media.oldap.org")
        self.assertEqual(host["oldap_import_email_backend"], "smtp")

        for variable in (
            "OLDAP_IMPORT_UPLOAD_JWT_SECRET",
            "OLDAP_IMPORT_SERVICE_JWT_SECRET",
            "OLDAP_IMPORT_RECORDS_JWT_SECRET",
            "OLDAP_IMPORT_SERVICE_USER",
            "OLDAP_IMPORT_SERVICE_PASSWORD",
            "OLDAP_MEDIA_INGEST_URL",
            "OLDAP_MEDIA_INTERNAL_URL",
            "OLDAP_IMPORT_EMAIL_BACKEND",
        ):
            self.assertIn(f"{variable}=", template)
            self.assertIn(f"{variable}:", compose)

        self.assertIn(
            "OLDAP_PUBLIC_APP_URL={{ oldap_public_app_url",
            template,
        )

    def test_zip_export_contract_reaches_api_container(self) -> None:
        """Export credentials, delivery origin, and mail mode must be deployed."""
        host = _production_host()
        template = ENV_TEMPLATE.read_text(encoding="utf-8")
        compose = COMPOSE_FILE.read_text(encoding="utf-8")

        self.assertEqual(host["oldap_public_app_url"], "https://fasnacht.digital")
        self.assertEqual(host["oldap_media_export_url"], "https://media.oldap.org")
        self.assertEqual(host["oldap_export_email_backend"], "smtp")
        for variable in (
            "OLDAP_EXPORT_SERVICE_JWT_SECRET",
            "OLDAP_EXPORT_DOWNLOAD_JWT_SECRET",
            "OLDAP_EXPORT_SERVICE_USER",
            "OLDAP_EXPORT_SERVICE_PASSWORD",
            "OLDAP_EXPORT_MAX_ARCHIVE_BYTES",
            "OLDAP_EXPORT_READY_RETENTION_HOURS",
            "OLDAP_EXPORT_AUDIT_RETENTION_DAYS",
            "OLDAP_EXPORT_MAX_ACTIVE_JOBS_PER_USER",
            "OLDAP_EXPORT_MAX_ACTIVE_JOBS_TOTAL",
            "OLDAP_EXPORT_MAX_RESERVED_BYTES_PER_USER",
            "OLDAP_EXPORT_MAX_RESERVED_BYTES_TOTAL",
            "OLDAP_MEDIA_EXPORT_URL",
            "OLDAP_EXPORT_EMAIL_BACKEND",
        ):
            self.assertIn(f"{variable}=", template)
            self.assertIn(f"{variable}:", compose)

        defaults = (REPOSITORY_ROOT / "group_vars" / "all.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("oldap_export_max_archive_bytes: 50000000000", defaults)
        self.assertIn("oldap_export_ready_retention_hours: 24", defaults)
        self.assertIn("oldap_export_audit_retention_days: 60", defaults)
        self.assertIn("oldap_export_max_active_jobs_per_user: 3", defaults)
        self.assertIn("oldap_export_max_active_jobs_total: 20", defaults)
        self.assertIn(
            "oldap_export_max_reserved_bytes_per_user: 100000000000", defaults
        )
        self.assertIn(
            "oldap_export_max_reserved_bytes_total: 500000000000", defaults
        )

    def test_home_uses_internal_http_without_changing_public_media_https(self) -> None:
        """The test API must avoid the untrusted private CA server-to-server."""
        host = _home_host()

        self.assertEqual(host["oldap_media_ingest_url"], "https://media.home.org")
        self.assertEqual(host["oldap_media_internal_url"], "http://media.home.org")

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
        self.assertIn("Validate SMTP password-reset delivery configuration", content)
        self.assertIn("Validate production ZIP-import integration", content)
        self.assertIn("Validate production ZIP-export integration", content)
        self.assertIn("Wait for the deployed OLDAP API health endpoint", content)
        self.assertIn("Verify ZIP export service account authentication", content)
        self.assertIn("/mobile/v1/auth/login", content)
        self.assertIn("nine distinct JWT secrets", content)
        self.assertIn("when: inventory_hostname in groups['oldap_prod']", content)


if __name__ == "__main__":
    unittest.main()
