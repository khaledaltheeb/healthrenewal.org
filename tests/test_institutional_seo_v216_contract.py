from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "upgrade_institutional_seo_v215.py").read_text(encoding="utf-8")


class InstitutionalSeoV216ContractTests(unittest.TestCase):
    def test_keywords_are_page_specific_and_bounded(self) -> None:
        for marker in (
            "core = re.split",
            "for match in re.finditer(r\"<h[12]",
            "SECTION_KEYWORDS",
            "if len(result) >= 12",
            '"مصطلحات علم النفس", "الصحة النفسية", "علم النفس بالعربي"',
        ):
            self.assertIn(marker, SCRIPT)
        self.assertIn("keyword_policy", SCRIPT)
        self.assertNotIn("keyword stuffing", SCRIPT.lower())

    def test_public_operational_copy_is_reported(self) -> None:
        for marker in (
            "OPERATIONAL_TOKENS",
            "operational_copy_pages",
            "operational_copy_examples",
            "built-not-published",
            "ما تم إنجازه",
            "ما سيتم إنجازه",
            "خطة العمل الحالية",
        ):
            self.assertIn(marker, SCRIPT)

    def test_no_banned_language_or_automatic_content_padding(self) -> None:
        self.assertNotRegex(SCRIPT, re.compile(r"معاق(?:ين|ون|ات)", re.I))
        self.assertNotIn("lorem ipsum", SCRIPT.lower())
        self.assertNotIn("while words <", SCRIPT)
        self.assertIn("content_expansion_required", SCRIPT)


if __name__ == "__main__":
    unittest.main()
