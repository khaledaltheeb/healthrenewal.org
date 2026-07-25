from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "link_care_guides_v21.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"


class CareGuidesV234Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        (site / "api").mkdir(parents=True)
        (site / "sectors" / "family").mkdir(parents=True)
        (site / "encyclopedia").mkdir(parents=True)
        extension = site / "care-guides" / "choosing-mental-health-professional"
        extension.mkdir(parents=True)
        (site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><nav><a href="tips/">النصائح</a></nav>'
            '<main><a class="btn secondary" href="tips/">افتح الأدلة العملية</a></main></body></html>',
            encoding="utf-8",
        )
        (site / "sectors" / "family" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>الأسرة</h1></main></body></html>',
            encoding="utf-8",
        )
        (site / "encyclopedia" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>الموسوعة</h1></main></body></html>',
            encoding="utf-8",
        )
        extension_html = (
            '<!doctype html><html lang="ar" dir="rtl"><head>'
            '<title>اختيار مختص نفسي مناسب | منصة الصحة النفسية</title>'
            '<meta name="description" content="دليل مستقل محفوظ لاختيار مختص نفسي مناسب والتحقق من المؤهلات وحدود الخدمة.">'
            '<meta name="robots" content="index,follow"><meta name="keywords" content="اختيار مختص نفسي">'
            f'<link rel="canonical" href="{BASE}care-guides/choosing-mental-health-professional/">'
            '<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Article"},{"@type":"HowTo"}]}</script>'
            '</head><body><main><h1>اختيار مختص نفسي مناسب</h1>'
            '<section><h2>مصادر مؤسسية للمراجعة</h2><p>خدمات الطوارئ المحلية عند الخطر.</p></section>'
            '</main></body></html>'
        )
        (extension / "index.html").write_text(extension_html, encoding="utf-8")
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )
        (site / "sitemap-care-guides.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{BASE}care-guides/</loc></url>'
            f'<url><loc>{BASE}care-guides/choosing-mental-health-professional/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        (site / "api" / "care-guides-v21.json").write_text(
            '{"version":194,"publication_gate_version":194,"published_core_guides":7,"source_guides":8,"autism_published":false}\n',
            encoding="utf-8",
        )
        return site

    def run_linker(self, site: Path) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(site)],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        return json.loads(result.stdout)

    def test_expansion_safety_seo_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            first = self.run_linker(site)
            self.assertEqual(first["expansion_version"], 234)
            self.assertEqual(first["expansion_status"], "passed")
            self.assertTrue(first["idempotent_blocks"])
            self.assertTrue(first["no_blocked_review_routes"])

            report = json.loads((site / "api" / "care-guides-v234.json").read_text(encoding="utf-8"))
            legacy = json.loads((site / "api" / "care-guides-v21.json").read_text(encoding="utf-8"))
            self.assertEqual(report["expansion_guides"], 12)
            self.assertEqual(report["published_known_guides"], 19)
            self.assertEqual(report["blocked_review_slugs"], ["autism-family-practical-guide"])
            self.assertEqual(report["extension_guides_preserved"], 1)
            self.assertEqual(report["pages"], 21)
            self.assertEqual(report["sitemap_urls"], 21)
            self.assertEqual(legacy["guides"], 20)
            self.assertEqual(legacy["published_core_guides"], 7)
            self.assertEqual(legacy["published_known_guides"], 19)
            self.assertFalse((site / "care-guides" / "autism-family-practical-guide").exists())
            self.assertTrue((site / "care-guides" / "choosing-mental-health-professional" / "index.html").is_file())

            index = (site / "care-guides" / "index.html").read_text(encoding="utf-8")
            for token in (
                'data-care-search', 'data-care-filter', 'منهجية التحرير والنشر',
                '<meta name="keywords"', '<meta name="robots"', '<link rel="canonical"',
                '"CollectionPage"', '"ItemList"', '"FAQPage"',
            ):
                self.assertIn(token, index)

            self_harm = (site / "care-guides" / "self-harm-family-response-plan" / "index.html").read_text(encoding="utf-8")
            for token in (
                "مصادر مؤسسية للمراجعة", "خدمات الطوارئ", '"@type":"MedicalWebPage"',
                '"@type":"Article"', '"HowTo"', '"FAQPage"', "لا توجد مراجعة اختصاصية بشرية موثقة",
            ):
                self.assertIn(token, self_harm)
            self.assertNotIn("معاقين", "\n".join(p.read_text(encoding="utf-8") for p in (site / "care-guides").rglob("*.html")))

            sitemap = ET.parse(site / "sitemap-care-guides.xml").getroot()
            urls = [n.text for n in sitemap.findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), len(set(urls)))
            self.assertIn(BASE + "care-guides/choosing-mental-health-professional/", urls)
            self.assertNotIn(BASE + "care-guides/autism-family-practical-guide/", urls)
            self.assertIn(BASE + "sitemap-care-guides.xml", (site / "sitemap.xml").read_text(encoding="utf-8"))
            robots = (site / "robots.txt").read_text(encoding="utf-8")
            self.assertIn("Allow: /pterminology-site/", robots)
            self.assertIn("Sitemap: " + BASE + "sitemap-care-guides.xml", robots)

            second = self.run_linker(site)
            self.assertTrue(second["idempotent_blocks"])
            self.assertTrue(second["duplicate_free"])
            second_report = json.loads((site / "api" / "care-guides-v234.json").read_text(encoding="utf-8"))
            self.assertEqual(second_report["pages"], report["pages"])
            self.assertEqual(second_report["sitemap_urls"], report["sitemap_urls"])

    def test_source_manifest_contract(self) -> None:
        payload = json.loads((ROOT / "content" / "v234" / "care-guides-manifest-ar.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 234)
        self.assertEqual(payload["review_status"], "internally-reviewed")
        self.assertFalse(payload["external_specialist_review"])
        self.assertEqual(len(payload["guide_slugs"]), 12)
        slugs = payload["guide_slugs"]
        self.assertEqual(len(slugs), len(set(slugs)))
        guides = []
        for relative in payload["guide_files"]:
            item = json.loads((ROOT / "content" / "v234" / relative).read_text(encoding="utf-8"))
            guides.extend(item.get("guides", [item]))
        self.assertEqual([g["slug"] for g in guides], slugs)
        for guide in guides:
            self.assertEqual(guide["review_status"], "internally-reviewed")
            self.assertFalse(guide["external_specialist_review"])
            self.assertGreaterEqual(len(guide["sources"]), 2)
            self.assertTrue(guide["emergency_note"])
            practical_sections = [
                key for key, value in guide.items()
                if isinstance(value, list) and key not in {"sources", "audience", "search_intent"} and value
            ]
            self.assertGreaterEqual(len(practical_sections), 5)
            for source in guide["sources"]:
                self.assertRegex(source["url"], r"^https://")
                self.assertRegex(source["url"], r"(nice\.org\.uk|nhs\.uk|who\.int|samhsa\.gov)")


if __name__ == "__main__":
    unittest.main()
