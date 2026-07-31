from __future__ import annotations

import re
import sqlite3
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class SpecialistIdentityV6Tests(unittest.TestCase):
    def test_identity_migration_applies_and_enforces_owner_schema(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE providers_private (
              provider_id TEXT PRIMARY KEY,
              email TEXT NOT NULL,
              display_name TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'active',
              notification_enabled INTEGER NOT NULL DEFAULT 1,
              accepts_new_requests INTEGER NOT NULL DEFAULT 1,
              account_enabled INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        connection.executescript(read("specialists-partners/backend/migrations/0005_identity_password_admin.sql"))
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"identity_users","identity_sessions","password_reset_tokens","provider_account_drafts","identity_audit_log"}.issubset(tables))
        connection.execute(
            """INSERT INTO identity_users (id,email,phone_e164,display_name_ar,display_name_en,role,status)
            VALUES (?,?,?,?,?,'owner','invited')""",
            ("owner-test","pterminology@gmail.com","+962795945817","خالد الذيب","Khaled Altheeb"),
        )
        row = connection.execute("SELECT email,phone_e164,display_name_ar,display_name_en,role,status FROM identity_users").fetchone()
        self.assertEqual(row,("pterminology@gmail.com","+962795945817","خالد الذيب","Khaled Altheeb","owner","invited"))
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO identity_users (id,email,display_name_ar,role,status) VALUES (?,?,?,?,?)",("bad-role","bad@example.com","Bad","root","active"))

    def test_worker_exposes_password_account_admin_and_compatibility_routes(self) -> None:
        worker = read("specialists-partners/account-backend/src/index.js")
        required_routes = (
            "/v1/auth/login","/v1/auth/password/request","/v1/auth/password/reset",
            "/v1/account/password/change","/v1/account/profile-draft","/v1/admin/users",
            "/v1/admin/core-session","/v1/admin/profile-drafts","/v1/admin/identity-audit",
            "/v1/internal/bootstrap-owner","/v1/specialist/session/request",
            "/v1/specialist/session/verify","/v1/specialist/conversations",
        )
        for route in required_routes:
            self.assertIn(route, worker)
        self.assertIn("const BUILD_VERSION = '6.0.0'", worker)
        self.assertIn("requireRole(actor,['owner']", worker)
        self.assertIn("OWNER_PHONE||'+962795945817'", worker)
        self.assertIn("OWNER_EMAIL||'pterminology@gmail.com'", worker)
        self.assertIn("display_name_ar", worker)
        self.assertIn("display_name_en", worker)
        self.assertIn("reset_token_id", worker)
        self.assertIn("actor.role==='reviewer'?env.REVIEWER_API_KEY", worker)
        self.assertIn("env.MODERATOR_API_KEY", worker)
        self.assertIn("login_token_used", worker)
        self.assertIn("requiresSetup", worker)
        self.assertIn("status=CASE WHEN status='invited' THEN 'active' ELSE status END", worker)
        self.assertIn("phone_verified_at=CASE WHEN ?=1 THEN NULL", worker)

    def test_password_storage_is_derived_and_never_plaintext(self) -> None:
        worker = read("specialists-partners/account-backend/src/index.js")
        migration = read("specialists-partners/backend/migrations/0005_identity_password_admin.sql")
        self.assertIn("PBKDF2", worker)
        self.assertIn("SHA-256", worker)
        self.assertIn("PASSWORD_ITERATIONS = 310_000", worker)
        self.assertIn("crypto.getRandomValues(new Uint8Array(16))", worker)
        self.assertIn("password_hash TEXT", migration)
        self.assertIn("password_salt TEXT", migration)
        self.assertIn("password_iterations INTEGER", migration)
        self.assertNotRegex(migration, r"(?im)^\s*password\s+TEXT")
        self.assertNotIn("localStorage", worker)

    def test_frontends_are_private_and_use_ephemeral_session_storage(self) -> None:
        account_html = read("specialists-partners/account/index.html")
        account_js = read("specialists-partners/account/account.js")
        admin_html = read("specialists-partners/admin/index.html")
        admin_js = read("specialists-partners/admin/admin.js")
        for html in (account_html, admin_html):
            self.assertIn('content="noindex,nofollow,noarchive"', html)
            self.assertIn("frame-ancestors 'none'", html)
        for script in (account_js, admin_js):
            self.assertIn("sessionStorage", script)
            self.assertNotIn("localStorage", script)
        self.assertIn('type="password"', account_html)
        self.assertIn('type="password"', admin_html)
        self.assertIn("استعادة", account_html)
        self.assertIn("إدارة الحسابات والصلاحيات", admin_html)
        self.assertIn("سجل المحادثات", account_html)
        self.assertIn("current.required=!user.mustChangePassword", account_js)

    def test_admin_contract_covers_requested_owner_operations(self) -> None:
        worker = read("specialists-partners/account-backend/src/index.js")
        admin = read("specialists-partners/admin/admin.js")
        for operation in ("createUser","updateUser","archiveUser","adminPasswordReset","verifyUser","reviewProfileDraft","identityAudit"):
            self.assertIn(operation, worker)
        for action in ("save-user","verify-user","reset-user","archive-user"):
            self.assertIn(action, admin)
        self.assertIn("applications", admin)
        self.assertIn("providers", admin)
        self.assertIn("conversations", admin)
        self.assertIn("profile-drafts", admin)

    def test_runtime_and_production_deployment_use_v10_without_committed_secrets(self) -> None:
        runtime = read("specialists-partners/assets/runtime-config.js")
        validation = read(".github/workflows/deploy-specialist-identity-v10.yml")
        production = read(".github/workflows/deploy-specialist-identity-v10-production.yml")
        verifier = read("scripts/verify_specialist_identity_v10_production.py")
        legacy = read(".github/workflows/deploy-specialists-account-backend.yml")
        self.assertIn("accountApiBase", runtime)
        self.assertIn('identityVersion: "10.3.0"', runtime)
        self.assertNotIn("wrangler@4 deploy", validation)
        self.assertIn("secrets.CLOUDFLARE_API_TOKEN", production)
        self.assertIn("/tokens/verify", production)
        self.assertIn("/d1/database", production)
        self.assertIn("wrangler@4 d1 migrations apply", production)
        self.assertIn("wrangler@4 deploy", production)
        self.assertIn('main = "src/index-v10-production.js"', production)
        self.assertIn("verify_specialist_identity_v10_production.py", production)
        self.assertIn('"x-bootstrap-key": ADMIN_KEY', verifier)
        self.assertIn("if stable >= 3", verifier)
        self.assertIn("specialist-identity-v10-production.json", production)
        self.assertNotIn("wrangler@4 deploy", legacy)
        self.assertIn("validation-only", legacy)
        self.assertNotRegex(production, r"CLOUDFLARE_API_TOKEN:\s*[A-Za-z0-9_-]{30,}")

    def test_javascript_is_syntactically_valid(self) -> None:
        files = (
            "specialists-partners/account-backend/src/index.js",
            "specialists-partners/account-backend/src/index-v8.js",
            "specialists-partners/account-backend/src/index-v10.js",
            "specialists-partners/account-backend/src/index-v10-final.js",
            "specialists-partners/account-backend/src/index-v10-production.js",
            "specialists-partners/account/account.js",
            "specialists-partners/admin/admin.js",
            "specialists-partners/admin/admin-recovery-v10-final.js",
            "specialists-partners/admin/admin-provider-status-v10.js",
            "specialists-partners/password-reset/reset-v10.js",
            "specialists-partners/recover/recover.js",
        )
        for relative in files:
            result = subprocess.run(["node","--check",str(ROOT / relative)],capture_output=True,text=True,check=False)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__ == "__main__":
    unittest.main()
