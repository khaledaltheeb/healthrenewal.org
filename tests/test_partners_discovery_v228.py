from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


publisher = load_module("partners_v228", ROOT / "scripts" / "publish_partners_v201.py")
orphan = load_module("orphan_v228", ROOT / "scripts" / "audit_orphan_pages_v197.py")

HOME = '''<!doctype html><html lang="ar" dir="rtl"><head><title>الرئيسية</title></head><body>
<main><a href="trust/">الثقة</a></main>
<footer><div class="footer-links"><a href="trust/">الثقة والمنهجية</a></div></footer>
</body></html>'''
SITEMAP = '''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://healthrenewal.org/</loc></url>
<url><loc>https://healthrenewal.org/trust/</loc></url>
</urlset>'''


class PartnersDiscoveryV228Tests(unittest.TestCase):
    def make_site(self, root: Path) -> None:
        (root / "index.html").write_text(HOME, encoding="utf-8")
        (root / "sitemap.xml").write_text(SITEMAP, encoding="utf-8")
        trust = root / "trust" / "index.html"
        trust.parent.mkdir(parents=True)
        trust.write_text('<a href="../">الرئيسية</a>', encoding="utf-8")

    def test_publish_links_and_maps_partners_without_false_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self.make_site(site)
            report = publisher.publish(site)
            homepage = (site / "index.html").read_text(encoding="utf-8")
            page = (site / "partners" / "index.html").read_text(encoding="utf-8")
            sitemap = (site / "sitemap-partners.xml").read_text(encoding="utf-8")

            self.assertEqual(report["version"], 228)
            self.assertTrue(report["homepage_link_verified"])
            self.assertFalse(report["unverified_partners_claimed"])
            self.assertEqual(homepage.count(publisher.PARTNERS_LINK), 1)
            self.assertIn("لا توجد جهات مدرجة", page)
            self.assertIn("/partners/", sitemap)

            audit = orphan.audit(site)
            self.assertNotIn("partners/", audit["critical_orphans"])
            self.assertNotIn("partners/", audit["critical_unmapped"])

    def test_publish_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self.make_site(site)
            publisher.publish(site)
            second = publisher.publish(site)
            homepage = (site / "index.html").read_text(encoding="utf-8")
            self.assertFalse(second["footer_link_added"])
            self.assertEqual(homepage.count(publisher.PARTNERS_LINK), 1)

    def test_partners_is_required_gateway(self) -> None:
        self.assertIn("partners/", orphan.CRITICAL_PREFIXES)
        self.assertIn("partners/", orphan.REQUIRED_GATEWAYS)
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text(HOME, encoding="utf-8")
            report = orphan.audit(site, require_gateways=True)
            self.assertIn("partners/", report["missing_gateways"])
            self.assertEqual(report["status"], "failed")


if __name__ == "__main__":
    unittest.main()
