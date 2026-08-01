from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts import apply_homepage_v20 as publisher


ROOT = Path(__file__).resolve().parents[1]


class HomepageMetadataContractV223Tests(unittest.TestCase):
    def test_current_homepage_has_no_meta_keywords(self) -> None:
        source = (ROOT / "index.html").read_text(encoding="utf-8")
        publisher.enforce_homepage_metadata_contract(source)

    def test_publisher_rejects_meta_keywords_regression(self) -> None:
        source = '<head><meta NAME = "keywords" content="obsolete"></head>'
        with self.assertRaisesRegex(
            SystemExit,
            "must not publish obsolete meta keywords metadata",
        ):
            publisher.enforce_homepage_metadata_contract(source)

    def test_publisher_no_longer_requires_meta_keywords(self) -> None:
        script = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("'name=\"keywords\"',", script)
        self.assertIn('"meta_keywords_absent": True', script)

    def test_publisher_heading_contract_matches_verified_homepage(self) -> None:
        source = (ROOT / "index.html").read_text(encoding="utf-8")
        counts = [len(re.findall(rf"<h{level}\b", source)) for level in (1, 2, 3)]
        self.assertEqual(counts[0], 1)
        self.assertGreaterEqual(counts[1], 5)
        self.assertGreaterEqual(sum(counts), 8)
        self.assertLessEqual(sum(counts), 20)
        script = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("at least sixteen H3 cards", script)
        self.assertIn('"heading_count": heading_count', script)


if __name__ == "__main__":
    unittest.main()
