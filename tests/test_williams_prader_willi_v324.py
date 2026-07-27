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

import publish_new_special_needs_conditions_v323 as base
import publish_williams_prader_willi_v324 as module


class WilliamsPraderWilliV324Tests(unittest.TestCase):
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
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/special-needs/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        base.publish(site)
        return site

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_publishes_two_deep_guides_and_expands_cluster_to_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = module.publish(site)
            self.assertEqual(report["version"], 324)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["base_condition_count"], 3)
            self.assertEqual(report["added_condition_count"], 2)
            self.assertEqual(report["total_condition_count"], 5)
            self.assertEqual(report["added_condition_slugs"], list(module.EXPECTED))
            self.assertEqual(report["section_count"], 14)
            self.assertEqual(report["faq_count"], 10)
            self.assertEqual(report["source_count"], 14)
            self.assertGreaterEqual(report["minimum_condition_words"], 1400)
            self.assertTrue(report["cluster_expanded"])
            self.assertTrue(report["hub_link_updated"])
            self.assertTrue(report["sitemap_registered"])
            self.assertFalse(report["external_clinical_review_completed"])

            required = {
                "williams-syndrome": ("7q11.23", "التخدير", "W1", "W7"),
                "prader-willi-syndrome": ("المثيلة", "diazoxide choline", "P1", "P7"),
            }
            for slug, markers in required.items():
                page = site / "special-needs" / slug / "index.html"
                self.assertTrue(page.is_file(), slug)
                text = page.read_text(encoding="utf-8")
                self.assertEqual(text.lower().count("<h1"), 1)
                self.assertEqual(text.count('class="section-card"'), 7)
                self.assertIn("MedicalWebPage", text)
                self.assertIn("FAQPage", text)
                self.assertIn("BreadcrumbList", text)
                self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", text)
                self.assertIsNone(base.BANNED.search(text))
                for marker in markers:
                    self.assertIn(marker, text, slug)

            cluster = site / "special-needs" / "genetic-developmental-syndromes" / "index.html"
            text = cluster.read_text(encoding="utf-8")
            self.assertIn("CollectionPage", text)
            self.assertIn("متلازمة ويليامز", text)
            self.assertIn("متلازمة برادر–ويلي", text)
            self.assertNotIn("متلازمة ويليامز ومتلازمة برادر-ويلي", text)
            for slug in (*base.EXPECTED, *module.EXPECTED):
                self.assertIn(f"/pterminology-site/special-needs/{slug}/", text)

            hub = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(hub.count(base.HUB_MARKER), 1)
            for slug in (*base.EXPECTED, *module.EXPECTED):
                self.assertIn(f"/pterminology-site/special-needs/{slug}/", hub)

            urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            expected_urls = [
                f"{base.BASE}/special-needs/genetic-developmental-syndromes/",
                *(f"{base.BASE}/special-needs/{slug}/" for slug in (*base.EXPECTED, *module.EXPECTED)),
            ]
            for url in expected_urls:
                self.assertEqual(urls.count(url), 1)
            self.assertEqual(len(urls), len(set(urls)))

            api = json.loads((site / "api" / "williams-prader-willi-guides-v324.json").read_text(encoding="utf-8"))
            self.assertEqual(api["total_condition_count"], 5)
            self.assertEqual(api["content_source"], "content/v324/williams-prader-willi-guides-ar.json")

    def test_publication_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            module.publish(site)
            tracked = [
                site / "special-needs" / "index.html",
                site / "special-needs" / "genetic-developmental-syndromes" / "index.html",
                *(site / "special-needs" / slug / "index.html" for slug in module.EXPECTED),
                site / "sitemap-special-needs.xml",
                site / "api" / "williams-prader-willi-guides-v324.json",
            ]
            before = [self.digest(path) for path in tracked]
            second = module.publish(site)
            after = [self.digest(path) for path in tracked]
            self.assertEqual(second["total_condition_count"], 5)
            self.assertEqual(before, after)

    def test_manifest_uses_verified_primary_source_routes(self) -> None:
        payload = module.read_payload()
        guides = {guide["slug"]: guide for guide in module.validate_payload(payload)}
        source_urls = {
            source["id"]: source["url"]
            for guide in guides.values()
            for source in guide["sources"]
        }
        self.assertEqual(
            source_urls["W2"],
            "https://www.ncbi.nlm.nih.gov/books/NBK1249/table/williams.T.recommended_evaluations_follo/",
        )
        self.assertEqual(
            source_urls["W4"],
            "https://www.ncbi.nlm.nih.gov/books/NBK1249/table/williams.T.treatment_of_manifestations_i/",
        )
        self.assertEqual(
            source_urls["W7"],
            "https://www.ncbi.nlm.nih.gov/books/NBK1249/table/williams.T.surveillance_for_williams_syn/",
        )
        self.assertEqual(
            source_urls["P4"],
            "https://www.ncbi.nlm.nih.gov/books/NBK1330/table/pws.T.praderwilli_syndrome_treatment_of/",
        )
        self.assertEqual(
            source_urls["P5"],
            "https://www.ncbi.nlm.nih.gov/books/NBK1330/table/pws.T.praderwilli_syndrome_recommended_s/",
        )

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
