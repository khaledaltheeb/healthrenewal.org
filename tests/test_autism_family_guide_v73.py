from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v18" / "care-guides-autism-ar.json"
PUBLISHER = ROOT / "scripts" / "publish_care_guides_v21.py"
PUBLISHER_IMPLEMENTATION = ROOT / "scripts" / "publish_care_guides_v246.py"
LINKER = ROOT / "scripts" / "link_care_guides_v21.py"
BLOCKED_SLUG = "autism-family-practical-guide"
BLOCKED_ROUTE = f"care-guides/{BLOCKED_SLUG}/"
EXPECTED_SOURCE_FILES = {
    "care-guides-ar.json",
    "care-guides-adhd-ar.json",
    "care-guides-autism-ar.json",
    "care-guides-family-anxiety-panic-support-ar.json",
    "care-guides-family-ocd-support-ar.json",
    "care-guides-bipolar-family-early-warning-plan-ar.json",
    "care-guides-trauma-ptsd-family-support-ar.json",
    "care-guides-eating-disorder-family-support-ar.json",
    "care-guides-self-harm-family-safety-support-ar.json",
}


class AutismFamilyGuideV73Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(DATA.read_text(encoding="utf-8"))
        cls.payload = payload
        cls.guide = payload["guides"][0]
        cls.serialized = json.dumps(cls.guide, ensure_ascii=False)

    def test_identity_review_status_and_depth(self) -> None:
        guide = self.guide
        self.assertEqual(self.payload["version"], 73)
        self.assertEqual(self.payload["language"], "ar")
        self.assertEqual(guide["id"], "guide.autism.family-practical")
        self.assertEqual(guide["slug"], BLOCKED_SLUG)
        self.assertEqual(guide["review_status"], "needs-specialist-review")
        required = {
            "understanding", "what_the_person_may_feel", "strengths_and_differences",
            "communication_plan", "sensory_plan", "do", "avoid", "home_plan",
            "school_plan", "transition_protocol", "meltdown_protocol", "wandering_protocol",
            "sleep_plan", "food_plan", "medication_awareness", "when_to_seek_help",
            "caregiver_plan",
        }
        self.assertTrue(required.issubset(guide))
        self.assertGreaterEqual(sum(len(guide[key]) for key in required), 80)
        self.assertGreaterEqual(len(guide["sources"]), 4)

    def test_situation_protocols_are_actionable(self) -> None:
        for key in ("transition_protocol", "meltdown_protocol", "wandering_protocol"):
            text = " ".join(self.guide[key])
            self.assertIn("ماذا أرى", text)
            self.assertIn("ماذا أفعل", text)
            self.assertIn("أتجنب", text)
            self.assertIn("مختص", text)
            self.assertIn("طارئة", text)

    def test_safety_non_diagnostic_and_dignity_language(self) -> None:
        text = self.serialized
        required_phrases = (
            "التشخيص مهني", "لا توقف الدواء", "خدمات الطوارئ المحلية", "يشفي التوحد",
            "راجع الألم", "احترم رفض التواصل البصري", "الهدف ليس جعل الشخص يبدو غير متوحد",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, text)
        for phrase in ("جرعة موصى بها", "يعالج التوحد نهائيًا", "تشخيصك هو", "اضبطه بالقوة"):
            self.assertNotIn(phrase, text)

    def test_sources_are_unique_https_and_institutional(self) -> None:
        sources = self.guide["sources"]
        urls = [source["url"] for source in sources]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(url.startswith("https://") for url in urls))
        hosts = " ".join(urls)
        for host in ("who.int", "nice.org.uk", "cdc.gov"):
            self.assertIn(host, hosts)

    def test_source_contract_is_retained_but_publication_is_blocked(self) -> None:
        publisher = PUBLISHER.read_text(encoding="utf-8")
        implementation = PUBLISHER_IMPLEMENTATION.read_text(encoding="utf-8")
        linker = LINKER.read_text(encoding="utf-8")
        data_sources = set(re.findall(r'ROOT / "content/v18/(care-guides-[^"]+\.json)"', implementation))
        self.assertEqual(data_sources, EXPECTED_SOURCE_FILES)
        self.assertIn("EXPECTED_LEGACY_SOURCE_GUIDES = 14", implementation)
        self.assertIn("EXPECTED_SOURCE_GUIDES = 101", implementation)
        self.assertIn("MINIMUM_PUBLISHED_GUIDES = 100", implementation)
        self.assertIn("CONTENT_RELEASE_VERSION = 246", implementation)
        self.assertIn('BLOCKED_REVIEW_STATUSES = {"needs-specialist-review"}', implementation)
        self.assertIn('"needs_specialist_review_published": False', implementation)
        self.assertIn('"blocked_review_slugs": blocked_slugs', implementation)
        self.assertIn("shutil.rmtree", implementation)
        self.assertIn("import publish_care_guides_v246 as implementation", publisher)
        self.assertIn("autism_published = AUTISM_PAGE.is_file()", linker)
        self.assertIn("blocked_review_links_removed", linker)
        self.assertIn("no_blocked_review_routes", linker)
        self.assertIn("autism-family-journey-v73", linker)
        self.assertIn("autism-encyclopedia-journey-v73", linker)
        self.assertIn("autism-related-journey-v73", linker)
        self.assertIn("@media print", implementation)

    def test_production_publisher_and_linker_cannot_recreate_blocked_guide(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            (site / "sectors" / "family").mkdir(parents=True)
            (site / "encyclopedia").mkdir(parents=True)
            (site / "index.html").write_text(
                '<html lang="ar" dir="rtl"><body>'
                '<a href="tips/">النصائح</a>'
                '<a class="btn secondary" href="tips/">افتح الأدلة العملية</a>'
                '<main></main></body></html>', encoding="utf-8"
            )
            (site / "sectors" / "family" / "index.html").write_text(
                '<html lang="ar" dir="rtl"><main></main></html>', encoding="utf-8"
            )
            (site / "encyclopedia" / "index.html").write_text(
                '<html lang="ar" dir="rtl"><main></main></html>', encoding="utf-8"
            )
            namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
            root = ET.Element("urlset", xmlns=namespace)
            node = ET.SubElement(root, "url")
            ET.SubElement(node, "loc").text = "https://healthrenewal.org/"
            ET.ElementTree(root).write(site / "sitemap.xml", encoding="utf-8", xml_declaration=True)

            for _ in range(2):
                subprocess.run([sys.executable, str(PUBLISHER), str(site)], check=True, cwd=ROOT)
                subprocess.run([sys.executable, str(LINKER), str(site)], check=True, cwd=ROOT)

            self.assertFalse((site / "care-guides" / BLOCKED_SLUG).exists())
            approved = site / "care-guides" / "adhd-family-practical-guide" / "index.html"
            self.assertTrue(approved.is_file())
            for relative in (
                "care-guides/index.html", "sectors/family/index.html", "encyclopedia/index.html",
                "sitemap-care-guides.xml", "sitemap.xml",
            ):
                self.assertNotIn(BLOCKED_ROUTE, (site / relative).read_text(encoding="utf-8"), relative)

            care_report = json.loads((site / "api" / "care-guides-v21.json").read_text(encoding="utf-8"))
            self.assertEqual(care_report["publication_gate_version"], 246)
            self.assertEqual(care_report["content_release_version"], 246)
            self.assertEqual(care_report["blocked_review_slugs"], [BLOCKED_SLUG])
            self.assertFalse(care_report["needs_specialist_review_published"])
            self.assertFalse(care_report["autism_published"])
            self.assertEqual(care_report["source_guides"], 101)
            self.assertEqual(care_report["core_guides"], 101)
            self.assertEqual(care_report["published_core_guides"], 100)
            self.assertTrue(care_report["minimum_published_guides_met"])

            journey = json.loads((site / "api" / "care-guides-homepage-v21.json").read_text(encoding="utf-8"))
            self.assertFalse(journey["autism_published"])
            self.assertFalse(journey["autism_inbound_from_care_hub"])
            self.assertTrue(journey["blocked_review_links_removed"])
            self.assertTrue(journey["no_blocked_review_routes"])
            self.assertTrue(journey["idempotent_blocks"])


if __name__ == "__main__":
    unittest.main()
