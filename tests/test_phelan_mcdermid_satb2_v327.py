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

import publish_mowat_wilson_kleefstra_v326 as v326
import publish_new_special_needs_conditions_v323 as v323
import publish_phelan_mcdermid_satb2_v327 as module
import publish_smith_magenis_pitt_hopkins_v325 as v325
import publish_williams_prader_willi_v324 as v324


class PhelanMcDermidSatb2V327Tests(unittest.TestCase):
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
        v323.publish(site)
        v324.publish(site)
        v325.publish(site)
        v326.publish(site)
        return site

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_publishes_two_guides_and_expands_cluster_to_eleven(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = module.publish(site)
            self.assertEqual(report["version"], 327)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["previous_condition_count"], 9)
            self.assertEqual(report["added_condition_count"], 2)
            self.assertEqual(report["total_condition_count"], 11)
            self.assertEqual(report["added_condition_slugs"], list(module.EXPECTED))
            self.assertEqual(report["section_count"], 14)
            self.assertEqual(report["source_count"], 14)
            self.assertEqual(report["faq_count"], 10)
            self.assertGreaterEqual(report["minimum_condition_words"], 1750)
            self.assertTrue(report["cluster_expanded"])
            self.assertTrue(report["hub_link_updated"])
            self.assertTrue(report["sitemap_registered"])
            self.assertFalse(report["external_clinical_review_completed"])

            required = {
                "phelan-mcdermid-syndrome": ("SHANK3", "الحلقة الصبغية 22", "NF2", "P1", "P7"),
                "satb2-associated-syndrome": ("SATB2", "ESES", "DXA", "A1", "A7"),
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
                self.assertIsNone(v323.BANNED.search(text))
                for marker in markers:
                    self.assertIn(marker, text, slug)

            all_slugs = (*v323.EXPECTED, *v324.EXPECTED, *v325.EXPECTED, *v326.EXPECTED, *module.EXPECTED)
            cluster = site / "special-needs" / "genetic-developmental-syndromes" / "index.html"
            cluster_text = cluster.read_text(encoding="utf-8")
            self.assertIn("CollectionPage", cluster_text)
            self.assertIn("متلازمة فيلان–ماكديرميد", cluster_text)
            self.assertIn("المتلازمة المرتبطة بـSATB2", cluster_text)
            self.assertIn("يضم المركز الآن أحد عشر دليلًا مستقلًا", cluster_text)
            self.assertNotIn("يضم المركز الآن تسعة أدلة مستقلة", cluster_text)
            for slug in all_slugs:
                self.assertIn(f"/pterminology-site/special-needs/{slug}/", cluster_text)
                self.assertTrue((site / "special-needs" / slug / "index.html").is_file())

            hub = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(hub.count(v323.HUB_MARKER), 1)
            for slug in all_slugs:
                self.assertIn(f"/pterminology-site/special-needs/{slug}/", hub)

            urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            expected_urls = [
                f"{v323.BASE}/special-needs/genetic-developmental-syndromes/",
                *(f"{v323.BASE}/special-needs/{slug}/" for slug in all_slugs),
            ]
            for url in expected_urls:
                self.assertEqual(urls.count(url), 1)
            self.assertEqual(len(urls), len(set(urls)))

            api = json.loads((site / "api" / "phelan-mcdermid-satb2-guides-v327.json").read_text(encoding="utf-8"))
            self.assertEqual(api["total_condition_count"], 11)
            self.assertEqual(api["content_source"], "content/v327/phelan-mcdermid-satb2-guides-ar.json")

    def test_publication_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            module.publish(site)
            tracked = [
                site / "special-needs" / "index.html",
                site / "special-needs" / "genetic-developmental-syndromes" / "index.html",
                *(site / "special-needs" / slug / "index.html" for slug in module.EXPECTED),
                site / "sitemap-special-needs.xml",
                site / "api" / "phelan-mcdermid-satb2-guides-v327.json",
            ]
            before = [self.digest(path) for path in tracked]
            second = module.publish(site)
            after = [self.digest(path) for path in tracked]
            self.assertEqual(second["total_condition_count"], 11)
            self.assertEqual(before, after)

    def test_manifest_primary_source_contract(self) -> None:
        payload = module.read_payload()
        guides = {guide["slug"]: guide for guide in module.validate_payload(payload)}
        urls = {source["id"]: source["url"] for guide in guides.values() for source in guide["sources"]}
        self.assertEqual(urls["P1"], "https://www.ncbi.nlm.nih.gov/books/NBK1198/")
        self.assertEqual(urls["A1"], "https://www.ncbi.nlm.nih.gov/books/NBK458647/")
        self.assertTrue(urls["P6"].endswith("phelanmcdermid_syndromeshan_5/"))
        self.assertTrue(urls["A6"].startswith("https://www.ncbi.nlm.nih.gov/books/NBK458647/table/"))

    def test_rejects_dishonest_review_missing_evidence_or_duplicate_route(self) -> None:
        payload = module.read_payload()
        payload["review_status"] = "externally-reviewed"
        with self.assertRaises(SystemExit):
            module.validate_payload(payload)

        payload = module.read_payload()
        payload["guides"][0]["sections"][0]["source_ids"] = ["MISSING"]
        with self.assertRaises(SystemExit):
            module.validate_payload(payload)

        payload = module.read_payload()
        payload["guides"][1]["slug"] = "phelan-mcdermid-syndrome"
        with self.assertRaises(SystemExit):
            module.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
