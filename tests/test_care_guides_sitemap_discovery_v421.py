from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_care_guides_v21 as publisher


class CareGuidesSitemapDiscoveryV421(unittest.TestCase):
    def test_discovers_materialized_pages_not_present_in_previous_sitemap(self) -> None:
        original_site = publisher.implementation.SITE
        with tempfile.TemporaryDirectory() as temp_dir:
            site = Path(temp_dir)
            (site / "care-guides" / "legacy-guide").mkdir(parents=True)
            (site / "care-guides" / "legacy-guide" / "index.html").write_text("<h1>legacy</h1>", encoding="utf-8")
            (site / "care-guides" / "clinical-literacy" / "new-wave-page").mkdir(parents=True)
            (site / "care-guides" / "clinical-literacy" / "new-wave-page" / "index.html").write_text("<h1>new</h1>", encoding="utf-8")
            (site / "care-guides" / "index.html").write_text("<h1>hub</h1>", encoding="utf-8")

            publisher.implementation.SITE = site
            try:
                urls = publisher._discover_existing_care_guide_urls()
            finally:
                publisher.implementation.SITE = original_site

        self.assertEqual(
            urls,
            [
                "https://healthrenewal.org/care-guides/clinical-literacy/new-wave-page/",
                "https://healthrenewal.org/care-guides/legacy-guide/",
            ],
        )


if __name__ == "__main__":
    unittest.main()
