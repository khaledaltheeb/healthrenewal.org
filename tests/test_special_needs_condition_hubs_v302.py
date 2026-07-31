from __future__ import annotations

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

import publish_special_needs_condition_hubs_v302 as publisher


class SpecialNeedsConditionHubsV302Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "site"
        (site / "special-needs").mkdir(parents=True)
        (site / "special-needs" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body>'
            '<main><section class="section" id="method"><h2>المنهجية</h2></section></main>'
            '</body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/special-needs/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    def add_topic_first_encyclopedia(self, site: Path) -> None:
        (site / "encyclopedia").mkdir(parents=True, exist_ok=True)
        (site / "encyclopedia" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body>'
            '<main class="ency-topic-v2" data-encyclopedia-index-v2="true">'
            '<header class="ency-topic-v2__hero"><h1>الموسوعة النفسية العربية</h1></header>'
            '<section class="ency-topic-v2__grid" aria-label="الموضوعات المرجعية">'
            '<article class="ency-topic-v2__card topic-item"><h2>موضوع تجريبي</h2></article>'
            '</section></main></body></html>',
            encoding="utf-8",
        )
        topic = site / "hubs" / "topic-058"
        topic.mkdir(parents=True, exist_ok=True)
        topic.joinpath("index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body>'
            '<main class="ency-topic-v2" data-topic-hub-v2="true" data-topic-index="58">'
            '<header class="ency-topic-v2__hero"><h1>التوحد: الدليل المرجعي المتكامل</h1></header>'
            '<section class="ency-topic-v2__section"><h2>ابدأ من السؤال الأقرب</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )

    def test_publish_generates_scientific_hubs_and_editable_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = publisher.publish(site)
            self.assertEqual(report["version"], 302)
            self.assertEqual(report["condition_count"], 2)
            self.assertEqual(report["generated_page_count"], 2)
            self.assertEqual(report["published_provider_count"], 0)
            self.assertEqual(report["source_count"], 17)
            self.assertEqual(report["source_url_override_count"], 1)
            self.assertEqual(
                report["source_url_override_source"],
                "content/v312/special-needs-condition-source-url-overrides.json",
            )
            self.assertEqual(report["encyclopedia_bridge_version"], 322)
            self.assertFalse(report["encyclopedia_bridge"]["available"])
            self.assertFalse(report["autism_topic_bridge"]["available"])
            self.assertFalse(report["down_syndrome_specialized_route_visible"])

            for slug in ("autism", "down-syndrome"):
                page = (site / "special-needs" / slug / "index.html").read_text(encoding="utf-8")
                self.assertEqual(page.count("<h1"), 1)
                self.assertGreaterEqual(page.count('class="evidence-section"'), 12)
                self.assertIn("MedicalWebPage", page)
                self.assertIn("MedicalCondition", page)
                self.assertIn("لا توجد حاليًا سجلات محلية مكتملة التحقق", page)
                self.assertNotIn("قيد الإعداد", page)
                self.assertNotIn("special-needs-providers-ar.json", page)
                self.assertIn('/encyclopedia/', page)
                self.assertIsNone(publisher.BANNED.search(page))

            autism = (site / "special-needs" / "autism" / "index.html").read_text(encoding="utf-8")
            down = (site / "special-needs" / "down-syndrome" / "index.html").read_text(encoding="utf-8")
            self.assertIn('/hubs/topic-058/', autism)
            self.assertIn('المسار الموسوعي للتوحد', autism)
            self.assertIn('الموسوعة النفسية العربية', down)

            corrected = "https://apps.asha.org/EvidenceMaps/Maps/LandingPage/990772a6-9cd8-4203-a76c-6ccd91eac874"
            corrected_title = "Augmentative and Alternative Communication (AAC) Evidence Map"
            obsolete = "https://www.asha.org/Practice-Portal/Professional-Issues/Augmentative-and-Alternative-Communication/"
            failed_lowercase = "https://www.asha.org/practice-portal/professional-issues/augmentative-and-alternative-communication/"
            failed_njc = "https://www.asha.org/NJC/AAC/"
            self.assertEqual(autism.count(corrected), 1)
            self.assertEqual(autism.count(corrected_title), 1)
            self.assertNotIn(obsolete, autism)
            self.assertNotIn(failed_lowercase, autism)
            self.assertNotIn(failed_njc, autism)

            hub = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(hub.count(publisher.HUB_MARKER), 1)
            self.assertIn('/special-needs/autism/', hub)
            self.assertIn('/special-needs/down-syndrome/', hub)

            root = ET.parse(site / "sitemap-special-needs.xml").getroot()
            locations = {(item.findtext("{*}loc") or "").strip() for item in root.findall("{*}url")}
            self.assertIn(f"{publisher.BASE}/special-needs/autism/", locations)
            self.assertIn(f"{publisher.BASE}/special-needs/down-syndrome/", locations)

            api = json.loads((site / "api" / "special-needs-condition-hubs-v302.json").read_text(encoding="utf-8"))
            self.assertEqual(api["condition_slugs"], ["autism", "down-syndrome"])
            self.assertEqual(api["source_url_override_count"], 1)
            self.assertEqual(api["encyclopedia_bridge_version"], 322)

    def test_topic_first_encyclopedia_exposes_specialized_portals_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            self.add_topic_first_encyclopedia(site)

            first = publisher.publish(site)
            second = publisher.publish(site)

            self.assertEqual(first["encyclopedia_bridge_version"], 322)
            self.assertTrue(first["encyclopedia_bridge"]["available"])
            self.assertTrue(first["encyclopedia_bridge"]["added"])
            self.assertTrue(first["autism_topic_bridge"]["available"])
            self.assertTrue(first["autism_topic_bridge"]["added"])
            self.assertTrue(first["down_syndrome_specialized_route_visible"])
            self.assertEqual(first["encyclopedia_bridge"], second["encyclopedia_bridge"])
            self.assertEqual(first["autism_topic_bridge"], second["autism_topic_bridge"])

            encyclopedia = (site / "encyclopedia" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(encyclopedia.count(publisher.ENCYCLOPEDIA_BRIDGE_MARKER), 1)
            self.assertEqual(encyclopedia.count('/special-needs/autism/'), 1)
            self.assertEqual(encyclopedia.count('/special-needs/down-syndrome/'), 1)
            self.assertIn("بوابات علمية متخصصة للتوحد ومتلازمة داون", encyclopedia)
            self.assertIn("خارج قائمة الموضوعات المئة", encyclopedia)

            autism_topic = (site / "hubs" / "topic-058" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(autism_topic.count(publisher.AUTISM_TOPIC_BRIDGE_MARKER), 1)
            self.assertEqual(autism_topic.count('/special-needs/autism/'), 1)
            self.assertIn("الدليل العلمي المتخصص للتوحد", autism_topic)

            api = json.loads((site / "api" / "special-needs-condition-hubs-v302.json").read_text(encoding="utf-8"))
            self.assertEqual(api["encyclopedia_bridge"]["path"], "encyclopedia/index.html")
            self.assertEqual(api["autism_topic_bridge"]["path"], "hubs/topic-058/index.html")
            self.assertTrue(api["down_syndrome_specialized_route_visible"])

    def test_publication_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            first = publisher.publish(site)
            second = publisher.publish(site)
            self.assertEqual(first["generated_pages"], second["generated_pages"])
            hub = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(hub.count(publisher.HUB_MARKER), 1)
            root = ET.parse(site / "sitemap-special-needs.xml").getroot()
            locations = [(item.findtext("{*}loc") or "").strip() for item in root.findall("{*}url")]
            self.assertEqual(locations.count(f"{publisher.BASE}/special-needs/autism/"), 1)
            self.assertEqual(locations.count(f"{publisher.BASE}/special-needs/down-syndrome/"), 1)

    def test_unverified_provider_cannot_be_published(self) -> None:
        providers = json.loads(publisher.PROVIDERS_FILE.read_text(encoding="utf-8"))
        example = dict(providers["example_not_published"])
        example["published"] = True
        example["verification_status"] = "pending"
        providers["providers"] = [example]
        with self.assertRaises(SystemExit):
            publisher.validate_providers(providers)


if __name__ == "__main__":
    unittest.main()
