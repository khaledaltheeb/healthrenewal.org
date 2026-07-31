from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "sections" / "index.html"
BANNED = re.compile(r"\bمعاق(?:ون|ين)?\b")


class SectionsDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_page_exists_and_has_one_primary_heading(self) -> None:
        self.assertTrue(PAGE.is_file())
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn("دليل جميع الأقسام", self.html)

    def test_metadata_and_structured_data(self) -> None:
        self.assertIn(
            'rel="canonical" href="https://healthrenewal.org/sections/"',
            self.html,
        )
        self.assertIn('data-sections-directory="v1"', self.html)
        self.assertIn('"@type":"CollectionPage"', self.html)
        self.assertIn('"@type":"BreadcrumbList"', self.html)
        self.assertIn('"@type":"ItemList"', self.html)

        match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            self.html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        json.loads(match.group(1))

    def test_core_sections_are_linked(self) -> None:
        required_links = {
            "../start-here/",
            "../encyclopedia/",
            "../special-needs/",
            "../library/",
            "../magazine/",
            "../care-guides/",
            "../daily-tools/",
            "../learning-paths/",
            "../sectors/",
            "../specialists-partners/",
            "../platform/",
            "../trust/",
        }
        for href in required_links:
            self.assertIn(f'href="{href}"', self.html)

    def test_respectful_terminology_and_safety_boundary(self) -> None:
        self.assertIsNone(BANNED.search(self.html))
        self.assertIn("لا يثبت تشخيصًا", self.html)
        self.assertIn("الموافقة الكتابية", self.html)


if __name__ == "__main__":
    unittest.main()
