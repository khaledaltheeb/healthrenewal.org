import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_content_inventory_v69.py"
spec = importlib.util.spec_from_file_location("inventory_v69", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def page(title, body, path, *, links="", source="", robots="", canonical=None, headings=True):
    canonical = canonical or f"https://healthrenewal.org/{path}"
    if path.endswith("index.html"):
        canonical = canonical[:-len("index.html")]
    h = f"<h1>{title}</h1><h2>تفاصيل</h2>" if headings else ""
    source_link = f'<a href="{source}">مصدر</a>' if source else ""
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<title>{title}</title><meta name="description" content="وصف عربي مفيد ومحدد لهذه الصفحة">
<meta name="robots" content="{robots}"><link rel="canonical" href="{canonical}">
<script type="application/ld+json">{{"@type":"Article"}}</script></head>
<body>{h}<main>{body}</main>{links}{source_link}</body></html>'''


class ContentInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.site = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rel, html):
        target = self.site / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    def test_classification_links_duplicates_and_outputs(self):
        long_text = " ".join(["معلومة نفسية موثقة ومفيدة للأسرة والمختص والقارئ"] * 35)
        duplicate_text = " ".join(["شرح متكرر ينبغي دمجه لأنه يقدم المحتوى نفسه دون قيمة مستقلة"] * 25)
        self.write("index.html", page(
            "الرئيسية", long_text, "index.html",
            links='<a href="good/">جيد</a><a href="dup-a/">أ</a><a href="dup-b/">ب</a><a href="search/">بحث</a>',
            source="https://www.who.int/health-topics/mental-health",
        ))
        self.write("good/index.html", page(
            "صفحة جيدة", long_text, "good/index.html",
            links='<a href="../">الرئيسية</a><a href="../dup-a/">مرتبط</a>',
            source="https://www.nice.org.uk/guidance",
        ))
        same = page(
            "محتوى متكرر", duplicate_text, "dup-a/index.html",
            links='<a href="../">الرئيسية</a><a href="../good/">جيد</a>',
            source="https://www.cdc.gov/mental-health/",
        )
        self.write("dup-a/index.html", same)
        self.write("dup-b/index.html", same.replace("dup-a/", "dup-b/"))
        self.write("search/index.html", page(
            "البحث", "نتائج البحث", "search/index.html", robots="noindex,follow"
        ))
        self.write("orphan/index.html", page(
            "صفحة يتيمة", "هذه صفحة قصيرة تحتاج إلى تحسين وتوسيع ومصادر وروابط داخلية أوضح للقارئ", "orphan/index.html"
        ))

        report, pages = module.build_report(self.site)
        by_path = {item.path: item for item in pages}

        self.assertEqual(report["pages_scanned"], 6)
        self.assertEqual(by_path["search/index.html"].decision, "NOINDEX")
        self.assertEqual(by_path["orphan/index.html"].decision, "IMPROVE")
        self.assertIn("orphan_page", by_path["orphan/index.html"].reasons)
        duplicate_decisions = {by_path["dup-a/index.html"].decision, by_path["dup-b/index.html"].decision}
        self.assertIn("MERGE", duplicate_decisions)
        self.assertIn("KEEP", duplicate_decisions)
        self.assertGreater(by_path["good/index.html"].inbound_links, 0)
        self.assertTrue(report["policy"]["advisory_only"])
        self.assertFalse(report["policy"]["automatic_delete_or_noindex"])

        module.write_outputs(self.site, report, pages)
        json_path = self.site / "api" / "content-inventory-v69.json"
        csv_path = self.site / "api" / "content-inventory-v69.csv"
        self.assertTrue(json_path.is_file())
        self.assertTrue(csv_path.is_file())
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], "69-content-inventory")
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 6)
        self.assertIn("decision", rows[0])
        self.assertIn("reasons", rows[0])

    def test_empty_orphan_is_delete_recommendation_only(self):
        self.write("index.html", page("الرئيسية", "محتوى كاف", "index.html"))
        self.write("empty/index.html", page("فارغة", "", "empty/index.html", headings=False))
        report, pages = module.build_report(self.site)
        empty = {page.path: page for page in pages}["empty/index.html"]
        self.assertEqual(empty.decision, "DELETE")
        self.assertIn("effectively_empty", empty.reasons)
        self.assertTrue(report["policy"]["advisory_only"])
        self.assertIn("DELETE", report["policy"]["required_human_review_for"])

    def test_relative_link_resolution_uses_current_directory(self):
        self.assertEqual(module.site_path("../b/", "a/index.html"), "b/index.html")
        self.assertEqual(module.site_path("/c/"), "c/index.html")
        self.assertIsNone(module.site_path("https://example.com/a"))


if __name__ == "__main__":
    unittest.main()
