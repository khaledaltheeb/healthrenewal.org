from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HomepageModernSeoContractTests(unittest.TestCase):
    def test_homepage_and_production_builder_use_modern_semantic_seo(self) -> None:
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        publisher = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(encoding="utf-8")

        self.assertIsNone(
            re.search(r'<meta\b[^>]*\bname=["\']keywords["\']', homepage, re.IGNORECASE),
            "The homepage must not restore the obsolete meta keywords field.",
        )
        required_block = publisher.split("required = [", 1)[1].split("]", 1)[0]
        self.assertNotIn('name="keywords"', required_block)
        self.assertIn('property="og:image"', required_block)
        self.assertIn('name="twitter:image"', required_block)
        self.assertIn('application/ld+json', required_block)

        self.assertEqual(1, len(re.findall(r"<h1\b", homepage)))
        self.assertGreaterEqual(len(re.findall(r"<h2\b", homepage)), 4)
        self.assertGreaterEqual(len(re.findall(r"<h3\b", homepage)), 1)
        self.assertIn("if h3_count < 1:", publisher)
        self.assertNotIn("if h3_count < 16:", publisher)


if __name__ == "__main__":
    unittest.main()
