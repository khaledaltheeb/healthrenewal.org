from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from tests.test_practical_tips_v237 import PracticalTipsV237Tests, module


REQUIRED_HEADINGS = (
    "جملة جاهزة للاستخدام",
    "كيف تعرف أن الخطة تتحسن؟",
    "متى تحتاج إلى مساعدة؟",
    "مصادر موثوقة للتوسع",
)


class PracticalTipsCoreCompatibilityV244Tests(unittest.TestCase):
    def test_all_guides_satisfy_the_legacy_core_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture = PracticalTipsV237Tests()
            repo, site = fixture.make_fixture(Path(temporary_directory))
            report = module.publish(site, repo)

            pages = sorted((site / "tips").glob("*/index.html"))
            self.assertEqual(len(pages), 100)
            self.assertEqual(report["core_sections_compatibility"], "passed")
            self.assertEqual(report["compatibility_pages"], 100)
            self.assertEqual(report["unique_titles"], 100)
            self.assertEqual(report["unique_descriptions"], 100)

            titles: set[str] = set()
            descriptions: set[str] = set()
            for page in pages:
                source = page.read_text(encoding="utf-8")
                self.assertEqual(source.count("practical-tips-v237-core-compat:start"), 1, page)
                self.assertEqual(source.count("practical-tips-v237-core-compat:end"), 1, page)
                for heading in REQUIRED_HEADINGS:
                    self.assertIn(heading, source, page)
                self.assertGreaterEqual(len(re.findall(r"<li\b", source, flags=re.I)), 6, page)

                title = re.search(r"<title\b[^>]*>(.*?)</title\s*>", source, flags=re.I | re.S)
                description = re.search(
                    r"<meta\b(?=[^>]*\bname=[\"']description[\"'])[^>]*\bcontent=[\"']([^\"']+)[\"'][^>]*>",
                    source,
                    flags=re.I | re.S,
                )
                self.assertIsNotNone(title, page)
                self.assertIsNotNone(description, page)
                titles.add(re.sub(r"\s+", " ", title.group(1)).strip())
                descriptions.add(re.sub(r"\s+", " ", description.group(1)).strip())

            self.assertEqual(len(titles), 100)
            self.assertEqual(len(descriptions), 100)

    def test_compatibility_layer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture = PracticalTipsV237Tests()
            repo, site = fixture.make_fixture(Path(temporary_directory))
            module.publish(site, repo)
            module.publish(site, repo)
            for page in (site / "tips").glob("*/index.html"):
                source = page.read_text(encoding="utf-8")
                self.assertEqual(source.count("practical-tips-v237-core-compat:start"), 1, page)
                self.assertEqual(source.count("practical-tips-v237-core-compat:end"), 1, page)


if __name__ == "__main__":
    unittest.main()
