from __future__ import annotations

import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_adjustment_disorder_v335.py"
spec = importlib.util.spec_from_file_location("adjustment_disorder_v335", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AdjustmentDisorderPublisherTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        (root / "encyclopedia").mkdir(parents=True)
        (root / "encyclopedia" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>الموسوعة</h1></main></body></html>',
            encoding="utf-8",
        )
        (root / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )

    def test_publish_creates_complete_indexed_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self.fixture(site)
            report = module.publish(site)
            page = site / "encyclopedia" / "adjustment-disorder" / "index.html"
            text = page.read_text(encoding="utf-8")
            self.assertEqual(report["version"], 335)
            self.assertIn('<html lang="ar" dir="rtl">', text)
            self.assertEqual(text.lower().count("<h1"), 1)
            self.assertIn("اضطراب التكيف", text)
            self.assertIn("الفروق التي تمنع الخلط", text)
            self.assertIn("استجابة الضغط الطبيعية", text)
            self.assertIn("الاكتئاب الجسيم", text)
            self.assertIn("اضطراب ما بعد الصدمة", text)
            self.assertIn("الحزن", text)
            self.assertIn("10.1016/j.jad.2023.11.059", text)
            self.assertIn("37992766", text)
            self.assertIn('"@type":"FAQPage"', text)
            self.assertIn('rel="canonical"', text)
            self.assertNotIn('name="keywords"', text)
            index = (site / "encyclopedia" / "index.html").read_text(encoding="utf-8")
            self.assertIn(module.URL, index)
            namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            root = ET.parse(site / "sitemap.xml").getroot()
            urls = [node.text for node in root.findall("sm:url/sm:loc", namespace)]
            self.assertIn(module.URL, urls)
            self.assertTrue((site / "api" / "adjustment-disorder-v335.json").is_file())

    def test_publish_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self.fixture(site)
            module.publish(site)
            second = module.publish(site)
            index = (site / "encyclopedia" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(index.count(module.URL), 1)
            namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            root = ET.parse(site / "sitemap.xml").getroot()
            urls = [node.text for node in root.findall("sm:url/sm:loc", namespace)]
            self.assertEqual(urls.count(module.URL), 1)
            self.assertEqual(second["index_links_added"], 0)


if __name__ == "__main__":
    unittest.main()
