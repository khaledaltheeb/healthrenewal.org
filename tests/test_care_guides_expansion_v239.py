from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXPANDED_FILES = tuple(sorted((ROOT / "content/v18").glob("care-guides-*-support-ar.json"))) + (
    ROOT / "content/v18/care-guides-bipolar-family-early-warning-plan-ar.json",
)
SOURCE_FILES = (
    ROOT / "content/v18/care-guides-ar.json",
    ROOT / "content/v18/care-guides-adhd-ar.json",
    ROOT / "content/v18/care-guides-autism-ar.json",
    *EXPANDED_FILES,
)
EXPECTED_SLUGS = {
    "family-anxiety-panic-support",
    "family-ocd-support",
    "bipolar-family-early-warning-plan",
    "trauma-ptsd-family-support",
    "eating-disorder-family-support",
    "self-harm-family-safety-support",
}
TRUSTED_HOSTS = {"www.who.int", "www.nice.org.uk", "www.nhs.uk"}


class CareGuidesExpansionV239Tests(unittest.TestCase):
    def test_expanded_guides_depth_sources_and_safety(self) -> None:
        self.assertEqual(len(EXPANDED_FILES), 6)
        guides: list[dict] = []
        for path in EXPANDED_FILES:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(payload.get("version", 0), 239)
            self.assertEqual(payload.get("language"), "ar")
            guides.extend(payload.get("guides", []))
        self.assertEqual(len(guides), 6)
        self.assertEqual({guide["slug"] for guide in guides}, EXPECTED_SLUGS)
        self.assertEqual(len({guide["title"] for guide in guides}), len(guides))

        for guide in guides:
            joined = json.dumps(guide, ensure_ascii=False)
            word_count = len(re.findall(r"[\w\u0600-\u06ff]+", joined, flags=re.UNICODE))
            actionable_items = sum(
                len(value)
                for key, value in guide.items()
                if isinstance(value, list) and key not in {"audience", "search_intent", "sources"}
            )
            self.assertGreaterEqual(word_count, 900, guide["slug"])
            self.assertGreaterEqual(actionable_items, 60, guide["slug"])
            self.assertGreaterEqual(len(guide["summary"]), 170, guide["slug"])
            self.assertEqual(guide.get("review_status"), "internally-reviewed", guide["slug"])
            self.assertRegex(guide.get("reviewed_at", ""), r"^20\d{2}-\d{2}-\d{2}$")
            self.assertGreaterEqual(len(guide.get("sources", [])), 3, guide["slug"])
            self.assertTrue(guide.get("emergency_note"), guide["slug"])
            self.assertGreaterEqual(len(guide.get("when_to_seek_help", [])), 8, guide["slug"])
            self.assertGreaterEqual(len(guide.get("caregiver_plan", [])), 6, guide["slug"])

            for source in guide["sources"]:
                parsed = urlparse(source["url"])
                self.assertEqual(parsed.scheme, "https", source)
                self.assertIn(parsed.netloc, TRUSTED_HOSTS, source)

            for prohibited in (
                "تشخيص مؤكد",
                "يغني عن الطبيب",
                "بديل عن العلاج",
                "نتيجة نهائية",
                "معاقين",
                "اضمن عدم التكرار",
            ):
                self.assertNotIn(prohibited, joined, guide["slug"])

    def test_legacy_inventory_and_v246_publication_gate(self) -> None:
        all_guides: list[dict] = []
        for path in SOURCE_FILES:
            payload = json.loads(path.read_text(encoding="utf-8"))
            all_guides.extend(payload.get("guides", []))
        self.assertEqual(len(all_guides), 14)
        slugs = [guide["slug"] for guide in all_guides]
        self.assertEqual(len(slugs), len(set(slugs)))
        blocked = [guide for guide in all_guides if guide.get("review_status") == "needs-specialist-review"]
        self.assertEqual([guide["slug"] for guide in blocked], ["autism-family-practical-guide"])
        self.assertTrue(EXPECTED_SLUGS.isdisjoint({guide["slug"] for guide in blocked}))

        compatibility = (ROOT / "scripts/publish_care_guides_v21.py").read_text(encoding="utf-8")
        publisher = (ROOT / "scripts/publish_care_guides_v246.py").read_text(encoding="utf-8")
        self.assertIn("publish_care_guides_v246", compatibility)
        for path in EXPANDED_FILES:
            self.assertIn(f'ROOT / "content/v18/{path.name}"', publisher)
        self.assertIn("EXPECTED_LEGACY_SOURCE_GUIDES = 14", publisher)
        self.assertIn("EXPECTED_SOURCE_GUIDES = 101", publisher)
        self.assertIn("MINIMUM_PUBLISHED_GUIDES = 100", publisher)
        self.assertIn("CONTENT_RELEASE_VERSION = 246", publisher)


if __name__ == "__main__":
    unittest.main()
