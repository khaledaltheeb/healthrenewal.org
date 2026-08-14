from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import care_guides_catalog_v246 as catalog  # noqa: E402
import care_guides_wave_v401_fixed as wave  # noqa: E402


class CareGuidesWaveV401SourceTests(unittest.TestCase):
    def test_specs_have_required_fields_and_registered_contracts(self):
        topics = wave.topics()
        self.assertEqual(len(topics), 50)
        for topic in topics:
            self.assertEqual(len(topic), 9)
            self.assertTrue(topic[0])
            self.assertTrue(topic[1])
            self.assertTrue(topic[3])
            self.assertEqual(len(topic[4].split("|")), 3)
            self.assertTrue(topic[5])
            self.assertTrue(topic[6])
            self.assertTrue(topic[7])
            self.assertEqual(topic[2], topic[2].strip(), topic[0])
            self.assertEqual(topic[8], topic[8].strip(), topic[0])
            self.assertIn(topic[2], catalog.CATEGORY_LABELS, topic[0])
            self.assertIn(topic[8], catalog.SOURCES, topic[0])
            self.assertGreaterEqual(len(catalog.SOURCES[topic[8]]), 3, topic[0])

    def test_expansion_aliases_resolve_to_relevant_registered_bundles(self):
        topics = {topic[0]: topic for topic in wave.topics()}
        self.assertEqual(topics["family-boundaries-substance-use-plan"][8], "substance")
        self.assertEqual(topics["digital-overuse-family-plan"][8], "gaming")
        self.assertEqual(topics["dementia-night-wandering-safety-plan"][8], "wandering")
        self.assertEqual(topics["dementia-bathing-support-protocol"][8], "dementia")
        self.assertEqual(topics["family-grief-support-routine-plan"][8], "grief")


if __name__ == "__main__":
    unittest.main()
