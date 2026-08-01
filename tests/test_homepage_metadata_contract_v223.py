from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
