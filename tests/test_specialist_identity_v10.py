import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKER = ROOT / "specialists-partners/account-backend/src/index-v10.js"
ADMIN_RECOVERY = ROOT / "specialists-partners/admin/admin-recovery-v10.js"
RUNTIME = ROOT / "specialists-partners/assets/runtime-config.js"
DEPLOY = ROOT / ".github/workflows/deploy-specialist-identity-v10.yml"


class SpecialistIdentityV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = WORKER.read_text(encoding="utf-8")
        cls.admin = ADMIN_RECOVERY.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")

    def test_worker_uses_v10_overlay(self):
        self.assertIn("const BUILD_VERSION = '10.0.0'", self.worker)
        self.assertIn("import recoveryWorker from './index-v8.js'", self.worker)

    def test_deep_email_auth_probe_is_truthful(self):
        self.assertIn("https://api.resend.com/domains", self.worker)
        self.assertIn("emailProviderAuth", self.worker)
        self.assertIn("invalid_api_key", self.worker)
        self.assertIn("user-agent':'pterminology-specialist-identity/10.0.0'", self.worker)

    def test_reset_links_are_single_use_and_supersede_older_links(self):
        self.assertIn("UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL", self.worker)
        self.assertIn("allSessionsRevoked:true", self.worker)
        self.assertIn("id<>? AND used_at IS NULL", self.worker)

    def test_reset_commit_is_batched(self):
        marker = "const results = await env.DB.batch(["
        self.assertIn(marker, self.worker)
        self.assertIn("reset_commit_failed", self.worker)

    def test_login_has_constant_time_dummy_path(self):
        self.assertIn("verifyPasswordConstantTime", self.worker)
        self.assertIn("dummy-login|", self.worker)

    def test_sessions_are_bound_to_user_agent(self):
        self.assertIn("session_binding_mismatch", self.worker)
        self.assertIn("user_agent_hash", self.worker)
        self.assertIn("SESSION_BIND_IP", self.worker)

    def test_admin_delivery_is_truthful_and_manual_fallback_exists(self):
        self.assertIn("/password-reset-link", self.worker)
        self.assertIn("manual_password_link_created", self.worker)
        self.assertIn("partialSuccess:true", self.worker)
        self.assertIn("email_service_unavailable", self.worker)

    def test_break_glass_export_requires_two_secrets(self):
        self.assertIn("x-recovery-export-key", self.worker)
        self.assertIn("RECOVERY_EXPORT_KEY", self.worker)
        self.assertIn("owner_recovery_exported", self.worker)

    def test_admin_ui_injects_owner_manual_reset_control(self):
        self.assertIn("إنشاء رابط يدوي", self.admin)
        self.assertIn("password-reset-link", self.admin)
        self.assertIn("navigator.clipboard.writeText", self.admin)
        self.assertIn("admin-recovery-v10.js?v=10.0.0", self.runtime)

    def test_production_workflow_exists(self):
        self.assertTrue(DEPLOY.exists())
        workflow = DEPLOY.read_text(encoding="utf-8")
        self.assertIn('main = "src/index-v10.js"', workflow)
        self.assertIn("node --check specialists-partners/account-backend/src/index-v10.js", workflow)
        self.assertIn("health?deep=1", workflow)
        self.assertIn("tests.test_specialist_identity_v10", workflow)


if __name__ == "__main__":
    unittest.main()
