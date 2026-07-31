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


class SpecialNeedsSupportIntegrationV318Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="special-needs-support-v318-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main>'
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

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run_publisher(self) -> dict:
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads((self.site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8"))

    def test_support_layer_is_integrated_with_all_condition_layers(self) -> None:
        first = self.run_publisher()
        self.assertEqual(first["status"], "passed")
        self.assertEqual(first["condition_age_guides_contract"], 314)
        self.assertEqual(first["diagnostic_decision_guides_contract"], 316)
        self.assertEqual(first["support_intervention_guides_contract"], 318)

        support = first["condition_hubs"]["support_interventions"]
        self.assertEqual(support["version"], 318)
        self.assertEqual(support["status"], "passed")
        self.assertEqual(support["guide_count"], 2)
        self.assertEqual(support["section_count"], 10)
        self.assertEqual(support["source_count"], 9)
        self.assertEqual(support["plan_step_count"], 10)
        self.assertEqual(support["urgent_item_count"], 6)
        self.assertEqual(support["parent_links_added"], 2)
        self.assertTrue(support["sitemap_registered"])
        self.assertFalse(support["external_clinical_review_completed"])
        self.assertEqual(support["next_review_due"], "2027-01-27")
        self.assertEqual(
            support["guide_slugs"],
            ["autism-evidence-based-support-plan", "down-syndrome-development-communication-independence"],
        )

        parent_children = {
            "autism": (
                "autism-signs-by-age",
                "autism-screening-vs-diagnosis",
                "autism-evidence-based-support-plan",
            ),
            "down-syndrome": (
                "down-syndrome-health-by-age",
                "down-syndrome-prenatal-screening-vs-diagnosis",
                "down-syndrome-development-communication-independence",
            ),
        }
        for parent, children in parent_children.items():
            page = (self.site / "special-needs" / parent / "index.html").read_text(encoding="utf-8")
            self.assertEqual(page.count('data-age-guide="'), 1)
            self.assertEqual(page.count('data-diagnostic-guide="'), 1)
            self.assertEqual(page.count('data-support-guide="'), 1)
            for slug in children:
                self.assertEqual(page.count(f'/special-needs/{slug}/'), 1)
                self.assertTrue((self.site / "special-needs" / slug / "index.html").is_file())

        autism = (
            self.site / "special-needs" / "autism-evidence-based-support-plan" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("لا توجد متطلبات مسبقة لاستخدام AAC", autism)
        self.assertIn("لا تستخدم الخلب أو الأكسجين عالي الضغط أو السيكريتين", autism)
        self.assertIn("لا تنطبق مخاوف وقت الشاشة المعتادة", autism)
        down = (
            self.site / "special-needs" / "down-syndrome-development-communication-independence" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("لا يوجد علاج موحد لمتلازمة داون", down)
        self.assertIn("الاستقلال ليس غياب الدعم", down)
        self.assertIn("لا تفترض أنه جزء طبيعي من متلازمة داون", down)

        locations = [
            (node.text or "").strip()
            for node in ET.parse(self.site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        for slug in support["guide_slugs"]:
            self.assertEqual(locations.count(f"{BASE}/special-needs/{slug}/"), 1)
        self.assertEqual(len(locations), len(set(locations)))

        tracked = [
            self.site / "special-needs/autism/index.html",
            self.site / "special-needs/down-syndrome/index.html",
            self.site / "special-needs/autism-evidence-based-support-plan/index.html",
            self.site / "special-needs/down-syndrome-development-communication-independence/index.html",
            self.site / "api/special-needs-support-interventions-v318.json",
            self.site / "api/special-needs-guides-v221.json",
            self.site / "sitemap-special-needs.xml",
        ]
        before = [self.digest(path) for path in tracked]
        second = self.run_publisher()
        after = [self.digest(path) for path in tracked]
        self.assertEqual(second["condition_hubs"]["support_interventions"]["guide_count"], 2)
        self.assertEqual(before, after)

    def test_repository_audit_classifies_v318_as_production_reachable(self) -> None:
        result = subprocess.run(
            ["python3", str(AUDITOR), "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads((ROOT / "_audit/unpublished-content-v201.json").read_text(encoding="utf-8"))
        by_path = {item["path"]: item for item in report["items"]}
        required = (
            "content/v318/special-needs-support-interventions-ar.json",
            "scripts/publish_special_needs_support_interventions_v318.py",
        )
        for path in required:
            self.assertIn(path, by_path)
            self.assertEqual(by_path[path]["category"], "production-reachable", path)


if __name__ == "__main__":
    unittest.main()
