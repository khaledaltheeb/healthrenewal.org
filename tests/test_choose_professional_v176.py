import json
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v176" / "choosing-mental-health-professional-ar.json"
SCRIPT = ROOT / "scripts" / "publish_choose_professional_v176.py"
BASE = "https://healthrenewal.org"


class ChooseProfessionalGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_content_depth_sources_and_limits(self):
        data = self.data
        self.assertEqual(data["status"], "reviewed")
        self.assertEqual(data["review_status"], "internally-reviewed")
        self.assertGreaterEqual(len(data["sections"]), 9)
        self.assertGreaterEqual(len(data["sources"]), 4)
        self.assertGreaterEqual(len(data["checklist"]), 8)
        self.assertGreaterEqual(len(data["description"]), 120)
        text = json.dumps(data, ensure_ascii=False)
        for phrase in ["لا يستبدل", "لا يقدم تشخيصًا", "خطر وشيك", "الطوارئ المحلية"]:
            self.assertIn(phrase, text)

    def test_sources_are_unique_official_https_records(self):
        sources = self.data["sources"]
        reviewed_at = date.fromisoformat(self.data["reviewed_at"])
        self.assertEqual(len({source["id"] for source in sources}), len(sources))
        self.assertTrue(all(source["type"] == "official_primary_source" for source in sources))
        self.assertTrue(all(source["url"].startswith("https://") for source in sources))
        for source in sources:
            accessed_at = date.fromisoformat(source["accessed_at"])
            verified_at = date.fromisoformat(source["verified_at"])
            self.assertLessEqual(accessed_at, reviewed_at)
            self.assertLessEqual(verified_at, reviewed_at)
            self.assertTrue(source["claims_supported"])
            self.assertEqual(source["status"], "current")

    def test_publisher_generates_accessible_seo_complete_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            subprocess.run(["python", str(SCRIPT), str(site)], cwd=ROOT, check=True, capture_output=True, text=True)
            page = site / "care-guides" / "choosing-mental-health-professional" / "index.html"
            self.assertTrue(page.is_file())
            html = page.read_text(encoding="utf-8")
            checks = [
                '<html lang="ar" dir="rtl">',
                '<meta name="description"',
                '<link rel="canonical"',
                'application/ld+json',
                'BreadcrumbList',
                'max-image-preview:large',
                'انتقل إلى المحتوى الرئيسي',
                'aria-label="التنقل الرئيسي"',
                'window.print()',
                'لا توجد دعوى مراجعة خارجية',
            ]
            for token in checks:
                self.assertIn(token, html)
            self.assertEqual(html.count("<h1>"), 1)
            self.assertGreaterEqual(html.count("<h2>"), 12)
            self.assertGreater(len(html), 12000)

    def test_sitemap_is_idempotent(self):
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        target_url = BASE + "/care-guides/choosing-mental-health-professional/"
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            for _ in range(2):
                subprocess.run(["python", str(SCRIPT), str(site)], cwd=ROOT, check=True, capture_output=True, text=True)
            root = ET.parse(site / "sitemap-care-guides.xml").getroot()
            urls = [node.text for node in root.findall(f"{{{namespace}}}url/{{{namespace}}}loc")]
            self.assertEqual(urls.count(target_url), 1)

    def test_no_diagnostic_or_medication_instruction_claims(self):
        text = json.dumps(self.data, ensure_ascii=False)
        forbidden = ["نضمن الشفاء", "شخّص نفسك", "أوقف الدواء", "غيّر الجرعة", "العلاج المؤكد"]
        for phrase in forbidden:
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
