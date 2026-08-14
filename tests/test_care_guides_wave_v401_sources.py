from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import care_guides_wave_v401_fixed as wave
class CareGuidesWaveV401SourceTests(unittest.TestCase):
    def test_specs_have_required_fields(self):
        for topic in wave.topics():
            self.assertEqual(len(topic), 9)
            self.assertTrue(topic[0])
            self.assertTrue(topic[1])
            self.assertTrue(topic[3])
            self.assertEqual(len(topic[4].split("|")), 3)
            self.assertTrue(topic[5])
            self.assertTrue(topic[6])
            self.assertTrue(topic[7])
if __name__ == "__main__":
    unittest.main()
