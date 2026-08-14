from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import care_guides_catalog_v246 as catalog  # noqa: E402
import care_guides_wave_v400 as wave1  # noqa: E402
import care_guides_wave_v401_fixed as wave2  # noqa: E402
import care_guides_wave_v402 as wave3  # noqa: E402
import publish_care_guides_v246 as publisher  # noqa: E402


class CareGuidesWaveV402Tests(unittest.TestCase):
    def test_exactly_fifty_unique_topics(self) -> None:
        topics = wave3.topics()
        self.assertEqual(len(topics), 50)
        self.assertEqual(len({item[0] for item in topics}), 50)
        self.assertEqual(len({item[1] for item in topics}), 50)
        for item in topics:
            self.assertEqual(len(item), 9)
            self.assertRegex(item[0], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertGreaterEqual(len(item[3]), 80, item[0])
            self.assertEqual(len(item[4].split("|")), 3, item[0])
            self.assertEqual(item[2], item[2].strip(), item[0])
            self.assertEqual(item[8], item[8].strip(), item[0])
            self.assertIn(item[2], catalog.CATEGORY_LABELS, item[0])
            self.assertIn(item[8], catalog.SOURCES, item[0])
            self.assertGreaterEqual(len(catalog.SOURCES[item[8]]), 3, item[0])

    def test_contextual_source_resolution_is_topic_relevant(self) -> None:
        topics = {item[0]: item for item in wave3.topics()}
        self.assertEqual(topics["family-screen-time-transition-plan"][8], "gaming")
        self.assertEqual(topics["child-separation-anxiety-dropoff-plan"][8], "anxiety")
        self.assertEqual(topics["adhd-email-overload-triage-plan"][8], "work")
        self.assertEqual(topics["dementia-new-caregiver-first-week-plan"][8], "dementia")
        self.assertEqual(topics["care-home-transition-familiar-items-plan"][8], "dementia")

    def test_no_slug_or_title_collision_with_previous_waves(self) -> None:
        previous = [*wave1.topics(), *wave2.topics()]
        current = wave3.topics()
        self.assertTrue({x[0] for x in previous}.isdisjoint({x[0] for x in current}))
        self.assertTrue({x[1] for x in previous}.isdisjoint({x[1] for x in current}))

    def test_install_reaches_expected_cumulative_contract(self) -> None:
        report = wave3.install(publisher)
        self.assertEqual(report["added_guides"], 50)
        self.assertEqual(report["cumulative_wave_guides"], 150)
        self.assertEqual(report["expected_institutional_guides"], 237)
        self.assertEqual(report["expected_source_guides"], 251)
        self.assertEqual(report["minimum_published_guides"], 250)
        self.assertEqual(report["unique_slugs"], 50)
        self.assertEqual(report["unique_titles"], 50)
        self.assertGreaterEqual(report["minimum_sources"], 3)
        self.assertFalse(report["specialist_review_claimed"])
        self.assertEqual(len(catalog.institutional_guides()), 237)

    def test_generated_guides_preserve_depth_and_safety_contract(self) -> None:
        wave3.install(publisher)
        slugs = {item[0] for item in wave3.topics()}
        guides = [guide for guide in catalog.institutional_guides() if guide["slug"] in slugs]
        self.assertEqual(len(guides), 50)
        for guide in guides:
            words = len(re.findall(r"[\w\u0600-\u06ff]+", str(guide), flags=re.UNICODE))
            self.assertGreaterEqual(words, 850, guide["slug"])
            self.assertGreaterEqual(len(guide.get("sources", [])), 3, guide["slug"])
            self.assertTrue(guide.get("emergency_note"), guide["slug"])
            self.assertEqual(guide.get("review_status"), "internally-reviewed", guide["slug"])


if __name__ == "__main__":
    unittest.main()
