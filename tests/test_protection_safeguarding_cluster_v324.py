from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_protection_safeguarding_cluster_v324.py"


def load_module():
    spec = importlib.util.spec_from_file_location("protection324", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ProtectionSafeguardingClusterV324Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        (site / "special-needs").mkdir(parents=True)
        (site / "api").mkdir()
        (site / "special-needs" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main>'
            '<section class="pathway" id="protection-safeguarding"><h2>الحماية</h2>'
            '<p>الدليل الأساسي</p></section></main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/special-needs/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    def test_content_contract_and_source_use(self):
        module = load_module()
        payload = module.load_payload()
        guides, source_index = module.validate_payload(payload)
        self.assertEqual(6, len(guides))
        self.assertEqual(12, len(source_index))
        self.assertEqual(module.EXPECTED_SLUGS, [guide["slug"] for guide in guides])
        self.assertGreaterEqual(min(module.visible_words(guide) for guide in guides), 620)
        self.assertEqual(30, sum(len(guide["sections"]) for guide in guides))
        self.assertFalse(payload.get("external_safeguarding_review_completed", False))

    def test_publish_parent_sitemap_pages_schema_and_idempotence(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = module.publish(site)
            self.assertEqual("passed", report["status"])
            self.assertEqual(6, report["guide_count"])
            self.assertEqual(30, report["section_count"])
            self.assertGreaterEqual(report["minimum_rendered_words"], 650)
            self.assertEqual(18, report["urgent_item_count"])
            self.assertEqual(36, report["checklist_item_count"])
            self.assertFalse(report["external_safeguarding_review_completed"])

            parent = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, parent.count(module.MARKER))
            for slug in module.EXPECTED_SLUGS:
                self.assertEqual(1, parent.count(f"/special-needs/{slug}/"))
                page = (site / "special-needs" / slug / "index.html").read_text(encoding="utf-8")
                self.assertEqual(1, page.count("<h1"))
                self.assertEqual(5, page.count('class="section-card"'))
                self.assertIn('<script type="application/ld+json">', page)
                self.assertIn('"@type": "Article"', page)
                self.assertIn('"@type": "BreadcrumbList"', page)
                self.assertIn(f'<link rel="canonical" href="{module.BASE}/special-needs/{slug}/">', page)
                self.assertIn('meta name="robots" content="index,follow', page)
                self.assertNotRegex(page, module.BANNED)

            tree = ET.parse(site / "sitemap-special-needs.xml")
            urls = [(row.findtext("{*}loc") or "").strip() for row in tree.getroot().findall("{*}url")]
            for slug in module.EXPECTED_SLUGS:
                self.assertEqual(1, urls.count(f"{module.BASE}/special-needs/{slug}/"))

            report_file = json.loads(
                (site / "api" / "protection-safeguarding-cluster-v324.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report, report_file)

            before = digest_tree(site)
            report2 = module.publish(site)
            after = digest_tree(site)
            self.assertEqual(report, report2)
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
