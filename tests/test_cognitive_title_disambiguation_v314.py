from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PUBLISHER_SCRIPT = SCRIPTS / "publish_cognitive_sectors_v246.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_cognitive_sectors_v246 as publisher


class CognitiveTitleDisambiguationV314Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="cognitive-title-v314-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        page = self.site / publisher.LEGACY_ROUTE
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            "<!doctype html><html lang=\"ar\" dir=\"rtl\"><head>"
            "<title>التناظر اللفظي | منصة روافد</title>"
            "<meta property=\"og:title\" content=\"التناظر اللفظي | منصة روافد\">"
            "<meta content=\"التناظر اللفظي | منصة روافد\" name=\"twitter:title\">"
            "<script type=\"application/ld+json\">{\"@context\":\"https://schema.org\",\"name\":\"التناظر اللفظي\"}</script>"
            "</head><body><main><h1>التناظر اللفظي</h1><p>محتوى المهمة التراثية.</p></main></body></html>",
            encoding="utf-8",
        )
        report = self.site / publisher.REPORT_PATH
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "version": 246,
                    "status": "passed",
                    "legacy_pages": [
                        {
                            "path": publisher.LEGACY_ROUTE,
                            "slug": publisher.LEGACY_SLUG,
                            "title": publisher.LEGACY_OLD_TITLE,
                        }
                    ],
                    "modern_pages": [
                        {
                            "path": "cognitive-lab/verbal-analogy/index.html",
                            "slug": "verbal-analogy",
                            "title": publisher.LEGACY_OLD_TITLE,
                        }
                    ],
                    "contracts": {"complete_inventory": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_core_self_test_does_not_treat_flag_as_a_site_path(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PUBLISHER_SCRIPT), "--self-test"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertFalse((ROOT / "--self-test").exists())

    def test_only_legacy_route_gets_a_unique_title_and_report_evidence(self) -> None:
        first = publisher.disambiguate_legacy_verbal_analogy(self.site)
        second = publisher.disambiguate_legacy_verbal_analogy(self.site)
        self.assertEqual(first["new_title"], publisher.LEGACY_NEW_TITLE)
        self.assertEqual(second["new_title"], publisher.LEGACY_NEW_TITLE)

        page = (self.site / publisher.LEGACY_ROUTE).read_text(encoding="utf-8")
        full_title = (
            publisher.LEGACY_NEW_TITLE
            + " | منصة روافد"
        )
        self.assertEqual(page.count(f"<title>{full_title}</title>"), 1)
        self.assertEqual(page.count(f"<h1>{publisher.LEGACY_NEW_TITLE}</h1>"), 1)
        self.assertEqual(page.count(f'content="{full_title}"'), 2)
        self.assertIn(f'"name":"{publisher.LEGACY_NEW_TITLE}"', page)
        self.assertNotIn(
            "<title>التناظر اللفظي | منصة روافد</title>",
            page,
        )

        report = json.loads(
            (self.site / publisher.REPORT_PATH).read_text(encoding="utf-8")
        )
        legacy = next(item for item in report["legacy_pages"] if item["slug"] == publisher.LEGACY_SLUG)
        modern = next(item for item in report["modern_pages"] if item["slug"] == "verbal-analogy")
        self.assertEqual(legacy["title"], publisher.LEGACY_NEW_TITLE)
        self.assertEqual(modern["title"], publisher.LEGACY_OLD_TITLE)
        self.assertEqual(report["title_disambiguation_version"], 314)
        self.assertTrue(report["contracts"]["legacy_verbal_analogy_title_disambiguated"])


if __name__ == "__main__":
    unittest.main()
