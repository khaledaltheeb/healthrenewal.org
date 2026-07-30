from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECTOR = ROOT / "specialists-partners"
BACKEND = SECTOR / "backend"


class SpecialistOwnerConsoleV4Tests(unittest.TestCase):
    def test_all_database_migrations_are_atomic_and_replayable(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            for migration in sorted((BACKEND / "migrations").glob("*.sql")):
                connection.executescript(migration.read_text(encoding="utf-8"))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertTrue(
                {
                    "admin_sessions",
                    "provider_profiles",
                    "provider_review_records",
                    "provider_profile_versions",
                    "identity_users",
                    "identity_sessions",
                    "password_reset_tokens",
                }
                <= tables
            )
            profile_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(provider_profiles)")
            }
            self.assertTrue(
                {
                    "publication_status",
                    "verification_status",
                    "consent_status",
                    "next_review_at",
                    "public_revision",
                }
                <= profile_columns
            )
            profile_foreign_tables = {
                row[2]
                for row in connection.execute(
                    "PRAGMA foreign_key_list(provider_profiles)"
                )
            }
            self.assertTrue(
                {"providers_private", "applications"} <= profile_foreign_tables
            )
        finally:
            connection.close()

    def test_worker_enforces_owner_session_publication_gate_and_versions(self) -> None:
        source = (BACKEND / "src" / "index-v2.js").read_text(encoding="utf-8")
        for marker in (
            "/v1/admin/session",
            "admin_sessions",
            "/v1/providers",
            "approve_publish",
            "profile_not_publishable",
            "provider_profile_versions",
            "authorization",
            "x-conversation-role",
            "idempotency-key",
            "conversation_credentials_in_url_or_body",
        ):
            self.assertIn(marker, source)
        self.assertIn("parsed.protocol !== 'https:'", source)
        self.assertIn("AND pp.next_review_at >= date('now')", source)
        self.assertIn("ترخيص أو تسجيل ساري مع الجهة المنظمة", source)
        self.assertLess(
            source.index("assertPublishableProfile(profile, review);"),
            source.index("const providerId = await upsertProviderData"),
            "the publication gate must run before private account mutation",
        )
        self.assertIn(
            "#conversation=${encodeURIComponent(conversationId)}",
            source,
        )
        self.assertNotIn(
            "?conversation=${encodeURIComponent(conversationId)}&token=",
            source,
        )

    def test_owner_console_contains_identity_accounts_and_sector_controls(self) -> None:
        html = (SECTOR / "admin" / "index.html").read_text(encoding="utf-8")
        script = (SECTOR / "admin" / "admin.js").read_text(encoding="utf-8")
        for identifier in (
            "admin-login-form",
            "admin-email",
            "admin-password",
            "create-user-form",
            "user-name-ar",
            "user-email",
            "user-role",
            "user-provider-id",
            "users-list",
            "applications-list",
            "providers-list",
            "conversations-list",
            "drafts-list",
            "audit-list",
        ):
            self.assertIn(identifier, html)
        for marker in (
            "/v1/auth/login",
            "/v1/admin/core-session",
            "/v1/admin/users",
            "authorization",
            "save-user",
            "verify-user",
            "reset-user",
            "archive-user",
        ):
            self.assertIn(marker, script)
        self.assertIn("sessionStorage", script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("ADMIN_API_KEY", html)
        self.assertNotIn("x-admin-key", html)

    def test_public_directory_uses_live_registry_with_static_fallback(self) -> None:
        source = (SECTOR / "assets" / "sector.js").read_text(encoding="utf-8")
        self.assertIn("/v1/providers?limit=250", source)
        self.assertIn("data/providers.json", source)
        self.assertIn("live-verified-registry", source)
        self.assertIn("static-verified-fallback", source)
        self.assertIn("p.publicationStatus==='published'", source)
        self.assertIn("p.verification?.status==='verified'", source)
        self.assertIn("p.consent?.publicProfileApproved===true", source)
        self.assertIn("protocol === 'https:'", source)

    def test_join_preview_and_conversation_transport_redact_secrets(self) -> None:
        forms = (SECTOR / "assets" / "forms.js").read_text(encoding="utf-8")
        controls = (SECTOR / "assets" / "portal-controls.js").read_text(encoding="utf-8")
        preview_start = forms.index("function publicReviewRecord()")
        preview = forms[
            preview_start:
            forms.index("function downloadJson", preview_start)
        ]
        self.assertIn("private-verification", (BACKEND / "src" / "index-v2.js").read_text(encoding="utf-8"))
        self.assertNotIn("privateEmail:", preview)
        self.assertNotIn("privatePhone", preview)
        self.assertNotIn("licenseIdentifier", preview)
        self.assertIn("parsed.protocol !== 'https:'", forms)
        self.assertIn("const payload = publicReviewRecord();", forms)
        self.assertIn("const payload = joinPayload(form);", forms)
        self.assertIn("privateFieldsRedacted", forms)
        self.assertIn("portal/#conversation=", forms)
        self.assertIn("history.replaceState", forms)
        self.assertIn("authorization", controls)
        self.assertNotIn("token:auth.token", controls)

    def test_provider_schema_accepts_expiry_and_public_verification_summary(self) -> None:
        schema = json.loads(
            (SECTOR / "data" / "provider.schema.json").read_text(encoding="utf-8")
        )
        verification = schema["properties"]["verification"]["properties"]
        self.assertIn("expired", verification["status"]["enum"])
        self.assertIn("verifiedFields", verification)
        self.assertIn("publicNote", verification)
        self.assertIn("publicRevision", schema["properties"])

    def test_sector_pages_load_platform_shell_once(self) -> None:
        pages = (
            SECTOR / "index.html",
            SECTOR / "join.html",
            SECTOR / "contact.html",
            SECTOR / "verification.html",
            SECTOR / "portal" / "index.html",
            SECTOR / "account" / "index.html",
            SECTOR / "admin" / "index.html",
        )
        for page in pages:
            text = page.read_text(encoding="utf-8")
            self.assertEqual(
                text.count("platform-core.js"),
                1,
                f"{page} loads platform-core.js more than once",
            )
            self.assertEqual(
                text.count("platform-core.css"),
                1,
                f"{page} loads platform-core.css more than once",
            )
            self.assertIn("Content-Security-Policy", text)


if __name__ == "__main__":
    unittest.main()
