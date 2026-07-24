import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SitewideSeoVerifierDiagnosticsV216Tests(unittest.TestCase):
    def test_verifier_reports_exact_idempotency_paths(self):
        source = (ROOT / "scripts" / "verify_sitewide_seo_v216.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"idempotency_failures": sorted(set(idempotency_failures))[:300]',
            source,
        )
        self.assertIn(
            '"idempotency_failure_count": len(set(idempotency_failures))',
            source,
        )


if __name__ == "__main__":
    unittest.main()
