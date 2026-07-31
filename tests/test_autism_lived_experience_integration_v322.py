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
BASE = "https://healthrenewal.org"
SLUGS = (
    "autism-sensory-profile-overload",
    "autism-communication-stimming-neurodiversity",
)
SOURCE = "content/v322/autism-lived-experience-guides-ar.json"
MODULE = "scripts/publish_autism_lived_experience_guides_v322.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AutismLivedExperienceIntegrationV322Test(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="autism-v322-integration-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "special-needs/index.html").write_text(
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

    def run_publisher(self) -> dict:
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads((self.site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8"))

    def test_v322_is_reachable_discoverable_and_byte_stable(self) -> None:
        first = self.run_publisher()
        self.assertEqual(first["autism_lived_experience_guides_contract"], 322)
        layer = first["condition_hubs"]["autism_lived_experience"]
        self.assertEqual(layer["version"], 322)
        self.assertEqual(layer["status"], "passed")
        self.assertEqual(layer["guide_count"], 2)
        self.assertEqual(layer["guide_slugs"], list(SLUGS))
        self.assertEqual(layer["section_count"], 10)
        self.assertEqual(layer["source_count"], 11)
        self.assertEqual(layer["practical_resource_count"], 4)
        self.assertEqual(layer["parent_links_added"], 2)
        self.assertTrue(layer["sitemap_registered"])
        self.assertTrue(layer["national_autistic_society_resource_used"])
        self.assertTrue(layer["content_rewritten_not_copied"])
        self.assertFalse(layer["external_clinical_review_completed"])

        parent = self.site / "special-needs/autism/index.html"
        parent_html = parent.read_text(encoding="utf-8")
        tracked = [
            parent,
            self.site / "sitemap-special-needs.xml",
            self.site / "api/autism-lived-experience-guides-v322.json",
            self.site / "api/special-needs-guides-v221.json",
        ]
        for slug in SLUGS:
            page = self.site / "special-needs" / slug / "index.html"
            tracked.append(page)
            self.assertTrue(page.is_file())
            html = page.read_text(encoding="utf-8")
            self.assertEqual(html.count("<h1"), 1)
            self.assertEqual(html.count('class="section-card"'), 5)
            self.assertGreaterEqual(html.count('class="resource-card"'), 2)
            self.assertIn("MedicalWebPage", html)
            self.assertIn("National Autistic Society", html)
            self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", html)
            self.assertEqual(parent_html.count(f'data-autism-guide="{slug}"'), 1)
            self.assertEqual(parent_html.count(f"/special-needs/{slug}/"), 1)

        sensory = (self.site / "special-needs/autism-sensory-profile-overload/index.html").read_text(encoding="utf-8")
        self.assertIn("الحواس الثماني", sensory)
        self.assertIn("الحمل الحسي", sensory)
        self.assertIn("My sensory experience", sensory)
        communication = (self.site / "special-needs/autism-communication-stimming-neurodiversity/index.html").read_text(encoding="utf-8")
        self.assertIn("مشكلة التعاطف المتبادل", communication)
        self.assertIn("التحفيز الذاتي", communication)
        self.assertIn("How to talk and write about autism", communication)

        locations = [
            node.text
            for node in ET.parse(self.site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        for slug in SLUGS:
            self.assertEqual(locations.count(f"{BASE}/special-needs/{slug}/"), 1)
        self.assertEqual(len(locations), len(set(locations)))

        before = [digest(path) for path in tracked]
        second = self.run_publisher()
        after = [digest(path) for path in tracked]
        self.assertEqual(second["condition_hubs"]["autism_lived_experience"]["guide_count"], 2)
        self.assertEqual(before, after)

    def test_repository_audit_marks_v322_source_and_publisher_reachable(self) -> None:
        result = subprocess.run(
            ["python3", str(AUDITOR), "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads((ROOT / "_audit/unpublished-content-v201.json").read_text(encoding="utf-8"))
        by_path = {item["path"]: item for item in report["items"]}
        for path in (SOURCE, MODULE):
            self.assertIn(path, by_path)
            self.assertEqual(by_path[path]["category"], "production-reachable", path)


if __name__ == "__main__":
    unittest.main()
