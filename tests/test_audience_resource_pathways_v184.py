import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v184" / "audience-resource-pathways-ar.json"
SCRIPT = ROOT / "scripts" / "publish_audience_resource_pathways_v184.py"
BASE = "https://healthrenewal.org"


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.tags = []
        self.text = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        values = dict(attrs)
        self.attrs.append((tag, values))
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])

    def handle_data(self, data):
        self.text.append(data)


class AudienceResourcePathwaysTests(unittest.TestCase):
    def test_source_contract_is_complete_and_exact(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 184)
        self.assertEqual([item["id"] for item in data["audiences"]], ["person", "family", "teacher", "student", "professional"])
        self.assertEqual(len(data["content_formats"]), 4)
        self.assertEqual(len(data["infographics"]), 3)
        self.assertEqual(len(data["worksheets"]), 5)
        self.assertEqual({item["audience"] for item in data["worksheets"]}, {"person", "family", "teacher", "student", "professional"})
        self.assertIn("المصادر", data["dictionary_contract"]["required_fields"])
        self.assertIn("تاريخ المراجعة", data["dictionary_contract"]["required_fields"])
        self.assertIn("ما الذي لا يعنيه هذا وحده", data["plain_language_contract"]["required_blocks"])
        self.assertGreaterEqual(len(data["disability_content_rules"]), 5)
        self.assertTrue(all(len(item["prompts"]) >= 5 for item in data["worksheets"]))

    def _build(self, site: Path):
        (site / "start-here").mkdir(parents=True)
        (site / "index.html").write_text('<html lang="ar" dir="rtl"><main><h1>الرئيسية</h1></main></html>', encoding="utf-8")
        (site / "start-here" / "index.html").write_text('<html lang="ar" dir="rtl"><main><h1>ابدأ من هنا</h1></main><footer></footer></html>', encoding="utf-8")
        (site / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>', encoding="utf-8")
        result = run(["python", str(SCRIPT), str(site)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((site / "api" / "audience-resource-pathways-v184.json").read_text(encoding="utf-8"))

    def test_builds_all_pages_metadata_accessibility_and_safe_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            report = self._build(site)
            self.assertEqual(report["generated_page_count"], 17)
            self.assertEqual(report["audience_paths"], 5)
            self.assertEqual(report["infographics"], 3)
            self.assertEqual(report["worksheets"], 5)
            for relative in report["generated_pages"]:
                page = (site / relative).read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', page)
                self.assertIn('rel="canonical"', page)
                self.assertIn('application/ld+json', page)
                self.assertIn('href="#main"', page)
                self.assertEqual(page.count("<h1>"), 1)
                self.assertNotIn('شفاء مضمون', page)
                self.assertNotIn('غيّر جرعتك', page)
                self.assertNotIn('هذا الاختبار يشخّص', page)
            portal = (site / "audiences" / "index.html").read_text(encoding="utf-8")
            parser = Collector(); parser.feed(portal)
            for role in ["person", "family", "teacher", "student", "professional"]:
                self.assertIn(f"/audiences/{role}/", parser.links)
            self.assertTrue(all(not link.startswith("/encyclopedia") for link in parser.links))

    def test_worksheets_and_infographics_are_print_ready_and_non_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self._build(site)
            worksheet = (site / "resources" / "worksheets" / "classroom-support-observation" / "index.html").read_text(encoding="utf-8")
            infographic = (site / "resources" / "infographics" / "education-not-diagnosis" / "index.html").read_text(encoding="utf-8")
            for page in [worksheet, infographic]:
                self.assertIn("@media print", page)
                self.assertIn("window.print()", page)
                self.assertIn("لا تشخّص", page)
                self.assertIn("LearningResource", page)
            self.assertEqual(worksheet.count('type="checkbox"'), 5)
            self.assertIn("قارئات الشاشة", (site / "resources" / "infographics" / "index.html").read_text(encoding="utf-8"))

    def test_homepage_start_here_and_sitemap_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self._build(site)
            first_home = (site / "index.html").read_text(encoding="utf-8")
            first_start = (site / "start-here" / "index.html").read_text(encoding="utf-8")
            result = run(["python", str(SCRIPT), str(site)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            home = (site / "index.html").read_text(encoding="utf-8")
            start = (site / "start-here" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(home.count("data-audience-pathways-v184"), 1)
            self.assertEqual(start.count("data-audience-pathways-v184"), 1)
            self.assertEqual(first_home, home)
            self.assertEqual(first_start, start)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            root = ET.parse(site / "sitemap.xml").getroot()
            locs = [node.text for node in root.findall("sm:sitemap/sm:loc", ns)]
            self.assertEqual(locs.count(BASE + "/sitemap-audiences-resources.xml"), 1)
            child = ET.parse(site / "sitemap-audiences-resources.xml").getroot()
            child_locs = [node.text for node in child.findall("sm:url/sm:loc", ns)]
            self.assertEqual(len(child_locs), 17)
            self.assertEqual(len(child_locs), len(set(child_locs)))


if __name__ == "__main__":
    unittest.main()
