import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKER = ROOT / "specialists-partners/account-backend/src/index-v10.js"
FINAL_WORKER = ROOT / "specialists-partners/account-backend/src/index-v10-final.js"
PRODUCTION_WORKER = ROOT / "specialists-partners/account-backend/src/index-v10-production.js"
PROPAGATION = ROOT / "scripts/verify_specialist_identity_v10_production.py"
ADMIN_RECOVERY = ROOT / "specialists-partners/admin/admin-recovery-v10-final.js"
ADMIN_PROVIDER = ROOT / "specialists-partners/admin/admin-provider-status-v10.js"
RUNTIME = ROOT / "specialists-partners/assets/runtime-config.js"
RECOVER_HTML = ROOT / "specialists-partners/recover/index.html"
RECOVER_SCRIPT = ROOT / "specialists-partners/recover/recover.js"
RESET_HTML = ROOT / "specialists-partners/password-reset/index.html"
RESET_SCRIPT = ROOT / "specialists-partners/password-reset/reset-v10.js"
VALIDATE = ROOT / ".github/workflows/deploy-specialist-identity-v10.yml"
DEPLOY = ROOT / ".github/workflows/deploy-specialist-identity-v10-production.yml"
PAGES = ROOT / ".github/workflows/deploy-specialist-recovery-pages-v8.yml"
LEGACY_V6 = ROOT / ".github/workflows/deploy-specialists-account-backend.yml"
LEGACY_V8 = ROOT / ".github/workflows/deploy-specialist-recovery-overlay-v8.yml"
LEGACY_DELIVERY = ROOT / ".github/workflows/verify-specialist-recovery-v8.yml"


class SpecialistIdentityV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = WORKER.read_text(encoding="utf-8")
        cls.final_worker = FINAL_WORKER.read_text(encoding="utf-8")
        cls.production_worker = PRODUCTION_WORKER.read_text(encoding="utf-8")
        cls.propagation = PROPAGATION.read_text(encoding="utf-8")
        cls.admin = ADMIN_RECOVERY.read_text(encoding="utf-8")
        cls.admin_provider = ADMIN_PROVIDER.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.recover_html = RECOVER_HTML.read_text(encoding="utf-8")
        cls.recover_script = RECOVER_SCRIPT.read_text(encoding="utf-8")
        cls.reset_html = RESET_HTML.read_text(encoding="utf-8")
        cls.reset_script = RESET_SCRIPT.read_text(encoding="utf-8")

    def test_worker_uses_layered_v10_release(self):
        self.assertIn("const BUILD_VERSION = '10.0.0'", self.worker)
        self.assertIn("import recoveryWorker from './index-v8.js'", self.worker)
        self.assertIn("const BUILD_VERSION = '10.1.0'", self.final_worker)
        self.assertIn("import identityWorker from './index-v10.js'", self.final_worker)
        self.assertIn("const BUILD_VERSION = '10.3.0'", self.production_worker)
        self.assertIn("import finalWorker from './index-v10-final.js'", self.production_worker)

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
        self.assertIn("const results = await env.DB.batch([", self.worker)
        self.assertIn("reset_commit_failed", self.worker)

    def test_login_has_constant_time_dummy_path(self):
        self.assertIn("verifyPasswordConstantTime", self.worker)
        self.assertIn("dummy-login|", self.worker)

    def test_sessions_are_bound_to_user_agent(self):
        self.assertIn("session_binding_mismatch", self.worker)
        self.assertIn("user_agent_hash", self.worker)
        self.assertIn("SESSION_BIND_IP", self.worker)
        self.assertIn("session_binding_mismatch", self.final_worker)

    def test_admin_delivery_is_truthful_and_manual_fallback_exists(self):
        self.assertIn("/password-reset-link", self.worker)
        self.assertIn("manual_password_link_created", self.worker)
        self.assertIn("partialSuccess:true", self.worker)
        self.assertIn("email_service_unavailable", self.worker)

    def test_break_glass_export_requires_two_secrets(self):
        self.assertIn("x-recovery-export-key", self.worker)
        self.assertIn("RECOVERY_EXPORT_KEY", self.worker)
        self.assertIn("owner_recovery_exported", self.worker)

    def test_final_worker_unifies_password_and_preflight_contracts(self):
        self.assertIn("request.method === 'OPTIONS'", self.final_worker)
        self.assertIn("strictPasswordPolicy:true", self.final_worker)
        self.assertIn("accountPasswordPolicy:true", self.final_worker)
        self.assertIn("password_reuse", self.final_worker)
        self.assertIn("resetLinksRevoked:true", self.final_worker)
        self.assertIn("/\\p{L}/u", self.final_worker)
        self.assertNotIn("/\\s/u.test(password)", self.final_worker)

    def test_production_wrapper_guarantees_cors_and_safe_errors(self):
        self.assertIn("request.method === 'OPTIONS'", self.production_worker)
        self.assertIn("return new Response(null, {status:204, headers:cors})", self.production_worker)
        self.assertIn("ensureCors(response, origin, env)", self.production_worker)
        self.assertIn("'cross-origin-resource-policy':'cross-origin'", self.production_worker)
        self.assertIn("specialist_identity_v103_production_error", self.production_worker)
        self.assertIn("corsPreflight:true", self.production_worker)

    def test_recovery_pages_allow_both_worker_hosts(self):
        identity = "https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev"
        core = "https://pterminology-specialists.pterminology-826ac349.workers.dev"
        for page in (self.recover_html, self.reset_html):
            self.assertIn(identity, page)
            self.assertIn(core, page)
        self.assertIn("recover.js?v=10.3.0", self.recover_html)
        self.assertIn("reset-v10.js?v=10.3.0", self.reset_html)

    def test_recovery_network_failures_are_bounded_and_actionable(self):
        for script in (self.recover_script, self.reset_script):
            self.assertIn("AbortController", script)
            self.assertIn("mode: 'cors'", script)
            self.assertIn("redirect: 'follow'", script)
            self.assertNotIn("redirect: 'error'", script)
            self.assertIn("all_account_endpoints_unavailable", script)
            self.assertIn("CORE_API", script)
        self.assertNotIn("Failed to fetch", self.recover_script + self.reset_script)

    def test_deep_health_is_protected_and_admin_status_is_authenticated(self):
        self.assertIn("bootstrapAuthorized(request, env)", self.production_worker)
        self.assertIn("/v1/admin/email-provider-status", self.production_worker)
        self.assertIn("['owner','admin']", self.production_worker)
        self.assertIn("protectedDeepHealth:true", self.production_worker)
        self.assertIn("authorization:`Bearer ${value.token}`", self.admin_provider)
        self.assertNotIn("/health?deep=1", self.admin_provider)

    def test_admin_ui_activates_after_dynamic_load_and_login(self):
        self.assertIn("إنشاء رابط يدوي", self.admin)
        self.assertIn("password-reset-link", self.admin)
        self.assertIn("navigator.clipboard.writeText", self.admin)
        self.assertIn("document.readyState==='loading'", self.admin)
        self.assertIn("attributeFilter:['hidden']", self.admin)
        self.assertIn("admin-recovery-v10-final.js?v=10.3.0", self.runtime)
        self.assertIn("admin-provider-status-v10.js?v=10.3.0", self.runtime)
        self.assertIn('identityVersion: "10.3.0"', self.runtime)

    def test_propagation_verifier_requires_atomic_stability(self):
        self.assertIn("for attempt in range(1, 241)", self.propagation)
        self.assertIn("normal_ok(normal_status, normal)", self.propagation)
        self.assertIn("public_deep_ok(public_status, public)", self.propagation)
        self.assertIn("protected_deep_ok(deep_status, deep)", self.propagation)
        self.assertIn("if stable >= 3", self.propagation)
        self.assertIn("x-bootstrap-key", self.propagation)
        self.assertIn("/tmp/identity-health.json", self.propagation)
        self.assertIn("/tmp/identity-deep-health.json", self.propagation)

    def test_validation_and_production_workflows_are_separated(self):
        self.assertTrue(VALIDATE.exists())
        self.assertTrue(DEPLOY.exists())
        validation = VALIDATE.read_text(encoding="utf-8")
        production = DEPLOY.read_text(encoding="utf-8")
        self.assertNotIn("wrangler@4 deploy", validation)
        self.assertNotIn("push:\n    branches", validation)
        self.assertIn('main = "src/index-v10-production.js"', production)
        self.assertIn("node --check specialists-partners/account-backend/src/index-v10-production.js", production)
        self.assertIn("verify_specialist_identity_v10_production.py", production)
        self.assertIn("stable_contract_cycles", production)
        self.assertIn("Deep health must not be public", production)
        self.assertIn("/workers/scripts/pterminology-specialist-accounts/subdomain", production)
        self.assertIn('"enabled":true,"previews_enabled":true', production)
        self.assertIn("tests.test_specialist_identity_v10", production)
        self.assertIn("specialist-identity-v10-production.json", production)

    def test_pages_deployment_patches_and_verifies_complete_interface(self):
        self.assertTrue(PAGES.exists())
        pages = PAGES.read_text(encoding="utf-8")
        for path in (
            "specialists-partners/admin/admin-recovery-v10-final.js",
            "specialists-partners/admin/admin-provider-status-v10.js",
            "specialists-partners/assets/runtime-config.js",
            "specialists-partners/recover/index.html",
            "specialists-partners/recover/recover.js",
            "specialists-partners/password-reset/index.html",
            "specialists-partners/password-reset/reset-v10.js",
        ):
            self.assertIn(path, pages)
        self.assertIn("Patch complete specialist identity interface", pages)
        self.assertIn("Verify live specialist identity interface", pages)
        self.assertIn("specialist-identity-v10-pages.json", pages)
        self.assertIn("admin-provider-status-v10.js?v=10.3.0", pages)
        self.assertIn("recover.js?v=10.3.0", pages)
        self.assertIn("reset-v10.js?v=10.3.0", pages)
        self.assertIn("recovery_dual_endpoint_csp", pages)

    def test_legacy_workflows_are_validation_only_and_never_issue_links(self):
        for path in (LEGACY_V6, LEGACY_V8):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("wrangler@4 deploy", text)
            self.assertNotIn("push:\n    branches", text)
            self.assertIn("validation-only", text)
        delivery = LEGACY_DELIVERY.read_text(encoding="utf-8")
        self.assertNotIn("owner-password-reset", delivery)
        self.assertNotIn("providerMessageId", delivery)
        self.assertNotIn("-X POST", delivery)
        self.assertIn("without creating a reset token or sending email", delivery)


if __name__ == "__main__":
    unittest.main()
