import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_partners_v201.py"
SOURCE_SITEMAP = ROOT / "sitemap.xml"
BASE = "https://healthrenewal.org"
URL = BASE + "/partners/"
PARTNERS_LINK = '<a href="partners/">الشركاء والشفافية</a>'


class PartnersV201Tests(unittest.TestCase):
    def build_fixture(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="partners-v201-"))
        shutil.copy2(SOURCE_SITEMAP, site / "sitemap.xml")
        (site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>الرئيسية</title></head>'
            '<body><main><h1>الرئيسية</h1></main><footer><div class="footer-links">'
            '<a href="/">الرئيسية</a></div></footer></body></html>',
            encoding="utf-8",
        )
        self.addCleanup(shutil.rmtree, site, True)
        return site

    def publish(self, site: Path) -> None:
        subprocess.run(
            ["python3", str(PUBLISHER), str(site)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_generates_complete_transparent_page_and_report(self):
        site = self.build_fixture()
        self.publish(site)
        page = site / "partners" / "index.html"
        self.assertTrue(page.is_file())
        text = page.read_text(encoding="utf-8")
        self.assertIn('<html lang="ar" dir="rtl">', text)
        self.assertEqual(text.count("<h1>"), 1)
        self.assertIn(f'<link rel="canonical" href="{URL}">', text)
        self.assertIn("application/ld+json", text)
        self.assertIn("لا توجد جهات مدرجة في سجل الشراكات العام داخل هذا الإصدار", text)
        self.assertIn("لا تُعرض أي جهة بصفتها شريكًا رسميًا إلا بعد وجود اتفاق موثق وساري", text)
        self.assertNotIn("شركاؤنا الرسميون", text)
        report = json.loads((site / "api" / "partners-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["public_registry_entries"], 0)
        self.assertFalse(report["unverified_partners_claimed"])
        self.assertTrue(report["homepage_link_verified"])
        homepage = (site / "index.html").read_text(encoding="utf-8")
        self.assertIn(PARTNERS_LINK, homepage)
        self.assertEqual(homepage.count(PARTNERS_LINK), 1)

    def test_sitemap_is_idempotent(self):
        site = self.build_fixture()
        self.publish(site)
        self.publish(site)
        child = ET.parse(site / "sitemap-partners.xml").getroot()
        child_urls = [(node.text or "").strip() for node in child.findall("{*}url/{*}loc")]
        self.assertEqual(child_urls, [URL])
        root = ET.parse(site / "sitemap.xml").getroot()
        kind = root.tag.rsplit("}", 1)[-1]
        if kind == "urlset":
            urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
            self.assertEqual(urls.count(URL), 1)
        else:
            urls = [(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")]
            self.assertEqual(urls.count(BASE + "/sitemap-partners.xml"), 1)
        homepage = (site / "index.html").read_text(encoding="utf-8")
        self.assertEqual(homepage.count(PARTNERS_LINK), 1)

    def test_pipeline_invokes_publisher_before_identity_gate(self):
        pipeline = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(encoding="utf-8")
        self.assertIn('run_publisher("publish_partners_v201.py")', pipeline)
        self.assertIn('"partners_publisher": 201', pipeline)


if __name__ == "__main__":
    unittest.main()
