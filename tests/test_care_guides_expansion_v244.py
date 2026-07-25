from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_care_guides_v21.py"
V244_FILES = (
    ROOT / "content/v18/care-guides-suicide-risk-family-safety-plan-ar.json",
    ROOT / "content/v18/care-guides-substance-use-family-recovery-plan-ar.json",
    ROOT / "content/v18/care-guides-perinatal-mental-health-family-plan-ar.json",
    ROOT / "content/v18/care-guides-borderline-emotional-instability-family-plan-ar.json",
    ROOT / "content/v18/care-guides-dementia-behaviour-family-plan-ar.json",
    ROOT / "content/v18/care-guides-chronic-insomnia-family-sleep-plan-ar.json",
)
EXPECTED_SLUGS = {
    "suicide-risk-family-safety-plan",
    "substance-use-family-recovery-plan",
    "perinatal-mental-health-family-plan",
    "borderline-emotional-instability-family-plan",
    "dementia-behaviour-family-plan",
    "chronic-insomnia-family-sleep-plan",
}
TRUSTED_HOSTS = {"www.who.int", "www.nice.org.uk", "www.nhs.uk"}


class CareGuidesExpansionV244Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payloads = [json.loads(path.read_text(encoding="utf-8")) for path in V244_FILES]
        cls.guides = [guide for payload in cls.payloads for guide in payload.get("guides", [])]

    def test_payload_contract(self) -> None:
        self.assertEqual(len(self.payloads), 6)
        for path, payload in zip(V244_FILES, self.payloads):
            self.assertGreaterEqual(payload.get("version", 0), 244, path.name)
            self.assertEqual(payload.get("language"), "ar", path.name)
            self.assertEqual(len(payload.get("guides", [])), 1, path.name)

    def test_inventory_identity_and_depth(self) -> None:
        self.assertEqual(len(self.guides), 6)
        self.assertEqual({guide["slug"] for guide in self.guides}, EXPECTED_SLUGS)
        self.assertEqual(len({guide["title"] for guide in self.guides}), 6)
        for guide in self.guides:
            serialized = json.dumps(guide, ensure_ascii=False)
            word_count = len(re.findall(r"[\w\u0600-\u06ff]+", serialized, flags=re.UNICODE))
            actionable_items = sum(
                len(value)
                for key, value in guide.items()
                if isinstance(value, list) and key not in {"audience", "search_intent", "sources"}
            )
            self.assertGreaterEqual(word_count, 1400, guide["slug"])
            self.assertGreaterEqual(actionable_items, 90, guide["slug"])
            self.assertGreaterEqual(len(guide["summary"]), 170, guide["slug"])
            self.assertEqual(guide.get("review_status"), "internally-reviewed", guide["slug"])
            self.assertRegex(guide.get("reviewed_at", ""), r"^20\d{2}-\d{2}-\d{2}$")
            self.assertGreaterEqual(len(guide.get("when_to_seek_help", [])), 8, guide["slug"])
            self.assertGreaterEqual(len(guide.get("caregiver_plan", [])), 8, guide["slug"])
            self.assertTrue(guide.get("emergency_note"), guide["slug"])

    def test_sources_are_https_unique_and_institutional(self) -> None:
        for guide in self.guides:
            sources = guide.get("sources", [])
            self.assertGreaterEqual(len(sources), 3, guide["slug"])
            urls = [source["url"] for source in sources]
            self.assertEqual(len(urls), len(set(urls)), guide["slug"])
            for source in sources:
                parsed = urlparse(source["url"])
                self.assertEqual(parsed.scheme, "https", source)
                self.assertIn(parsed.netloc, TRUSTED_HOSTS, source)
                self.assertTrue(source.get("title"), source)
                self.assertTrue(source.get("publisher"), source)

    def test_safety_language_and_no_harmful_instructions(self) -> None:
        prohibited = (
            "معاقين",
            "تشخيص مؤكد",
            "يغني عن الطبيب",
            "بديل عن العلاج",
            "نتيجة نهائية",
            "اضمن عدم التكرار",
            "أوقف الدواء فورًا",
            "ارفع الجرعة",
            "لا تخبر الطبيب",
        )
        for guide in self.guides:
            text = json.dumps(guide, ensure_ascii=False)
            for phrase in prohibited:
                self.assertNotIn(phrase, text, guide["slug"])
            self.assertIn("خدمات الطوارئ المحلية", guide["emergency_note"], guide["slug"])
            self.assertIn("لا تترك الشخص وحده", guide["emergency_note"], guide["slug"])

        suicide = next(guide for guide in self.guides if guide["slug"] == "suicide-risk-family-safety-plan")
        suicide_text = json.dumps(suicide, ensure_ascii=False)
        for required in ("السؤال المباشر", "خطة الأمان", "لا تعد بسرية مطلقة", "لا تطلب وعدًا"):
            self.assertIn(required, suicide_text)
        for harmful_detail in ("جرعة قاتلة", "طريقة مضمونة", "اختر مكانًا مرتفعًا", "استخدم حبلًا"):
            self.assertNotIn(harmful_detail, suicide_text)

    def test_publisher_inventory_and_review_gate_contract(self) -> None:
        publisher = PUBLISHER.read_text(encoding="utf-8")
        for path in V244_FILES:
            self.assertIn(f'ROOT / "content/v18/{path.name}"', publisher)
        self.assertIn("EXPECTED_SOURCE_GUIDES = 20", publisher)
        self.assertIn("CONTENT_RELEASE_VERSION = 244", publisher)
        self.assertIn('BLOCKED_REVIEW_STATUSES = {"needs-specialist-review"}', publisher)
        self.assertIn("shutil.rmtree", publisher)
        self.assertIn('"needs_specialist_review_published": False', publisher)

        source_names = re.findall(r'ROOT / "content/v18/(care-guides-[^"]+\.json)"', publisher)
        self.assertEqual(len(source_names), 15)
        self.assertEqual(len(source_names), len(set(source_names)))


if __name__ == "__main__":
    unittest.main()
