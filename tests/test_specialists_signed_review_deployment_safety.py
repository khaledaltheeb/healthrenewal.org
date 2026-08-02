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

    def test_secret_values_are_not_requested_or_printed(self):
        for name in (
            "RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}",
            "TURNSTILE_SECRET: ${{ secrets.TURNSTILE_SECRET }}",
            "ADMIN_API_KEY: ${{ secrets.SPECIALISTS_ADMIN_API_KEY }}",
            "RATE_LIMIT_SALT: ${{ secrets.SPECIALISTS_RATE_LIMIT_SALT }}",
            "REVIEW_LINK_SECRET: ${{ secrets.SPECIALISTS_REVIEW_LINK_SECRET }}",
        ):
            self.assertNotIn(name, self.text)
        self.assertIn("required_worker_secret_names_verified", self.text)

    def test_current_public_hosts_are_in_worker_configuration(self):
        self.assertIn(
            'ALLOWED_ORIGINS = "https://healthrenewal.org,https://www.healthrenewal.org,https://khaledaltheeb.github.io"',
            self.text,
        )
        self.assertIn(
            'TURNSTILE_EXPECTED_HOSTNAMES = "healthrenewal.org,www.healthrenewal.org,khaledaltheeb.github.io"',
            self.text,
        )

    def test_production_health_remains_required(self):
        self.assertIn("Verify live signed-review health", self.text)
        self.assertIn("assert health['version'] == '6.0.0'", self.text)
        for check in ("signedReviews", "signedReviewSchema", "signedReviewEmail"):
            self.assertIn(check, self.text)


if __name__ == "__main__":
    unittest.main()
