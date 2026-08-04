from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "dispatch-specialist-identity-on-message-v10.yml"


class SpecialistMessageV10DeploymentTriggerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_message_module_changes_trigger_production_dispatch(self):
        self.assertIn('specialists-partners/account-backend/src/specialist-message-v10.js', self.text)
        self.assertIn('deploy-specialist-identity-v10-production.yml/dispatches', self.text)
        self.assertIn('-d \'{"ref":"main"}\'', self.text)

    def test_dispatcher_uses_repository_token_without_loading_runtime_secrets(self):
        self.assertIn('actions: write', self.text)
        self.assertIn('GH_TOKEN: ${{ github.token }}', self.text)
        for forbidden in (
            'CLOUDFLARE_API_TOKEN',
            'RESEND_API_KEY',
            'TURNSTILE_SECRET',
            'ADMIN_API_KEY',
            'PASSWORD_PEPPER',
            'RATE_LIMIT_SALT',
        ):
            self.assertNotIn(forbidden, self.text)

    def test_dispatch_is_serialized_and_does_not_cancel_active_deployments(self):
        self.assertIn('cancel-in-progress: false', self.text)
        self.assertIn('timeout-minutes: 5', self.text)


if __name__ == "__main__":
    unittest.main()
