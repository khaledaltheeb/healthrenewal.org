from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTOR = ROOT / "specialists-partners"
BACKEND = SECTOR / "backend"


class SpecialistMessagingV5Tests(unittest.TestCase):
    def test_v5_files_exist(self) -> None:
        for path in (
            BACKEND / "src" / "index-v3.js",
            BACKEND / "migrations" / "0004_messaging_notifications.sql",
            SECTOR / "assets" / "portal-live-v5.js",
            ROOT / ".github" / "workflows" / "deploy-specialists-messaging-v5.yml",
        ):
            self.assertTrue(path.is_file(), path)

    def test_backend_enforces_idempotency_and_dual_notifications(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((BACKEND / "src").glob("messaging-v5-*.js"))
        )
        for marker in (
            "message_requests",
            "idempotency-key",
            "message_specialist_v5",
            "message_visitor_v5",
            "message_owner_v5",
            "OWNER_DISPLAY_NAME",
            "خالد الذيب",
            "notificationPolicy",
            "provider_notifications_required",
            "لا يتضمن هذا البريد نص الرسالة",
        ):
            self.assertIn(marker, text)
        self.assertIn("if (canonical.message_id !== messageId)", text)
        self.assertNotIn("${escapeHtml(message)}", text)

    def test_message_migration_applies_after_existing_schema(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            for name in (
                "0001_initial.sql",
                "0002_operations.sql",
                "0003_provider_publication.sql",
                "0004_messaging_notifications.sql",
            ):
                connection.executescript((BACKEND / "migrations" / name).read_text(encoding="utf-8"))
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(message_requests)")
            }
            self.assertTrue(
                {"request_key_hash", "conversation_id", "sender_role", "message_id", "created_at"}
                <= columns
            )
            indexes = {
                row[1] for row in connection.execute("PRAGMA index_list(message_requests)")
            }
            self.assertIn("idx_message_requests_conversation_time", indexes)
        finally:
            connection.close()

    def test_portal_is_live_and_generates_message_keys(self) -> None:
        html = (SECTOR / "portal" / "index.html").read_text(encoding="utf-8")
        script = (SECTOR / "assets" / "portal-live-v5.js").read_text(encoding="utf-8")
        self.assertIn("portal-live-v5.js?v=5.0.0", html)
        self.assertIn('id="live-sync-state"', html)
        self.assertLess(html.index("portal-live-v5.js"), html.index("forms.js"))
        for marker in (
            "idempotency-key",
            "REFRESH_INTERVAL_MS",
            "visibilitychange",
            "navigator.onLine",
            "migrateLegacyQueryCredentials",
            "history.replaceState",
        ):
            self.assertIn(marker, script)

    def test_push_to_main_deploys_v5_worker(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "deploy-specialists-messaging-v5.yml"
        ).read_text(encoding="utf-8")
        for marker in (
            "push:",
            "branches: [main]",
            'main = "src/index-v3.js"',
            'OWNER_DISPLAY_NAME = "خالد الذيب"',
            "d1 migrations apply",
            "wrangler@4 deploy",
            "health['version'] == '5.0.0'",
        ):
            self.assertIn(marker, workflow)


if __name__ == "__main__":
    unittest.main()
