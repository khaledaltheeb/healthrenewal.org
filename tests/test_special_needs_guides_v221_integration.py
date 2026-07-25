from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_special_needs_guides_v217.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
VERSIONS = (209, 210, 211, 212, 214)


class SpecialNeedsGuidesV221Integration(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="special-needs-v221-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body><main>'
            '<section><h1>مركز ذوي الاحتياجات الخاصة</h1></section>'
            '<section class="review"><h2>المراجعة</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        for name in ("sitemap.xml", "sitemap-special-needs.xml"):
            (self.site / name).write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
                encoding="utf-8",
            )

    def run_publisher(self) -> dict:
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8"))

    def test_all_five_batches_are_published_discoverable_and_idempotent(self) -> None:
        first = self.run_publisher()
        self.assertEqual(first["version"], 221)
        self.assertEqual(first["batches"], list(VERSIONS))
        self.assertEqual(first["batch_count"], 5)
        self.assertEqual(first["guide_count"], 25)
        self.assertEqual(first["production_source_file_count"], 25)
        self.assertEqual(first["production_source_manifest"], "content/v221/special-needs-guides-production-manifest-ar.json")
        self.assertEqual(len(first["guide_slugs"]), 25)
        self.assertEqual(len(set(first["guide_slugs"])), 25)
        self.assertEqual(first["hub_linked_guides"], 25)
        self.assertEqual(first["review_status"], "internally-reviewed")
        self.assertFalse(first["external_review_completed"])

        hub_path = self.site / "special-needs/index.html"
        hub = hub_path.read_text(encoding="utf-8")
        self.assertEqual(hub.count('id="special-needs-guide-library-v221"'), 1)
        self.assertEqual(hub.count("special-needs-guide-library-v221:insert"), 1)
        for version in VERSIONS:
            self.assertEqual(hub.count(f"special-needs-guides-v{version}:start"), 1)
            self.assertEqual(hub.count(f"special-needs-guides-v{version}:end"), 1)
        for slug in first["guide_slugs"]:
            self.assertTrue((self.site / "special-needs" / slug / "index.html").is_file())
            self.assertEqual(hub.count(f'/pterminology-site/special-needs/{slug}/'), 1)

        locations = [
            node.text
            for node in ET.parse(self.site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        expected = {f"{BASE}/special-needs/{slug}/" for slug in first["guide_slugs"]}
        self.assertTrue(expected.issubset(set(locations)))
        self.assertEqual(len(locations), len(set(locations)))

        tracked = [
            hub_path,
            self.site / "sitemap.xml",
            self.site / "sitemap-special-needs.xml",
            self.site / "api/special-needs-guides-v217.json",
            self.site / "api/special-needs-guides-v221.json",
        ]
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
        second = self.run_publisher()
        after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
        self.assertEqual(second["guide_count"], 25)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
