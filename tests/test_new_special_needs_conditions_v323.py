from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_new_special_needs_conditions_v323 as module


class NewSpecialNeedsConditionsV323Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        (site / "special-needs").mkdir(parents=True)
        (site / "api").mkdir()
        (site / "special-needs" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main>'
            '<section class="section"><h1>ذوو الاحتياجات الخاصة</h1></section>'
            '<section class="section" id="method"><h2>المنهج</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/special-needs/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_publishes_three_deep_new_conditions_and_cluster(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = module.publish(site)
            self.assertEqual(report["version"], 323)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["condition_count"], 3)
            self.assertEqual(report["condition_slugs"], list(module.EXPECTED))
            self.assertEqual(report["section_count"], 21)
            self.assertEqual(report["faq_count"], 15)
            self.assertGreaterEqual(report["source_count"], 18)
            self.assertGreaterEqual(report["minimum_condition_words"], 1350)
            self.assertTrue(report["hub_link_added"])
            self.assertTrue(report["sitemap_registered"])
            self.assertFalse(report["external_clinical_review_completed"])

            cluster = site / "special-needs" / "genetic-developmental-syndromes" / "index.html"
            self.assertTrue(cluster.is_file())
            cluster_text = cluster.read_text(encoding="utf-8")
            self.assertIn("CollectionPage", cluster_text)
            self.assertIn("متلازمة ريت", cluster_text)
            self.assertIn("متلازمة الكروموسوم X الهش", cluster_text)
            self.assertIn("متلازمة أنجلمان", cluster_text)

            required = {
                "rett-syndrome": ("MECP2", "trofinetide", "R1", "R6"),
                "fragile-x-syndrome": ("FMR1", "microarray", "F1", "F6"),
                "angelman-syndrome": ("UBE3A", "فحص المثيلة", "A1", "A7"),
            }
            for slug, markers in required.items():
                path = site / "special-needs" / slug / "index.html"
                self.assertTrue(path.is_file(), slug)
                text = path.read_text(encoding="utf-8")
                self.assertEqual(text.lower().count("<h1"), 1)
                self.assertEqual(text.count('class="section-card"'), 7)
                self.assertIn("MedicalWebPage", text)
                self.assertIn("FAQPage", text)
                self.assertIn("BreadcrumbList", text)
                self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", text)
                self.assertIsNone(module.BANNED.search(text))
                for marker in markers:
                    self.assertIn(marker, text, slug)

            hub = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(hub.count(module.HUB_MARKER), 1)
            for slug in module.EXPECTED:
                self.assertIn(f"/special-needs/{slug}/", hub)

            urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            expected_urls = [
                f"{module.BASE}/special-needs/genetic-developmental-syndromes/",
                *(f"{module.BASE}/special-needs/{slug}/" for slug in module.EXPECTED),
            ]
            for url in expected_urls:
                self.assertEqual(urls.count(url), 1)
            self.assertEqual(len(urls), len(set(urls)))

            api = json.loads((site / "api" / "new-special-needs-conditions-v323.json").read_text(encoding="utf-8"))
            self.assertEqual(api["condition_count"], 3)
            self.assertEqual(api["content_source"], "content/v323/new-special-needs-conditions-ar.json")

    def test_publication_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            module.publish(site)
            tracked = [
                site / "special-needs" / "index.html",
                site / "special-needs" / "genetic-developmental-syndromes" / "index.html",
                *(site / "special-needs" / slug / "index.html" for slug in module.EXPECTED),
                site / "sitemap-special-needs.xml",
                site / "api" / "new-special-needs-conditions-v323.json",
            ]
            before = [self.digest(path) for path in tracked]
            second = module.publish(site)
            after = [self.digest(path) for path in tracked]
            self.assertEqual(second["condition_count"], 3)
            self.assertEqual(before, after)

    def test_manifest_rejects_dishonest_review_or_missing_evidence(self) -> None:
        payload = module.read_payload()
        payload["review_status"] = "externally-reviewed"
        with self.assertRaises(SystemExit):
            module.validate_payload(payload)

        payload = module.read_payload()
        payload["guides"][0]["sections"][0]["source_ids"] = ["MISSING"]
        with self.assertRaises(SystemExit):
            module.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
