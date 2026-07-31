from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_autism_lived_experience_guides_v322.py"
CONTENT = ROOT / "content" / "v322" / "autism-lived-experience-guides-ar.json"

spec = importlib.util.spec_from_file_location("autism_v322", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class AutismLivedExperienceGuidesV322Test(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        parent = site / "special-needs" / "autism" / "index.html"
        parent.parent.mkdir(parents=True)
        parent.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>التوحد</title></head><body>'
            '<main><h1>دليل التوحد</h1><section class="source-area" id="sources"><h2>المراجع</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        sitemap = site / "sitemap-special-needs.xml"
        sitemap.write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/special-needs/autism/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    def test_manifest_depth_evidence_and_language(self) -> None:
        payload = json.loads(CONTENT.read_text(encoding="utf-8"))
        guides = module.validate_payload(payload)
        self.assertEqual(payload["version"], 322)
        self.assertEqual(len(guides), 2)
        self.assertEqual(sum(len(g["sections"]) for g in guides), 10)
        self.assertEqual(sum(len(g["sources"]) for g in guides), 11)
        self.assertEqual(sum(len(g["resources"]) for g in guides), 4)
        text = json.dumps(payload, ensure_ascii=False)
        self.assertIn("National Autistic Society", text)
        self.assertIn("My sensory experience", text)
        self.assertIn("How to talk and write about autism", text)
        self.assertIn("مشكلة التعاطف المتبادل", text)
        self.assertIn("التحفيز الذاتي", text)
        self.assertNotRegex(text, module.BANNED)

    def test_publish_parent_sitemap_schema_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            first = module.publish(site)
            first_parent = (site / "special-needs" / "autism" / "index.html").read_text(encoding="utf-8")
            first_sitemap = (site / "sitemap-special-needs.xml").read_bytes()
            second = module.publish(site)
            second_parent = (site / "special-needs" / "autism" / "index.html").read_text(encoding="utf-8")
            second_sitemap = (site / "sitemap-special-needs.xml").read_bytes()

            self.assertEqual(first, second)
            self.assertEqual(first_parent, second_parent)
            self.assertEqual(first_sitemap, second_sitemap)
            self.assertEqual(first["guide_count"], 2)
            self.assertEqual(first["parent_links_added"], 2)
            self.assertTrue(first["national_autistic_society_resource_used"])
            self.assertTrue(first["content_rewritten_not_copied"])

            for slug in first["guide_slugs"]:
                page = site / "special-needs" / slug / "index.html"
                self.assertTrue(page.is_file())
                html = page.read_text(encoding="utf-8")
                self.assertEqual(html.count("<h1"), 1)
                self.assertEqual(html.count('class="section-card"'), 5)
                self.assertGreaterEqual(html.count('class="resource-card"'), 2)
                self.assertIn('type="application/ld+json"', html)
                self.assertIn('data-surface="dark"', html)
                self.assertIn('data-surface="light"', html)
                self.assertIn("National Autistic Society", html)
                self.assertNotRegex(html, module.BANNED)
                self.assertEqual(first_parent.count(f'data-autism-guide="{slug}"'), 1)

            root = ET.parse(site / "sitemap-special-needs.xml").getroot()
            urls = [(row.findtext("{*}loc") or "").strip() for row in root.findall("{*}url")]
            for slug in first["guide_slugs"]:
                expected = f"https://healthrenewal.org/special-needs/{slug}/"
                self.assertEqual(urls.count(expected), 1)

            report = json.loads((site / "api" / "autism-lived-experience-guides-v322.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["section_count"], 10)
            self.assertEqual(report["source_count"], 11)
            self.assertEqual(report["practical_resource_count"], 4)


if __name__ == "__main__":
    unittest.main()
