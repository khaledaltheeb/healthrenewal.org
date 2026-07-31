from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_trust_guides_v201.py"
FINALIZER = ROOT / "scripts" / "finalize_trust_guides_links_v201.py"


class TrustGuideLinkCompatibilityV201Tests(unittest.TestCase):
    def test_legacy_blog_link_maps_to_live_magazine_route(self) -> None:
        site = Path(tempfile.mkdtemp(prefix="trust-links-v201-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "trust").mkdir(parents=True)
        (site / "magazine").mkdir(parents=True)
        for relative in ("trust/index.html", "magazine/index.html"):
            (site / relative).write_text(
                '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>صفحة</h1></main></body></html>',
                encoding="utf-8",
            )
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            encoding="utf-8",
        )
        subprocess.run(["python3", str(PUBLISHER), str(site)], cwd=ROOT, check=True)
        subprocess.run(["python3", str(FINALIZER), str(site)], cwd=ROOT, check=True)

        page = site / "guides/source-citation-and-update-transparency/index.html"
        text = page.read_text(encoding="utf-8")
        self.assertNotIn('href="/blog/"', text)
        self.assertIn('href="/magazine/"', text)

        report = json.loads((site / "api/trust-guides-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["link_compatibility"]["active_route"], "/magazine/")
        self.assertEqual(report["link_compatibility"]["remaining_legacy_links"], [])


if __name__ == "__main__":
    unittest.main()
