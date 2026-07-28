from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTOR = ROOT / "specialists-partners"
BACKEND = SECTOR / "backend"


class SpecialistOperationsV3Tests(unittest.TestCase):
    def test_operations_files_exist(self) -> None:
        required = (
            BACKEND / "src" / "index-v2.js",
            BACKEND / "migrations" / "0002_operations.sql",
            BACKEND / "wrangler.toml.example",
            SECTOR / "admin" / "index.html",
            SECTOR / "admin" / "admin.js",
            SECTOR / "admin" / "admin.css",
            SECTOR / "assets" / "portal-controls.js",
            ROOT / ".github" / "workflows" / "deploy-specialists-backend.yml",
        )
        for path in required:
            self.assertTrue(path.is_file(), path)

    def test_admin_page_is_private_by_indexing_policy(self) -> None:
        text = (SECTOR / "admin" / "index.html").read_text(encoding="utf-8")
        self.assertIn('lang="ar"', text)
        self.assertIn('dir="rtl"', text)
        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', text)
        self.assertIn('name="referrer" content="no-referrer"', text)
        self.assertEqual(text.count("<h1"), 1)
        self.assertNotIn("ADMIN_API_KEY", text)
        self.assertNotIn("RESEND_API_KEY", text)

    def test_worker_exposes_operational_contracts(self) -> None:
        text = (BACKEND / "src" / "index-v2.js").read_text(encoding="utf-8")
        for marker in (
            "/v1/admin/overview",
            "/v1/admin/applications",
            "/v1/admin/conversations",
            "/v1/admin/providers",
            "/v1/admin/audit",
            "updateConversationByParticipant",
            "TURNSTILE_EXPECTED_HOSTNAMES",
            "idempotency-key",
            "user-agent",
            "email_events",
            "x-admin-key",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("replace-with-a-long-random-value", text)

    def test_migrations_apply_in_sequence(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            for name in ("0001_initial.sql", "0002_operations.sql"):
                connection.executescript((BACKEND / "migrations" / name).read_text(encoding="utf-8"))
            provider_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(providers_private)")
            }
            application_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(applications)")
            }
            conversation_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(conversations)")
            }
            self.assertIn("accepts_new_requests", provider_columns)
            self.assertTrue({"admin_notes", "reviewed_at", "reviewed_by"} <= application_columns)
            self.assertTrue({"admin_notes", "closed_by"} <= conversation_columns)
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("email_events", tables)
        finally:
            connection.close()

    def test_deploy_workflow_uses_github_and_cloudflare_secrets(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "deploy-specialists-backend.yml"
        ).read_text(encoding="utf-8")
        for secret in (
            "CLOUDFLARE_API_TOKEN",
            "CLOUDFLARE_ACCOUNT_ID",
            "SPECIALISTS_D1_DATABASE_ID",
            "RESEND_API_KEY",
            "TURNSTILE_SECRET",
            "SPECIALISTS_ADMIN_API_KEY",
            "SPECIALISTS_RATE_LIMIT_SALT",
            "SPECIALISTS_FROM_EMAIL",
        ):
            self.assertIn(f"secrets.{secret}", text)
        self.assertIn("--secrets-file worker-secrets.json", text)
        self.assertIn("d1 migrations apply", text)
        self.assertIn("rm -f worker-secrets.json wrangler.toml", text)
        self.assertNotIn("re_", text)

    def test_public_runtime_config_contains_no_private_credentials(self) -> None:
        text = (SECTOR / "assets" / "runtime-config.js").read_text(encoding="utf-8")
        for forbidden in (
            "ADMIN_API_KEY",
            "RESEND_API_KEY",
            "TURNSTILE_SECRET",
            "CLOUDFLARE_API_TOKEN",
            "RATE_LIMIT_SALT",
        ):
            self.assertNotIn(forbidden, text)

    def test_portal_supports_status_controls_without_indexing(self) -> None:
        html = (SECTOR / "portal" / "index.html").read_text(encoding="utf-8")
        script = (SECTOR / "assets" / "portal-controls.js").read_text(encoding="utf-8")
        self.assertIn('id="toggle-conversation-status"', html)
        self.assertIn("portal-controls.js", html)
        self.assertIn("history.replaceState", script)
        self.assertIn("method:'PATCH'", script)


if __name__ == "__main__":
    unittest.main()
