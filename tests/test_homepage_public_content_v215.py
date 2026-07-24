from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "index.html"
LOGO = ROOT / "assets" / "brand" / "logo-mark.svg"
SOCIAL_CARD = ROOT / "assets" / "brand" / "social-card.svg"
TAXONOMY = ROOT / "content" / "seo" / "keyword-taxonomy-v215.json"


class HomepagePublicContentV215Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = HOME.read_text(encoding="utf-8")
        cls.taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))

    def test_internal_execution_language_is_not_public(self) -> None:
        for phrase in self.taxonomy["forbidden_public_phrases"]:
            self.assertNotIn(phrase, self.text)
        self.assertNotIn("مسار مستقبلي للحسابات المؤسسية", self.text)
        self.assertNotIn("لا نشر قبل البوابات", self.text)

    def test_homepage_has_institutional_information_architecture(self) -> None:
        self.assertEqual(len(re.findall(r"<h1\b", self.text)), 1)
        self.assertGreaterEqual(len(re.findall(r"<h2\b", self.text)), 5)
        self.assertGreaterEqual(len(re.findall(r"<h3\b", self.text)), 16)
        for route in ("encyclopedia/", "special-needs/", "care-guides/", "assessment-lab/", "cognitive-lab/", "api/", "developers/"):
            self.assertIn(f'href="{route}"', self.text)

    def test_semantic_seo_replaces_keyword_stuffing(self) -> None:
        match = re.search(r'<meta name="keywords" content="([^"]+)">', self.text)
        self.assertIsNotNone(match)
        keywords = [item.strip() for item in match.group(1).split(",") if item.strip()]
        self.assertLessEqual(len(keywords), self.taxonomy["policy"]["maximum_meta_keywords"])
        self.assertIn('"keywords":[', self.text)
        self.assertIn('"about":[', self.text)
        self.assertIn('"@type":"FAQPage"', self.text)
        self.assertIn('rel="alternate" hreflang="ar"', self.text)
        self.assertIn('rel="alternate" hreflang="x-default"', self.text)
        self.assertIn('property="og:image"', self.text)
        self.assertIn('name="twitter:image"', self.text)

    def test_brand_assets_exist_and_are_referenced(self) -> None:
        self.assertTrue(LOGO.is_file())
        self.assertTrue(SOCIAL_CARD.is_file())
        self.assertIn("assets/brand/logo-mark.svg", self.text)
        self.assertIn("assets/brand/social-card.svg", self.text)

    def test_inclusive_language_contract(self) -> None:
        self.assertNotIn("معاقين", self.text)
        self.assertIn("ذوي الاحتياجات الخاصة", self.text)


if __name__ == "__main__":
    unittest.main()
