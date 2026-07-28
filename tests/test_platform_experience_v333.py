from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "enhance_platform_experience_v333.py"
spec = importlib.util.spec_from_file_location("experience_v333", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def page(title: str, description: str = "وصف عربي مفيد", body: str = "محتوى عربي واضح") -> str:
    slug = mod.normalize_arabic(title).replace(" ", "-")
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
    <title>{title}</title><meta name="description" content="{description}">
    <link rel="canonical" href="{mod.SITE_BASE}terms/{slug}/"></head>
    <body><main><h1>{title}</h1><p>{body}</p></main></body></html>'''


class ExperienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / "index.html").write_text(page("المنصة الرئيسية"), encoding="utf-8")
        (self.site / "terms/anxiety").mkdir(parents=True)
        (self.site / "terms/anxiety/index.html").write_text(page("القلق النفسي", "شرح القلق والتوتر"), encoding="utf-8")
        (self.site / "assessment-lab/anxiety").mkdir(parents=True)
        (self.site / "assessment-lab/anxiety/index.html").write_text(page("مقياس القلق الاستكشافي"), encoding="utf-8")
        (self.site / "developers").mkdir(parents=True)
        (self.site / "developers/index.html").write_text(page("واجهة المطورين"), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_arabic_normalization(self) -> None:
        self.assertEqual(mod.normalize_arabic("فَرْطُ الحَرَكَة"), mod.normalize_arabic("فرط الحركه"))
        self.assertEqual(mod.normalize_arabic("إعاقة"), "اعاقه")

    def test_complete_generation(self) -> None:
        report = mod.run(self.site, strict=True, min_pages=2)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["coverage_ratio"], 1.0)
        index = json.loads((self.site / mod.SEARCH_API).read_text(encoding="utf-8"))
        self.assertGreaterEqual(index["count"], 3)
        self.assertTrue((self.site / "search/index.html").exists())
        self.assertTrue((self.site / "my-library/index.html").exists())
        self.assertTrue((self.site / mod.OPENAPI).exists())
        self.assertIn("platform-api-v333", (self.site / "developers/index.html").read_text(encoding="utf-8"))

    def test_assets_are_sitewide_and_idempotent(self) -> None:
        first = mod.run(self.site, strict=True, min_pages=2)
        second = mod.run(self.site, strict=True, min_pages=2)
        self.assertGreater(first["pages_updated"], 0)
        self.assertEqual(second["pages_updated"], 0)
        for path in self.site.rglob("*.html"):
            if path.name not in {"404.html", "offline.html", mod.VERIFY_FILE}:
                self.assertEqual(path.read_text(encoding="utf-8").count(mod.MARKER), 2)

    def test_privacy_and_result_storage_are_opt_in(self) -> None:
        script = mod.JS
        self.assertIn("data-save-result", script)
        self.assertIn("onclick", script)
        self.assertIn("لا تُحفظ إجابات", mod.library_page())
        self.assertNotIn("fetch(KEYS.results", script)
        self.assertIn("pterminology:assessment-result", script)

    def test_full_search_contract(self) -> None:
        mod.run(self.site, strict=True, min_pages=2)
        data = json.loads((self.site / mod.SEARCH_API).read_text(encoding="utf-8"))
        anxiety = next(item for item in data["items"] if "القلق" in item["title"])
        self.assertIn("القلق", anxiety["tokens"])
        self.assertTrue(anxiety["url"].startswith("https://"))
        self.assertIn("section", anxiety)

    def test_platform_json_is_merged(self) -> None:
        (self.site / "platform.json").write_text('{"legacy": true}', encoding="utf-8")
        mod.run(self.site, strict=True, min_pages=2)
        payload = json.loads((self.site / "platform.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["legacy"])
        self.assertEqual(payload["schema_version"], 333)
        self.assertIn("search_index", payload["endpoints"])


if __name__ == "__main__":
    unittest.main()
