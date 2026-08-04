from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-specialists-signed-review-v6.yml"


class SpecialistsSignedReviewDeploymentSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_requires_independent_review_secret_to_exist_on_worker(self):
        self.assertIn("'REVIEW_LINK_SECRET'", self.text)
        self.assertIn("Missing required Worker secret names", self.text)
        self.assertNotIn("hmac.new", self.text)
        self.assertNotIn("application-review-v6',", self.text)

    def test_deployment_does_not_replace_worker_secret_set(self):
        self.assertIn("Deploy signed-review Worker v6 without replacing existing secrets", self.text)
        self.assertIn("wrangler@4 deploy --config wrangler.toml --minify --keep-vars", self.text)
        self.assertNotIn("--secrets-file", self.text)
        self.assertNotIn("worker-secrets.json", self.text)

    def test_secret_values_are_not_loaded_into_workflow_environment(self):
        for forbidden in (
            "RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}",
            "TURNSTILE_SECRET: ${{ secrets.TURNSTILE_SECRET }}",
            "ADMIN_API_KEY: ${{ secrets.SPECIALISTS_ADMIN_API_KEY }}",
            "REVIEWER_API_KEY: ${{ secrets.SPECIALISTS_REVIEWER_API_KEY }}",
            "MODERATOR_API_KEY: ${{ secrets.SPECIALISTS_MODERATOR_API_KEY }}",
            "RATE_LIMIT_SALT: ${{ secrets.SPECIALISTS_RATE_LIMIT_SALT }}",
            "REVIEW_LINK_SECRET: ${{ secrets.SPECIALISTS_REVIEW_LINK_SECRET }}",
        ):
            self.assertNotIn(forbidden, self.text)

    def test_cloudflare_preflight_checks_names_only(self):
        self.assertIn("/workers/scripts/${WORKER_NAME}/secrets", self.text)
        self.assertIn("required_worker_secret_names_verified", self.text)
        for required_name in (
            "'RESEND_API_KEY'",
            "'TURNSTILE_SECRET'",
            "'ADMIN_API_KEY'",
            "'REVIEWER_API_KEY'",
            "'MODERATOR_API_KEY'",
            "'RATE_LIMIT_SALT'",
            "'REVIEW_LINK_SECRET'",
        ):
            self.assertIn(required_name, self.text)

    def test_role_credentials_are_required_before_deployment(self):
        required_block = self.text.split("required={", 1)[1].split("}", 1)[0]
        self.assertIn("'REVIEWER_API_KEY'", required_block)
        self.assertIn("'MODERATOR_API_KEY'", required_block)
        deploy_position = self.text.index("Deploy signed-review Worker v6 without replacing existing secrets")
        preflight_position = self.text.index("Missing required Worker secret names")
        self.assertLess(preflight_position, deploy_position)

    def test_live_health_contract_remains_required(self):
        self.assertIn("Verify live signed-review health", self.text)
        self.assertIn("health['version'] == '6.0.0'", self.text)
        for check_name in ("'signedReviews'", "'signedReviewSchema'", "'signedReviewEmail'"):
            self.assertIn(check_name, self.text)


if __name__ == "__main__":
    unittest.main()
