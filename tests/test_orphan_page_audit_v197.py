import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_orphan_pages_v197.py"
spec = importlib.util.spec_from_file_location("orphan_v197", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

PAGE = '<!doctype html><html lang="ar" dir="rtl"><head><title>x</title><meta name="description" content="x"><link rel="canonical" href="x"></head><body>{}</body></html>'


class OrphanAuditTests(unittest.TestCase):
    def test_detects_and_clears_critical_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "api").mkdir()
            (site / "index.html").write_text(PAGE.format('<a href="encyclopedia/">الموسوعة</a>'), encoding="utf-8")
            target = site / "encyclopedia" / "index.html"
            target.parent.mkdir()
            target.write_text(PAGE.format(''), encoding="utf-8")
            (site / "sitemap-content.xml").write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://khaledaltheeb.github.io/pterminology-site/</loc></url><url><loc>https://khaledaltheeb.github.io/pterminology-site/encyclopedia/</loc></url></urlset>', encoding="utf-8")
            report = module.audit(site)
            self.assertEqual(report["status"], "passed")
            (site / "index.html").write_text(PAGE.format(''), encoding="utf-8")
            report = module.audit(site)
            self.assertEqual(report["critical_orphans"], ["encyclopedia/"])
            self.assertEqual(report["status"], "failed")

    def test_flags_critical_page_missing_from_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text(PAGE.format('<a href="special-needs/">ذوو الاحتياجات</a>'), encoding="utf-8")
            target = site / "special-needs" / "index.html"
            target.parent.mkdir()
            target.write_text(PAGE.format(''), encoding="utf-8")
            report = module.audit(site)
            self.assertIn("special-needs/", report["critical_unmapped"])

    def test_treats_comparisons_as_critical_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text(PAGE.format(''), encoding="utf-8")
            target = site / "comparisons" / "index.html"
            target.parent.mkdir()
            target.write_text(PAGE.format(''), encoding="utf-8")
            report = module.audit(site)
            self.assertEqual(report["critical_orphans"], ["comparisons/"])
            self.assertEqual(report["critical_unmapped"], ["comparisons/"])
            self.assertEqual(report["status"], "failed")

    def test_requires_all_institutional_gateways_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text(PAGE.format(''), encoding="utf-8")
            report = module.audit(site, require_gateways=True)
            self.assertIn("sections/", report["missing_gateways"])
            self.assertIn("comparisons/", report["missing_gateways"])
            self.assertIn("library/", report["missing_gateways"])
            self.assertEqual(report["status"], "failed")

    def test_section_directory_must_be_linked_and_sitemapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            section = site / "sections" / "index.html"
            section.parent.mkdir()
            section.write_text(PAGE.format('<a href="../encyclopedia/">الموسوعة</a>'), encoding="utf-8")
            (site / "index.html").write_text(PAGE.format('<a href="sections/">جميع الأقسام</a>'), encoding="utf-8")
            (site / "sitemap-sections.xml").write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://khaledaltheeb.github.io/pterminology-site/</loc></url>'
                '<url><loc>https://khaledaltheeb.github.io/pterminology-site/sections/</loc></url>'
                '</urlset>',
                encoding="utf-8",
            )
            report = module.audit(site)
            self.assertNotIn("sections/", report["critical_orphans"])
            self.assertNotIn("sections/", report["critical_unmapped"])
            self.assertEqual(report["status"], "passed")

            (site / "index.html").write_text(PAGE.format(''), encoding="utf-8")
            report = module.audit(site)
            self.assertEqual(report["critical_orphans"], ["sections/"])
            self.assertEqual(report["status"], "failed")


if __name__ == "__main__":
    unittest.main()
