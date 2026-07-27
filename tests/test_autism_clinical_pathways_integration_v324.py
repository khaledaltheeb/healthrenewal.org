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
AUDITOR = ROOT / "scripts" / "audit_unpublished_content_v201.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
SLUGS = (
    "autism-comprehensive-assessment-differential-diagnosis",
    "autism-late-diagnosis-adults-women-masking",
    "autism-aac-assessment-implementation",
    "autism-unsafe-unproven-treatments",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AutismClinicalPathwaysIntegrationV324(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="autism-clinical-v324-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "special-needs" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body><main>'
            '<section><h1>مركز ذوي الاحتياجات الخاصة</h1></section>'
            '<section><h2>مصادر الوحدة الحالية</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        for name in ("sitemap.xml", "sitemap-special-needs.xml"):
            (self.site / name).write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
                encoding="utf-8",
            )

    def run_pipeline(self) -> dict:
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(
            (self.site / "api" / "special-needs-guides-v221.json").read_text(encoding="utf-8")
        )

    def test_full_pipeline_publishes_v324_and_is_stable(self) -> None:
        first = self.run_pipeline()
        self.assertEqual(first["autism_clinical_pathways_contract"], 324)
        clinical = first["condition_hubs"]["autism_clinical_pathways"]
        self.assertEqual(clinical["version"], 324)
        self.assertEqual(clinical["status"], "passed")
        self.assertEqual(clinical["guide_count"], 4)
        self.assertEqual(tuple(clinical["guide_slugs"]), SLUGS)
        self.assertEqual(clinical["section_count"], 28)
        self.assertEqual(clinical["source_count"], 26)
        self.assertEqual(clinical["action_step_count"], 24)
        self.assertEqual(clinical["urgent_item_count"], 12)
        self.assertEqual(clinical["parent_links_added"], 4)
        self.assertGreaterEqual(clinical["minimum_guide_words"], 1250)
        self.assertTrue(clinical["sitemap_registered"])
        self.assertFalse(clinical["external_clinical_review_completed"])

        parent = self.site / "special-needs" / "autism" / "index.html"
        parent_text = parent.read_text(encoding="utf-8")
        self.assertEqual(parent_text.count("data-autism-clinical-pathways-v324"), 1)
        tracked = [
            parent,
            self.site / "sitemap-special-needs.xml",
            self.site / "api" / "special-needs-guides-v217.json",
            self.site / "api" / "special-needs-guides-v221.json",
            self.site / "api" / "autism-clinical-pathways-v324.json",
        ]
        for slug in SLUGS:
            page = self.site / "special-needs" / slug / "index.html"
            self.assertTrue(page.is_file(), slug)
            source = page.read_text(encoding="utf-8")
            self.assertEqual(source.lower().count("<h1"), 1)
            self.assertEqual(source.count('class="section-card"'), 7)
            self.assertIn("MedicalWebPage", source)
            self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", source)
            self.assertEqual(parent_text.count(f"/pterminology-site/special-needs/{slug}/"), 1)
            tracked.append(page)

        urls = [
            (node.text or "").strip()
            for node in ET.parse(self.site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        for slug in SLUGS:
            self.assertEqual(urls.count(f"{BASE}/special-needs/{slug}/"), 1)
        self.assertEqual(len(urls), len(set(urls)))

        before = [digest(path) for path in tracked]
        second = self.run_pipeline()
        after = [digest(path) for path in tracked]
        self.assertEqual(second["condition_hubs"]["autism_clinical_pathways"], clinical)
        self.assertEqual(before, after)

    def test_repository_audit_marks_v324_sources_and_publishers_reachable(self) -> None:
        result = subprocess.run(
            ["python3", str(AUDITOR), "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads((ROOT / "_audit" / "unpublished-content-v201.json").read_text(encoding="utf-8"))
        by_path = {item["path"]: item for item in report["items"]}
        required = (
            "content/v324/autism-clinical-pathways-ar.json.gz",
            "scripts/publish_autism_clinical_pathways_v324.py",
            "scripts/publish_special_needs_guides_v217_pipeline_core.py",
        )
        for path in required:
            self.assertIn(path, by_path)
            self.assertEqual(by_path[path]["category"], "production-reachable", path)


if __name__ == "__main__":
    unittest.main()
