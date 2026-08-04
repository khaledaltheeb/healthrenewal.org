from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "materialize_sectors_v10_compat_v2.py"
SPEC = importlib.util.spec_from_file_location("materialize_sectors_v10_compat_v2", SCRIPT_PATH)
assert SPEC and SPEC.loader
compat = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compat
SPEC.loader.exec_module(compat)


class MaterializeSectorsV10CompatTests(unittest.TestCase):
    def test_normalizes_structured_reference_records(self) -> None:
        payload = {
            "sources": [
                {
                    "publisher": "World Health Organization",
                    "title": "Official guidance",
                    "url": "https://www.who.int/example",
                },
                {"title": "NICE guidance", "href": "https://www.nice.org.uk/example"},
            ],
            "articles": [],
        }
        compat.normalize_payload(payload)
        self.assertEqual(
            payload["sources"][0]["name"],
            "World Health Organization — Official guidance",
        )
        self.assertEqual(payload["sources"][1]["name"], "NICE guidance")
        self.assertEqual(payload["sources"][1]["url"], "https://www.nice.org.uk/example")

    def test_normalizes_comparison_article_without_fabricating_claims(self) -> None:
        payload = {
            "sources": [],
            "articles": [
                {
                    "title": "مقارنة عملية",
                    "comparison_axes": [
                        {"axis": "السياق", "first": "وصف أول", "second": "وصف ثان"},
                        {"axis": "المدة", "first": "مدة أولى", "second": "مدة ثانية"},
                        {"axis": "الأثر", "first": "أثر أول", "second": "أثر ثان"},
                    ],
                }
            ],
        }
        compat.normalize_payload(payload)
        article = payload["articles"][0]
        self.assertEqual(len(article["signals"]), 3)
        self.assertIn("السياق", article["signals"][0])
        self.assertEqual(len(article["phrases"]), 2)
        self.assertIn("لن نحسم", article["phrases"][0])

    def test_preserves_official_legal_term_but_rejects_prohibited_word(self) -> None:
        self.assertNotIn("ذوي الإعاقة", compat.base.UNWANTED_TERMS)
        self.assertIn("معاقين", compat.base.UNWANTED_TERMS)
        self.assertIn("المعاقين", compat.base.UNWANTED_TERMS)


if __name__ == "__main__":
    unittest.main()
