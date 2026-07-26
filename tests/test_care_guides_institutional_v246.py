from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from care_guides_catalog_v246 import CATALOG_VERSION, EXPECTED_GUIDES, institutional_guides  # noqa: E402
from enhance_care_guides_v246 import (  # noqa: E402
    CATEGORY_RULES,
    ENHANCEMENT_VERSION,
    deduplicate_meta_tags,
    duplicate_meta_keys,
)

LEGACY_FILES = (
    ROOT / "content/v18/care-guides-ar.json",
    ROOT / "content/v18/care-guides-adhd-ar.json",
    ROOT / "content/v18/care-guides-autism-ar.json",
    ROOT / "content/v18/care-guides-family-anxiety-panic-support-ar.json",
    ROOT / "content/v18/care-guides-family-ocd-support-ar.json",
    ROOT / "content/v18/care-guides-bipolar-family-early-warning-plan-ar.json",
    ROOT / "content/v18/care-guides-trauma-ptsd-family-support-ar.json",
    ROOT / "content/v18/care-guides-eating-disorder-family-support-ar.json",
    ROOT / "content/v18/care-guides-self-harm-family-safety-support-ar.json",
)
EXPECTED_DISTRIBUTION = {
    "crisis": 10, "mood": 12, "children": 12, "neurodevelopment": 20,
    "services": 10, "older": 10, "addictions": 8, "daily": 5,
}
TRUSTED_HOSTS = {
    "www.who.int", "www.nice.org.uk", "cks.nice.org.uk", "www.nhs.uk", "www.cdc.gov",
    "www.nimh.nih.gov", "www.nia.nih.gov", "www.nidcd.nih.gov", "www.nhlbi.nih.gov",
    "www.unicef.org", "www.ptsd.va.gov", "store.samhsa.gov",
}


class CareGuidesInstitutionalV246Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guides = institutional_guides()

    def test_catalog_count_distribution_and_identity(self) -> None:
        self.assertEqual((CATALOG_VERSION, EXPECTED_GUIDES, len(self.guides)), (246, 87, 87))
        self.assertEqual(Counter(guide["category"] for guide in self.guides), EXPECTED_DISTRIBUTION)
        self.assertEqual(len({guide["slug"] for guide in self.guides}), 87)
        self.assertEqual(len({guide["title"] for guide in self.guides}), 87)
        self.assertEqual(len({guide["summary"] for guide in self.guides}), 87)

    def test_every_guide_meets_depth_actionability_and_safety_contract(self) -> None:
        for guide in self.guides:
            joined = json.dumps(guide, ensure_ascii=False)
            words = len(re.findall(r"[\w\u0600-\u06ff]+", joined, flags=re.UNICODE))
            actionable = sum(
                len(value)
                for key, value in guide.items()
                if isinstance(value, list) and key not in {"audience", "search_intent", "sources"}
            )
            self.assertRegex(guide["slug"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertGreaterEqual(words, 900, guide["slug"])
            self.assertGreaterEqual(actionable, 60, guide["slug"])
            self.assertGreaterEqual(len(guide["summary"]), 150, guide["slug"])
            self.assertEqual(guide["review_status"], "internally-reviewed", guide["slug"])
            self.assertEqual(guide["editorial_review"], "structural-and-source-review", guide["slug"])
            self.assertEqual(guide["reviewed_at"], "2026-07-26", guide["slug"])
            self.assertGreaterEqual(len(guide["when_to_seek_help"]), 8, guide["slug"])
            self.assertGreaterEqual(len(guide["caregiver_plan"]), 6, guide["slug"])
            self.assertTrue(guide["emergency_note"], guide["slug"])
            self.assertEqual(len(guide["sources"]), 3, guide["slug"])
            self.assertEqual(len(guide["understanding"]), len(set(guide["understanding"])), guide["slug"])
            self.assertEqual(len(guide["do"]), len(set(guide["do"])), guide["slug"])
            for source in guide["sources"]:
                parsed = urlparse(source["url"])
                self.assertEqual(parsed.scheme, "https", source)
                self.assertIn(parsed.netloc, TRUSTED_HOSTS, source)
            for prohibited in ("معاقين", "يغني عن الطبيب", "بديل عن العلاج", "نتيجة نهائية", "مضمون 100%"):
                self.assertNotIn(prohibited, joined, guide["slug"])

    def test_source_and_publication_minimum(self) -> None:
        legacy: list[dict] = []
        for path in LEGACY_FILES:
            legacy.extend(json.loads(path.read_text(encoding="utf-8")).get("guides", []))
        self.assertEqual(len(legacy), 14)
        combined = [*legacy, *self.guides]
        self.assertEqual(len(combined), 101)
        self.assertEqual(len({guide["slug"] for guide in combined}), 101)
        blocked = [guide for guide in combined if guide.get("review_status") == "needs-specialist-review"]
        self.assertEqual([guide["slug"] for guide in blocked], ["autism-family-practical-guide"])
        self.assertEqual(len([guide for guide in combined if guide not in blocked]), 100)

    def test_metadata_deduplication_keeps_one_authoritative_tag(self) -> None:
        with tempfile.TemporaryDirectory(prefix="care-meta-v246-") as temp:
            path = Path(temp) / "index.html"
            path.write_text(
                '<html><head><meta name="description" content="الأول">'
                '<meta name="description" content="الثاني">'
                '<meta property="og:title" content="الأول">'
                '<meta property="og:title" content="الثاني">'
                '<meta name="robots" content="index,follow"></head><body></body></html>',
                encoding="utf-8",
            )
            self.assertEqual(deduplicate_meta_tags(path), 2)
            self.assertEqual(duplicate_meta_keys(path), [])
            text = path.read_text(encoding="utf-8")
            self.assertIn('content="الأول"', text)
            self.assertNotIn('content="الثاني"', text)

    def test_publisher_and_enhancer_contracts(self) -> None:
        publisher = (SCRIPTS / "publish_care_guides_v246.py").read_text(encoding="utf-8")
        compatibility = (SCRIPTS / "publish_care_guides_v21.py").read_text(encoding="utf-8")
        for contract in (
            "EXPECTED_SOURCE_GUIDES = 101", "MINIMUM_PUBLISHED_GUIDES = 100",
            "word_count(guide) < 900", "actionable_count(guide) < 60",
            "TRUSTED_SOURCE_HOSTS", "needs_specialist_review_published",
        ):
            self.assertIn(contract, publisher)
        self.assertIn("publish_care_guides_v246", compatibility)
        self.assertEqual(ENHANCEMENT_VERSION, 246)
        self.assertEqual(len(CATEGORY_RULES), 8)


if __name__ == "__main__":
    unittest.main()
