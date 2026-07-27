from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_sectors_portal_v327 import MIN_VISIBLE_WORDS, validate  # noqa: E402


class SectorsPortalV327Tests(unittest.TestCase):
    portal = ROOT / "sectors" / "index.html"

    def test_current_portal_passes_contract(self) -> None:
        report = validate(self.portal)
        self.assertEqual(report["status"], "passed", report)
        self.assertGreaterEqual(report["visible_words"], MIN_VISIBLE_WORDS)
        self.assertEqual(report["h1"], 1)
        self.assertGreaterEqual(report["faq_items"], 5)
        self.assertEqual(report["external_source_links"], 4)
        self.assertFalse(report["duplicate_ids"])
        for count in report["sector_link_counts"].values():
            self.assertGreaterEqual(count, 2)

    def _validate_mutation(self, old: str, new: str) -> dict[str, object]:
        source = self.portal.read_text(encoding="utf-8")
        self.assertIn(old, source)
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "index.html"
            candidate.write_text(source.replace(old, new, 1), encoding="utf-8")
            return validate(candidate)

    def test_rejects_loss_of_urgent_safety_boundary(self) -> None:
        report = self._validate_mutation(
            "عند وجود خطر مباشر لا تبدأ بالتصفح",
            "تنبيه عام",
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(
            any("required safety/method marker missing" in error for error in report["errors"]),
            report,
        )

    def test_rejects_duplicate_structural_id(self) -> None:
        report = self._validate_mutation(
            'id="faq"',
            'id="method"',
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("method", report["duplicate_ids"])

    def test_rejects_invalid_or_incomplete_schema(self) -> None:
        report = self._validate_mutation(
            '"@type":"FAQPage"',
            '"@type":"WebPage"',
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("missing schema types" in error for error in report["errors"]), report)


if __name__ == "__main__":
    unittest.main()
