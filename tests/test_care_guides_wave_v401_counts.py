from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import care_guides_wave_v401 as wave
class CareGuidesWaveV401CountTests(unittest.TestCase):
    def test_exactly_fifty_unique_topics(self):
        topics = wave.topics()
        self.assertEqual(len(topics), 50)
        self.assertEqual(len({item[0] for item in topics}), 50)
        self.assertEqual(len({item[1] for item in topics}), 50)
        self.assertTrue(all(len(item) == 9 for item in topics))
if __name__ == "__main__":
    unittest.main()
