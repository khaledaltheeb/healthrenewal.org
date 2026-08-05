from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / ".github" / "workflows" / "dispatch-specialist-identity-on-message-v10.yml"
VALIDATE = ROOT / ".github" / "workflows" / "validate-specialist-message-v10-deployment-trigger.yml"


class SpecialistMessageV10DeploymentTriggerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dispatch = DISPATCH.read_text(encoding="utf-8")
        cls.validate = VALIDATE.read_text(encoding="utf-8")

    def test_message_module_changes_trigger_production_dispatch(self):
        self.assertIn('specialists-partners/account-backend/src/specialist-message-v10.js', self.dispatch)
        self.assertIn('specialists-partners/account-backend/migrations/**', self.dispatch)
        self.assertIn('deploy-specialist-identity-v10-production.yml/dispatches', self.dispatch)
        self.assertIn('-d \'{"ref":"main"}\'', self.dispatch)

    def test_dispatcher_uses_repository_token_without_runtime_secrets(self):
        self.assertIn('actions: write', self.dispatch)
        self.assertIn('contents: read', self.dispatch)
        self.assertIn('GH_TOKEN: ${{ github.token }}', self.dispatch)
        for forbidden in (
            'CLOUDFLARE_API_TOKEN', 'RESEND_API_KEY', 'TURNSTILE_SECRET',
            'ADMIN_API_KEY', 'PASSWORD_PEPPER', 'RATE_LIMIT_SALT',
        ):
            self.assertNotIn(forbidden, self.dispatch)

    def test_dispatch_is_serialized_without_cancelling_active_deployments(self):
        self.assertIn('cancel-in-progress: false', self.dispatch)
        self.assertIn('timeout-minutes: 5', self.dispatch)

    def test_pull_request_validation_executes_this_contract(self):
        self.assertIn('pull_request:', self.validate)
        self.assertIn('tests/test_specialist_message_v10_deployment_trigger.py', self.validate)
        self.assertIn('python -m unittest -v tests.test_specialist_message_v10_deployment_trigger', self.validate)
        self.assertNotIn('secrets.', self.validate)


if __name__ == "__main__":
    unittest.main()
