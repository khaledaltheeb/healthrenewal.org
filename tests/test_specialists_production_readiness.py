import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'check-specialists-production-readiness.mjs'


def valid_env():
    return {
        'CLOUDFLARE_API_TOKEN': 'cf_' + 'a' * 40,
        'CLOUDFLARE_ACCOUNT_ID': 'a' * 32,
        'SPECIALISTS_D1_DATABASE_ID': '123e4567-e89b-42d3-a456-426614174000',
        'RESEND_API_KEY': 're_' + 'b' * 40,
        'TURNSTILE_SECRET': 'ts_' + 'c' * 40,
        'SPECIALISTS_ADMIN_API_KEY': 'd' * 40,
        'SPECIALISTS_RATE_LIMIT_SALT': 'e' * 40,
        'SPECIALISTS_REVIEW_LINK_SECRET': 'f' * 40,
        'SPECIALISTS_FROM_EMAIL': 'PTerminology <reviews@example.org>',
        'SPECIALISTS_OWNER_EMAIL': 'owner@example.org',
    }


def run_check(changes=None):
    env = os.environ.copy()
    env.update(valid_env())
    for key, value in (changes or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(['node', str(SCRIPT)], cwd=ROOT, env=env, text=True, capture_output=True)


class ProductionReadinessTests(unittest.TestCase):
    def test_valid_configuration_passes(self):
        result = run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])

    def test_missing_review_secret_fails(self):
        result = run_check({'SPECIALISTS_REVIEW_LINK_SECRET': None})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SPECIALISTS_REVIEW_LINK_SECRET: missing', result.stdout)

    def test_reused_secret_fails_without_printing_value(self):
        shared = 'z' * 40
        result = run_check({'SPECIALISTS_ADMIN_API_KEY': shared, 'SPECIALISTS_REVIEW_LINK_SECRET': shared})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be different', result.stdout)
        self.assertNotIn(shared, result.stdout)

    def test_invalid_identifiers_fail(self):
        result = run_check({'CLOUDFLARE_ACCOUNT_ID': 'bad', 'SPECIALISTS_D1_DATABASE_ID': 'bad'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CLOUDFLARE_ACCOUNT_ID', result.stdout)
        self.assertIn('SPECIALISTS_D1_DATABASE_ID', result.stdout)

    def test_workflow_places_gate_before_migration(self):
        workflow = (ROOT / '.github/workflows/deploy-specialists-signed-review-v6.yml').read_text(encoding='utf-8')
        gate = workflow.index('Validate production readiness without exposing values')
        migration = workflow.index('Apply D1 migrations')
        self.assertLess(gate, migration)
        self.assertIn('environment: specialists-production', workflow)
        self.assertNotIn('application-review-v6\',\n              hashlib.sha256', workflow)


if __name__ == '__main__':
    unittest.main()
