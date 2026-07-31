import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v191" / "source-citation-guide-ar.json"
SCRIPT = ROOT / "scripts" / "publish_source_citation_guide_v191.py"

spec = importlib.util.spec_from_file_location("source_citation_v191", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class SourceCitationGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTENT.read_text(encoding="utf-8"))

    def test_content_depth_and_limits(self):
        self.assertEqual(self.data["status"], "internally-reviewed")
        self.assertEqual(self.data["risk_level"], "low")
        self.assertGreaterEqual(len(self.data["sections"]), 8)
        self.assertGreaterEqual(len(self.data["checklist"]), 10)
        self.assertGreaterEqual(len(self.data["examples"]), 6)
        text = json.dumps(self.data, ensure_ascii=False)
        for marker in ["الادعاء", "المصدر الأولي", "تاريخ التحقق", "dateModified", "حالة المراجعة", "canonical", "built-not-published"]:
            self.assertIn(marker, text)

    def test_sources_follow_contract(self):
        sources = self.data["sources"]
        self.assertGreaterEqual(len(sources), 3)
        self.assertEqual(len({item["id"] for item in sources}), len(sources))
        self.assertEqual(len({item["url"] for item in sources}), len(sources))
        for source in sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertEqual(source["source_type"], "official_guideline")
            self.assertEqual(source["status"], "current")
            self.assertIsInstance(source["year"], int)
            self.assertRegex(source["verified_at"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(source["claims_supported"])

    def test_render_and_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            for relative in ["encyclopedia/index.html", "blog/index.html", "trust/index.html"]:
                path = site / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<html lang="ar" dir="rtl"><main><h1>قسم</h1></main></html>', encoding="utf-8")
            output = module.publish(site)
            page = output.read_text(encoding="utf-8")
            self.assertEqual(page.count("<h1>"), 1)
            for marker in ['rel="canonical"', 'name="robots" content="index,follow"', 'property="og:title"', 'name="twitter:card"', '"@type": "Article"', '"@type": "BreadcrumbList"', '"citation"', ':focus-visible', '@media print']:
                self.assertIn(marker, page)
            href = "/guides/source-citation-and-update-transparency/"
            for relative in ["encyclopedia/index.html", "blog/index.html", "trust/index.html"]:
                self.assertIn(href, (site / relative).read_text(encoding="utf-8"))
            canonical = "https://healthrenewal.org" + href
            self.assertEqual((site / module.SITEMAP_NAME).read_text(encoding="utf-8").count(canonical), 1)

    def test_idempotence_and_unpublished_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            hub = site / "encyclopedia" / "index.html"
            hub.parent.mkdir(parents=True)
            hub.write_text('<html lang="ar" dir="rtl"><main></main></html>', encoding="utf-8")
            module.publish(site)
            first = hub.read_text(encoding="utf-8")
            first_map = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            module.publish(site)
            self.assertEqual(first, hub.read_text(encoding="utf-8"))
            self.assertEqual(first_map, (site / module.SITEMAP_NAME).read_text(encoding="utf-8"))
            report = json.loads((site / "api" / "source-citation-guide-v191.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")


if __name__ == "__main__":
    unittest.main()
