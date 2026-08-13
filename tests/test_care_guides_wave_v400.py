from __future__ import annotations

import re
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import care_guides_catalog_v246 as catalog  # noqa: E402
import care_guides_wave_v400 as wave  # noqa: E402
import publish_care_guides_v246 as publisher  # noqa: E402


class CareGuidesWaveV400Tests(unittest.TestCase):
    def test_wave_has_exactly_fifty_unique_specs(self) -> None:
        topics = wave.topics()
        self.assertEqual(len(topics), 50)
        self.assertEqual(len({topic[0] for topic in topics}), 50)
        self.assertEqual(len({topic[1] for topic in topics}), 50)
        for topic in topics:
            self.assertEqual(len(topic), 9)
            self.assertRegex(topic[0], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertGreaterEqual(len(topic[3]), 90, topic[0])
            self.assertEqual(len(topic[4].split("|")), 3, topic[0])
            self.assertTrue(topic[5].strip(), topic[0])
            self.assertTrue(topic[6].strip(), topic[0])
            self.assertTrue(topic[7].strip(), topic[0])

    def test_wave_extends_existing_catalog_without_collisions(self) -> None:
        existing = catalog.institutional_guides()
        existing_slugs = {guide["slug"] for guide in existing}
        existing_titles = {guide["title"] for guide in existing}
        additions = wave.topics()
        self.assertTrue(existing_slugs.isdisjoint({topic[0] for topic in additions}))
        self.assertTrue(existing_titles.isdisjoint({topic[1] for topic in additions}))

    def test_install_generates_137_institutional_and_151_source_guides(self) -> None:
        report = wave.install(publisher)
        self.assertEqual(report["added_guides"], 50)
        self.assertEqual(report["expected_institutional_guides"], 137)
        self.assertEqual(report["expected_source_guides"], 151)
        self.assertEqual(report["minimum_published_guides"], 150)
        self.assertEqual(report["unique_slugs"], 50)
        self.assertEqual(report["unique_titles"], 50)
        self.assertGreaterEqual(report["minimum_sources"], 3)
        self.assertFalse(report["specialist_review_claimed"])
        self.assertEqual(len(catalog.institutional_guides()), 137)
        self.assertEqual(publisher.EXPECTED_INSTITUTIONAL_GUIDES, 137)
        self.assertEqual(publisher.EXPECTED_SOURCE_GUIDES, 151)
        self.assertEqual(publisher.MINIMUM_PUBLISHED_GUIDES, 150)

    def test_generated_wave_preserves_depth_safety_and_source_contract(self) -> None:
        wave.install(publisher)
        wave_slugs = {topic[0] for topic in wave.topics()}
        guides = [guide for guide in catalog.institutional_guides() if guide["slug"] in wave_slugs]
        self.assertEqual(len(guides), 50)
        categories = Counter(guide["category"] for guide in guides)
        self.assertGreaterEqual(len(categories), 6)
        for guide in guides:
            words = len(re.findall(r"[\w\u0600-\u06ff]+", str(guide), flags=re.UNICODE))
            actionable = sum(
                len(value)
                for key, value in guide.items()
                if isinstance(value, list) and key not in {"audience", "search_intent", "sources"}
            )
            self.assertGreaterEqual(words, 900, guide["slug"])
            self.assertGreaterEqual(actionable, 60, guide["slug"])
            self.assertGreaterEqual(len(guide["sources"]), 3, guide["slug"])
            self.assertEqual(guide["review_status"], "internally-reviewed", guide["slug"])
            self.assertEqual(guide["editorial_review"], "structural-and-source-review", guide["slug"])
            self.assertGreaterEqual(len(guide["when_to_seek_help"]), 8, guide["slug"])
            self.assertGreaterEqual(len(guide["caregiver_plan"]), 6, guide["slug"])
            self.assertTrue(guide["emergency_note"], guide["slug"])


if __name__ == "__main__":
    unittest.main()
