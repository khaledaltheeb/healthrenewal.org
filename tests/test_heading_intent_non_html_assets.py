from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import enforce_sitewide_heading_intent_v2 as heading  # noqa: E402


class HeadingIntentNonHtmlAssetTests(unittest.TestCase):
    def test_known_non_html_resources_are_not_heading_targets_but_unknown_routes_still_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sitemap = root / "sitemap.xml"
            sitemap.write_text(
                """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
  <url><loc>https://healthrenewal.org/guide/</loc></url>
  <url><loc>https://healthrenewal.org/assets/card.png</loc></url>
  <url><loc>https://healthrenewal.org/assets/photo.webp</loc></url>
  <url><loc>https://healthrenewal.org/api/v1/resource.json</loc></url>
  <url><loc>https://healthrenewal.org/api/unknown.bin</loc></url>
</urlset>
""",
                encoding="utf-8",
            )

            targets, unsupported = heading.discover_targets(root, sitemap, heading.DEFAULT_BASE_URLS)

            self.assertEqual([target.route for target in targets], ["/guide/"])
            self.assertEqual(unsupported, ["https://healthrenewal.org/api/unknown.bin"])


if __name__ == "__main__":
    unittest.main()
