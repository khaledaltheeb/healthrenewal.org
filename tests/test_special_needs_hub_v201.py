from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_special_needs_hub_v201.py"
FINALIZER = ROOT / "scripts" / "finalize_special_needs_hub_accessibility_v201.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site"


class SpecialNeedsHubV201CompatibilityTests(unittest.TestCase):
    """Keep the historical test entrypoint while enforcing the current v243 output."""

    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="special-needs-v201-compat-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "special-needs").mkdir(parents=True)
        (site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body><main>'
            '<h1>مركز قديم</h1><section><h2>مصادر الوحدة الحالية</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        for name in ("sitemap.xml", "sitemap-special-needs.xml"):
            (site / name).write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
                encoding="utf-8",
            )
        (site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n"
            f"Sitemap: {BASE}/sitemap.xml\n",
            encoding="utf-8",
        )
        return site

    def publish(self, site: Path) -> None:
        for script in (SCRIPT, FINALIZER):
            completed = subprocess.run(
                ["python3", str(script), str(site)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_historical_entrypoint_publishes_current_institutional_hub(self) -> None:
        site = self.make_site()
        self.publish(site)
        source = (site / "special-needs/index.html").read_text(encoding="utf-8")
        report = json.loads(
            (site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8")
        )
        compatibility = json.loads(
            (site / "api/special-needs-hub-v201.json").read_text(encoding="utf-8")
        )

        self.assertIn("منصة الصحة النفسية وذوي الاحتياجات الخاصة", source)
        self.assertIn("معرفة تحترم الإنسان. دعم يوسّع الإمكانات.", source)
        self.assertEqual(source.count("<h1"), 1)
        self.assertIn("pathway-communication", source)
        self.assertIn("data-special-needs-jordan-context-v241", source)
        self.assertIn("مصفوفة قرار سريعة", source)
        self.assertIn("معايير جودة الخطة أو الخدمة", source)
        self.assertIn("المنهجية التحريرية وحدود الاستخدام", source)
        self.assertIn("application/ld+json", source)
        self.assertIn("prefers-reduced-motion", source)
        self.assertIn("prefers-contrast:more", source)
        self.assertIn("@media print", source)
        self.assertNotIn('id="hub-search"', source)
        self.assertNotIn("قيد الإعداد", source)
        self.assertNotIn("قيد التوسع", source)

        self.assertEqual(report["version"], 221)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["hub_release"], 241)
        self.assertEqual(report["guide_count"], 25)
        self.assertEqual(report["batch_count"], 5)
        self.assertEqual(report["hub"]["pathway_count"], 8)
        self.assertEqual(report["hub"]["source_count"], 10)
        self.assertEqual(report["hub"]["jordan_source_count"], 3)
        self.assertTrue(report["hub"]["jordan_context_section"])

        self.assertEqual(compatibility["status"], "production-integrated")
        self.assertEqual(compatibility["superseded_by"], 243)
        self.assertEqual(compatibility["existing_resources"], 25)
        self.assertEqual(compatibility["source_count"], 10)
        self.assertEqual(
            compatibility["search_accessibility"]["mode"],
            "static-semantic-navigation",
        )
        self.assertFalse(compatibility["search_accessibility"]["search_input_required"])

        for slug in report["guide_slugs"]:
            route = f"/pterminology-site/special-needs/{slug}/"
            self.assertEqual(source.count(route), 1, slug)

    def test_historical_entrypoint_does_not_emit_unpublished_resource_links(self) -> None:
        site = self.make_site()
        self.publish(site)
        source = (site / "special-needs/index.html").read_text(encoding="utf-8")
        report = json.loads(
            (site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8")
        )
        published = set(report["guide_slugs"])

        self.assertEqual(len(published), 25)
        emitted_guide_hrefs = sum(
            source.count(f'href="/pterminology-site/special-needs/{slug}/"')
            for slug in published
        )
        self.assertEqual(emitted_guide_hrefs, 25)
        for unavailable in (
            "caregiver-wellbeing",
            "accessible-arabic-digital-content",
            "unpublished-placeholder-guide",
        ):
            if unavailable not in published:
                self.assertNotIn(
                    f'href="/pterminology-site/special-needs/{unavailable}/"',
                    source,
                )


if __name__ == "__main__":
    unittest.main()
