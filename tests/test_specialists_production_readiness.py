import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'check-specialists-production-readiness.mjs'


def valid_env():
    return {
        'CLOUDFLARE_API_TOKEN': 'cf_live_A7x9Q2m4N6p8R1t3V5w7Y9z2B4d6F8h0',
        'CLOUDFLARE_ACCOUNT_ID': 'a1b2c3d4e5f60718293a4b5c6d7e8f90',
        'SPECIALISTS_D1_DATABASE_ID': '123e4567-e89b-42d3-a456-426614174000',
        'RESEND_API_KEY': 're_live_B8y1P3k5M7q9S2u4W6x8Z1c3E5g7J9l2',
        'TURNSTILE_SECRET': 'ts_live_C9z2R4m6N8p1T3v5X7y9A2d4F6h8K1n3',
        'SPECIALISTS_ADMIN_API_KEY': 'adm_D7q2L9x4C1v8M5p3R6t0Y2k7N4s9W1f5',
        'SPECIALISTS_RATE_LIMIT_SALT': 'salt_H3m8Q1z6B4n9T2x7K5p0V3c8F1r6Y4d9',
        'SPECIALISTS_REVIEW_LINK_SECRET': 'review_J5v0N7q2D9x4L1m8S6p3C5t0W7k2R9y4',
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
    result = subprocess.run(
        ['node', str(SCRIPT)], cwd=ROOT, env=env,
        capture_output=True, text=True, check=False,
    )
    payload = json.loads(result.stdout)
    return result, payload


class SpecialistsProductionReadinessTests(unittest.TestCase):
    def test_valid_configuration_passes(self):
        result, payload = run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['requiredConfigured'], payload['requiredTotal'])

    def test_missing_required_secret_fails(self):
        result, payload = run_check({'SPECIALISTS_REVIEW_LINK_SECRET': None})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SPECIALISTS_REVIEW_LINK_SECRET: missing', payload['errors'])

    def test_reused_sensitive_secret_fails(self):
        shared = valid_env()['SPECIALISTS_ADMIN_API_KEY']
        result, payload = run_check({'SPECIALISTS_REVIEW_LINK_SECRET': shared})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any('must be different' in item for item in payload['errors']))

    def test_repeated_character_secret_fails(self):
        result, payload = run_check({'SPECIALISTS_ADMIN_API_KEY': 'a' * 40})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any('character diversity' in item or 'repeated-character' in item for item in payload['errors']))

    def test_predictable_sequence_fails(self):
        weak = 'prefix_abcdefghijklmnopqrstuvwxyz_1234567890'
        result, payload = run_check({'SPECIALISTS_RATE_LIMIT_SALT': weak})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any('predictable sequence' in item for item in payload['errors']))

    def test_invalid_identifiers_fail(self):
        result, payload = run_check({
            'CLOUDFLARE_ACCOUNT_ID': 'bad',
            'SPECIALISTS_D1_DATABASE_ID': 'bad',
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any('CLOUDFLARE_ACCOUNT_ID' in item for item in payload['errors']))
        self.assertTrue(any('SPECIALISTS_D1_DATABASE_ID' in item for item in payload['errors']))

    def test_output_never_contains_secret_values(self):
        env = valid_env()
        result, _ = run_check()
        for name in (
            'SPECIALISTS_ADMIN_API_KEY',
            'SPECIALISTS_RATE_LIMIT_SALT',
            'SPECIALISTS_REVIEW_LINK_SECRET',
        ):
            self.assertNotIn(env[name], result.stdout)
            self.assertNotIn(env[name], result.stderr)


if __name__ == '__main__':
    unittest.main()
