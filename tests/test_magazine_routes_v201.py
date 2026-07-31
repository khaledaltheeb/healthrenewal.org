import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_magazine_v201.py"
SOURCE = ROOT / "magazine"
SOURCE_SITEMAP = ROOT / "sitemap.xml"
BASE = "https://healthrenewal.org"
URL = BASE + "/magazine/"
ROBOTS_PATTERN = re.compile(r'<meta\s+[^>]*name=["\']robots["\'][^>]*>', re.I)
SPEC = importlib.util.spec_from_file_location("publish_magazine_routes_v320", PUBLISHER)
assert SPEC and SPEC.loader
PUBLISHER_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PUBLISHER_MODULE
SPEC.loader.exec_module(PUBLISHER_MODULE)


class MagazineRoutesV201Tests(unittest.TestCase):
    def fixture(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="magazine-v201-"))
        shutil.copy2(SOURCE_SITEMAP, site / "sitemap.xml")
        self.addCleanup(shutil.rmtree, site, True)
        return site

    @staticmethod
    def article_files() -> list[Path]:
        return PUBLISHER_MODULE.article_files()

    def test_magazine_archive_is_complete_honest_and_indexable(self):
        site = self.fixture()
        subprocess.run(["python3", str(PUBLISHER), str(site)], cwd=ROOT, check=True, capture_output=True, text=True)
        articles = self.article_files()
        self.assertGreaterEqual(len(articles), 72)
        dates = [PUBLISHER_MODULE.article_date(path) for path in articles]
        self.assertEqual(dates, sorted(dates, reverse=True))
        page = site / "magazine" / "index.html"
        self.assertTrue(page.is_file())
        text = page.read_text(encoding="utf-8")
        self.assertIn('<html lang="ar" dir="rtl">', text)
        self.assertEqual(text.count("<h1>"), 1)
        self.assertIn(f'<link rel="canonical" href="{URL}">', text)
        self.assertEqual(text.count('class="card"'), len(articles))
        self.assertNotIn("لا يتضمن هذا الإصدار ملخصات دراسات منفردة", text)
        self.assertNotIn("مراجعة اختصاصية مكتملة", text)

        published = [page, *(site / "magazine" / path.name for path in articles)]
        for published_page in published:
            published_text = published_page.read_text(encoding="utf-8")
            self.assertEqual(
                len(ROBOTS_PATTERN.findall(published_text)),
                1,
                published_page.name,
            )
            self.assertNotIn("noindex", published_text.lower(), published_page.name)

        report = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
        self.assertTrue(report["methodology_published"])
        self.assertEqual(report["research_summaries_published"], len(articles))
        self.assertEqual(report["articles"], [path.name for path in articles])
        self.assertEqual(report["article_dates"], {path.name: PUBLISHER_MODULE.article_date(path) for path in articles})
        self.assertEqual(report["review_status"], "internally-reviewed")
        self.assertEqual(report["risk_level"], "low")
        self.assertEqual(report["unwired_research_pages"], 0)
        self.assertEqual(report["robots_contract"], "exactly-one-index-follow-meta-per-published-page")
        self.assertGreaterEqual(report["robots"]["robots_normalized_pages"], 5)
        self.assertEqual(report["index_contract"], "generated-from-discovered-articles-sorted-by-datePublished")
        self.assertEqual(report["rss_contract"], "latest-twenty-sorted-by-datePublished")

    def test_magazine_sitemap_is_idempotent(self):
        site = self.fixture()
        for _ in range(2):
            subprocess.run(["python3", str(PUBLISHER), str(site)], cwd=ROOT, check=True, capture_output=True, text=True)
        expected = [URL, *(URL + path.name for path in self.article_files())]
        child = ET.parse(site / "sitemap-magazine.xml").getroot()
        urls = [(node.text or "").strip() for node in child.findall("{*}url/{*}loc")]
        self.assertEqual(urls, expected)
        self.assertEqual(len(urls), len(set(urls)))
        main = ET.parse(site / "sitemap.xml").getroot()
        kind = main.tag.rsplit("}", 1)[-1]
        if kind == "urlset":
            values = [(node.text or "").strip() for node in main.findall("{*}url/{*}loc")]
            for expected_url in expected:
                self.assertEqual(values.count(expected_url), 1)
        else:
            values = [(node.text or "").strip() for node in main.findall("{*}sitemap/{*}loc")]
            self.assertEqual(values.count(BASE + "/sitemap-magazine.xml"), 1)

    def test_pipeline_restores_existing_assessment_demo(self):
        pipeline = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(encoding="utf-8")
        self.assertIn('restore_static_route("provider-assessment-demo")', pipeline)
        self.assertIn('run_publisher("publish_magazine_v201.py")', pipeline)
        self.assertIn('"magazine_publisher": 201', pipeline)
        required = [
            ROOT / "provider-assessment-demo" / "index.html",
            ROOT / "provider-assessment-demo" / "styles.css",
            ROOT / "provider-assessment-demo" / "catalog.js",
            ROOT / "provider-assessment-demo" / "app.js",
        ]
        self.assertTrue(all(path.is_file() for path in required))


if __name__ == "__main__":
    unittest.main()
