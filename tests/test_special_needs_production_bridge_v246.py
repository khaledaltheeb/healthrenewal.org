from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_special_needs_hub_v201.py"
FINALIZER = ROOT / "scripts" / "finalize_special_needs_hub_accessibility_v201.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpecialNeedsProductionBridgeV246Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="special-needs-production-bridge-v246-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body><main>'
            '<h1>بوابة قديمة</h1><section><h2>مصادر الوحدة الحالية</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        for name in ("sitemap.xml", "sitemap-special-needs.xml"):
            (self.site / name).write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
                encoding="utf-8",
            )
        (self.site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n"
            f"Sitemap: {BASE}/sitemap.xml\n",
            encoding="utf-8",
        )

    def run_bridge(self) -> None:
        for script in (PUBLISHER, FINALIZER):
            result = subprocess.run(
                ["python3", str(script), str(self.site)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_legacy_entrypoints_publish_and_preserve_institutional_hub(self) -> None:
        self.run_bridge()

        report = json.loads(
            (self.site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8")
        )
        compatibility = json.loads(
            (self.site / "api/special-needs-hub-v201.json").read_text(encoding="utf-8")
        )
        source = (self.site / "special-needs/index.html").read_text(encoding="utf-8")

        self.assertEqual(report["version"], 221)
        self.assertEqual(report["hub_release"], 241)
        self.assertEqual(report["guide_count"], 25)
        self.assertEqual(report["hub"]["source_count"], 10)
        self.assertEqual(report["hub"]["jordan_source_count"], 3)
        self.assertTrue(report["hub"]["jordan_context_section"])

        self.assertEqual(compatibility["status"], "production-integrated")
        self.assertEqual(compatibility["superseded_by"], 243)
        self.assertEqual(
            compatibility["search_accessibility"]["mode"],
            "static-semantic-navigation",
        )
        self.assertFalse(compatibility["search_accessibility"]["search_input_required"])
        self.assertEqual(
            compatibility["legacy_accessibility_finalizer"],
            "institutional-v243-no-op",
        )

        for marker in (
            "pathway-communication",
            "data-special-needs-jordan-context-v241",
            "مصفوفة قرار سريعة",
            "معايير جودة الخطة أو الخدمة",
            "المنهجية التحريرية وحدود الاستخدام",
            "prefers-reduced-motion",
            "prefers-contrast:more",
            "@media print",
        ):
            self.assertIn(marker, source)
        self.assertNotIn('id="hub-search"', source)

        for slug in report["guide_slugs"]:
            route = f"/pterminology-site/special-needs/{slug}/"
            self.assertEqual(source.count(route), 1, slug)

    def test_bridge_and_finalizer_are_idempotent(self) -> None:
        self.run_bridge()
        tracked = (
            self.site / "special-needs/index.html",
            self.site / "api/special-needs-guides-v221.json",
            self.site / "api/special-needs-hub-v201.json",
            self.site / "robots.txt",
            self.site / "sitemap.xml",
            self.site / "sitemap-special-needs.xml",
        )
        before = [digest(path) for path in tracked]
        self.run_bridge()
        after = [digest(path) for path in tracked]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
