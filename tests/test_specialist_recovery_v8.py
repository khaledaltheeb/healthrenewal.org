from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SpecialistRecoveryV8Tests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_admin_recovery_button_does_not_navigate_away(self):
        html = self.read("specialists-partners/admin/index.html")
        self.assertIn('id="admin-forgot" type="button"', html)
        self.assertIn('href="../recover/?v=10.2.0"', html)
        self.assertIn('runtime-config.js?v=10.2.0', html)
        self.assertNotRegex(html, r'id="admin-forgot"[^>]+href=')

    def test_overlay_intercepts_recovery_and_delegates_other_routes(self):
        js = self.read("specialists-partners/account-backend/src/index-v8.js")
        self.assertIn("import baseWorker from './index.js'", js)
        self.assertIn("'/v1/auth/password/request'", js)
        self.assertIn("'/v1/internal/owner-password-reset'", js)
        self.assertIn("return await baseWorker.fetch(request, env, ctx)", js)
        self.assertIn("PASSWORD_RESET_BASE_URL", js)
        self.assertIn("password-reset", js)
        self.assertIn("email_delivery_failed", js)
        self.assertIn("password_email_sent", js)
        self.assertIn("password_email_failed", js)

    def test_recovery_waits_for_resend_and_retries(self):
        js = self.read("specialists-partners/account-backend/src/index-v8.js")
        request_body = re.search(
            r"async function requestPasswordReset\(.*?\n}\n\nasync function ownerPasswordReset",
            js,
            re.S,
        )
        self.assertIsNotNone(request_body)
        body = request_body.group(0)
        self.assertIn("await issuePasswordReset", body)
        self.assertNotIn("ctx.waitUntil", body)
        self.assertIn("for (let attempt = 1; attempt <= 3", js)
        self.assertIn("response.status !== 429", js)

    def test_reset_links_always_use_dedicated_page(self):
        js = self.read("specialists-partners/account-backend/src/index-v8.js")
        self.assertIn("const base = validHttpsBase(env.PASSWORD_RESET_BASE_URL)", js)
        self.assertIn("?v=10#resetToken=", js)
        self.assertNotIn("ADMIN_BASE_URL", js)
        self.assertNotIn("ACCOUNT_BASE_URL", js)


if __name__ == "__main__":
    unittest.main()
