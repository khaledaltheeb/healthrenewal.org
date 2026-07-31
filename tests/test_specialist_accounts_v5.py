from __future__ import annotations

import sqlite3
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "specialists-partners" / "account-backend" / "src" / "index.js"
FRONTEND = ROOT / "specialists-partners" / "account" / "account.js"
ACCOUNT_HTML = ROOT / "specialists-partners" / "account" / "index.html"
MIGRATIONS = ROOT / "specialists-partners" / "backend" / "migrations"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-specialist-identity-v10-production.yml"
PROPAGATION = ROOT / "scripts" / "verify_specialist_identity_v10_production.py"
RUNTIME = ROOT / "specialists-partners" / "assets" / "runtime-config.js"
DIRECTORY = ROOT / "specialists-partners" / "index.html"
JOIN = ROOT / "specialists-partners" / "join.html"
PORTAL = ROOT / "specialists-partners" / "portal" / "index.html"
ROBOTS = ROOT / "robots.txt"


class SpecialistAccountsV5Tests(unittest.TestCase):
    def test_javascript_is_syntactically_valid(self) -> None:
        for path in (WORKER, FRONTEND):
            completed = subprocess.run(
                ["node", "--check", str(path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_account_routes_and_security_contracts(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        for marker in (
            "/v1/specialist/session/request",
            "/v1/specialist/session/verify",
            "/v1/specialist/session/revoke",
            "/v1/specialist/me",
            "/v1/specialist/conversations",
            "specialist_login_tokens",
            "specialist_sessions",
            "token_hash",
            "verifyTurnstile",
            "specialist_login",
            "constantTimeEqual",
            "idempotency-key",
        ):
            self.assertIn(marker, source)
        self.assertIn("password_hash", source)
        self.assertNotIn("localStorage", source)

    def test_frontend_uses_ephemeral_browser_storage(self) -> None:
        source = FRONTEND.read_text(encoding="utf-8")
        html = ACCOUNT_HTML.read_text(encoding="utf-8")
        self.assertIn("sessionStorage", source)
        self.assertNotIn("localStorage", source)
        self.assertIn("accountApiBase", source)
        self.assertIn("/v1/specialist/session/verify", source)
        self.assertIn("noindex,nofollow,noarchive", html)
        self.assertIn("frame-ancestors 'none'", html)
        self.assertIn('type="password"', html)

    def test_migrations_apply_in_sequence(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            for path in sorted(MIGRATIONS.glob("*.sql")):
                connection.executescript(path.read_text(encoding="utf-8"))
            provider_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(providers_private)")
            }
            self.assertIn("account_enabled", provider_columns)
            self.assertIn("account_last_login_at", provider_columns)
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for name in (
                "specialist_login_tokens",
                "specialist_sessions",
                "specialist_message_requests",
            ):
                self.assertIn(name, tables)
        finally:
            connection.close()

    def test_deployment_contract(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        verifier = PROPAGATION.read_text(encoding="utf-8")
        runtime = RUNTIME.read_text(encoding="utf-8")
        for marker in (
            "push:",
            "pterminology-specialist-accounts",
            "SPECIALISTS_D1_DATABASE_ID",
            "SPECIALISTS_RATE_LIMIT_SALT",
            "d1 migrations apply",
            "wrangler@4 deploy",
            "src/index-v10-production.js",
            "verify_specialist_identity_v10_production.py",
            "Deep health must not be public",
            "specialist-identity-v10-production.json",
        ):
            self.assertIn(marker, workflow)
        self.assertIn('"x-bootstrap-key": ADMIN_KEY', verifier)
        self.assertIn("public_deep_ok", verifier)
        self.assertIn("if stable >= 3", verifier)
        self.assertIn("accountApiBase", runtime)
        self.assertIn('identityVersion: "10.3.0"', runtime)
        self.assertNotRegex(workflow, r"RESEND_API_KEY:\s*re_[A-Za-z0-9_-]+")

    def test_account_entry_points_are_exposed_but_not_indexed(self) -> None:
        self.assertIn('href="account/"', DIRECTORY.read_text(encoding="utf-8"))
        self.assertIn('href="account/"', JOIN.read_text(encoding="utf-8"))
        self.assertIn('href="../account/"', PORTAL.read_text(encoding="utf-8"))
        self.assertIn("specialists-partners/account/", ROBOTS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
