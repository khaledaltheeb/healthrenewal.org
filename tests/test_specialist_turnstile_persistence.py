import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/deploy-specialist-identity-v10-production.yml"
VERIFIER = ROOT / "scripts/verify_specialist_identity_v10_production.py"


class SpecialistTurnstilePersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.verifier = VERIFIER.read_text(encoding="utf-8")

    def test_deploy_does_not_replace_omitted_worker_secrets(self):
        self.assertNotIn("--secrets-file", self.workflow)
        self.assertNotIn("worker-secrets-v10-production.json", self.workflow)
        self.assertIn("without replacing existing secrets", self.workflow)
        self.assertIn("preserve TURNSTILE_SECRET", self.workflow)
        self.assertIn('for name in RESEND_API_KEY ADMIN_API_KEY RATE_LIMIT_SALT PASSWORD_PEPPER REVIEWER_API_KEY MODERATOR_API_KEY', self.workflow)
        self.assertNotIn('secret put TURNSTILE_SECRET', self.workflow)

    def test_health_verifier_identifies_itself(self):
        self.assertIn('PROBE_USER_AGENT = "pterminology-specialist-deploy-verifier/10.2"', self.verifier)
        self.assertIn('"user-agent": PROBE_USER_AGENT', self.verifier)
        self.assertIn('"pragma": "no-cache"', self.verifier)


if __name__ == "__main__":
    unittest.main()
