import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-specialists-production-readiness.mjs"


def valid_env():
    return {
        "CLOUDFLARE_API_TOKEN": "cf-token-production-value",
        "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
        "SPECIALISTS_D1_DATABASE_ID": "123e4567-e89b-42d3-a456-426614174000",
        "RESEND_API_KEY": "re_production_value",
        "TURNSTILE_SECRET": "turnstile-production-value",
        "SPECIALISTS_ADMIN_API_KEY": "A" * 40,
        "SPECIALISTS_REVIEWER_API_KEY": "B" * 40,
        "SPECIALISTS_MODERATOR_API_KEY": "C" * 40,
        "SPECIALISTS_RATE_LIMIT_SALT": "D" * 40,
        "SPECIALISTS_REVIEW_LINK_SECRET": "E" * 40,
        "SPECIALISTS_FROM_EMAIL": "PTerminology <reviews@example.org>",
        "SPECIALISTS_OWNER_EMAIL": "owner@example.org",
    }


def run_validator(overrides=None, remove=None):
    env = os.environ.copy()
    env.update(valid_env())
    env.update(overrides or {})
    for name in remove or []:
        env.pop(name, None)
    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, json.loads(result.stdout)


class SpecialistsProductionReadinessTests(unittest.TestCase):
    def test_valid_configuration_passes_without_echoing_values(self):
        result, payload = run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["requiredConfigured"], payload["requiredTotal"])
        self.assertNotIn("cf-token-production-value", result.stdout)
        self.assertNotIn("owner@example.org", result.stdout)

    def test_missing_required_secret_fails_by_name_only(self):
        result, payload = run_validator(remove=["SPECIALISTS_REVIEW_LINK_SECRET"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPECIALISTS_REVIEW_LINK_SECRET: missing", payload["errors"])

    def test_reused_security_material_is_rejected(self):
        result, payload = run_validator(
            {"SPECIALISTS_REVIEW_LINK_SECRET": "D" * 40}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("must be different" in item for item in payload["errors"]))

    def test_placeholder_and_invalid_identifiers_are_rejected(self):
        result, payload = run_validator(
            {
                "CLOUDFLARE_ACCOUNT_ID": "example",
                "SPECIALISTS_D1_DATABASE_ID": "not-a-uuid",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("CLOUDFLARE_ACCOUNT_ID" in item for item in payload["errors"]))
        self.assertTrue(any("SPECIALISTS_D1_DATABASE_ID" in item for item in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
