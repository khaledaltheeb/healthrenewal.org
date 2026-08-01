from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_special_needs_guides_v217.py"
AUDITOR = ROOT / "scripts" / "audit_unpublished_content_v201.py"
BASE = "https://healthrenewal.org"


class SpecialNeedsRegressionIntegrationV320Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="special-needs-regression-v320-"))
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

    @classmethod
    def report_differences(cls, first: object, second: object, path: str = "report") -> list[str]:
        differences: list[str] = []
        if isinstance(first, dict) and isinstance(second, dict):
            for key in sorted(set(first) | set(second)):
                child = f"{path}.{key}"
                if key not in first:
                    differences.append(f"{child}: missing from first")
                elif key not in second:
                    differences.append(f"{child}: missing from second")
                else:
                    differences.extend(cls.report_differences(first[key], second[key], child))
            return differences
        if isinstance(first, list) and isinstance(second, list):
            if len(first) != len(second):
                differences.append(f"{path}.length: {len(first)!r} != {len(second)!r}")
            for index, (left, right) in enumerate(zip(first, second)):
                differences.extend(cls.report_differences(left, right, f"{path}[{index}]"))
            return differences
        if first != second:
            differences.append(f"{path}: {first!r} != {second!r}")
        return differences

    def run_publisher(self) -> dict:
        result = subprocess.run(
            ["python3", str(PUBLISHER), str(self.site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads((self.site / "api/special-needs-guides-v221.json").read_text(encoding="utf-8"))

    def test_regression_layer_is_integrated_with_all_prior_condition_layers(self) -> None:
        first = self.run_publisher()
        self.assertEqual(first["status"], "passed")
        self.assertEqual(first["condition_age_guides_contract"], 314)
        self.assertEqual(first["diagnostic_decision_guides_contract"], 316)
        self.assertEqual(first["support_intervention_guides_contract"], 318)
        self.assertEqual(first["regression_coexisting_guides_contract"], 320)

        regression = first["condition_hubs"]["regression_coexisting"]
        self.assertEqual(regression["version"], 320)
        self.assertEqual(regression["status"], "passed")
        self.assertEqual(regression["guide_count"], 2)
        self.assertEqual(regression["section_count"], 10)
        self.assertEqual(regression["source_count"], 11)
        self.assertEqual(regression["action_step_count"], 10)
        self.assertEqual(regression["urgent_item_count"], 6)
        self.assertEqual(regression["parent_links_added"], 2)
        self.assertTrue(regression["sitemap_registered"])
        self.assertTrue(regression["dsrd_consensus_limit_visible"])
        self.assertTrue(regression["dementia_baseline_limit_visible"])
        self.assertTrue(regression["diagnostic_overshadowing_guard"])
        self.assertFalse(regression["external_clinical_review_completed"])
        self.assertEqual(regression["next_review_due"], "2027-01-27")
        self.assertEqual(
            regression["guide_slugs"],
            ["autism-coexisting-conditions-sudden-change", "down-syndrome-regression-dementia-urgent-changes"],
        )

        parent_children = {
            "autism": (
                "autism-signs-by-age",
                "autism-screening-vs-diagnosis",
                "autism-evidence-based-support-plan",
                "autism-coexisting-conditions-sudden-change",
            ),
            "down-syndrome": (
                "down-syndrome-health-by-age",
                "down-syndrome-prenatal-screening-vs-diagnosis",
                "down-syndrome-development-communication-independence",
                "down-syndrome-regression-dementia-urgent-changes",
            ),
        }
        for parent, children in parent_children.items():
            page = (self.site / "special-needs" / parent / "index.html").read_text(encoding="utf-8")
            self.assertEqual(page.count('data-age-guide="'), 1)
            self.assertEqual(page.count('data-diagnostic-guide="'), 1)
            self.assertEqual(page.count('data-support-guide="'), 1)
            self.assertEqual(page.count('data-regression-guide="'), 1)
            for slug in children:
                self.assertEqual(page.count(f'/special-needs/{slug}/'), 1)
                self.assertTrue((self.site / "special-needs" / slug / "index.html").is_file())

        autism = (
            self.site / "special-needs" / "autism-coexisting-conditions-sudden-change" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("التغير الجديد ليس سمة ثابتة من سمات التوحد", autism)
        self.assertIn("لا يجوز تفسير الألم أو الاكتئاب أو الصرع أو الإساءة", autism)
        self.assertIn("منع حجب التشخيص", autism)

        down = (
            self.site / "special-needs" / "down-syndrome-regression-dementia-urgent-changes" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("DSRD إطار سريري ناشئ مبني جزئيًا على إجماع خبراء", down)
        self.assertIn("لا يملك اختبارًا حاسمًا واحدًا", down)
        self.assertIn("لا يساوي تلقائيًا تشخيص الخرف السريري", down)
        self.assertIn("بدء تحرٍ سنوي منظم عن ألزهايمر من عمر 40 عامًا", down)
        self.assertIn("لا تطلب قائمة ثابتة من الفحوص للجميع", down)

        locations = [
            (node.text or "").strip()
            for node in ET.parse(self.site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        for slug in regression["guide_slugs"]:
            self.assertEqual(locations.count(f"{BASE}/special-needs/{slug}/"), 1)
        self.assertEqual(len(locations), len(set(locations)))

        tracked = [
            self.site / "special-needs/autism/index.html",
            self.site / "special-needs/down-syndrome/index.html",
            self.site / "special-needs/autism-coexisting-conditions-sudden-change/index.html",
            self.site / "special-needs/down-syndrome-regression-dementia-urgent-changes/index.html",
            self.site / "api/special-needs-regression-coexisting-v320.json",
            self.site / "api/special-needs-guides-v221.json",
            self.site / "sitemap-special-needs.xml",
        ]
        before = [self.digest(path) for path in tracked]
        second = self.run_publisher()
        after = [self.digest(path) for path in tracked]
        self.assertEqual(second["condition_hubs"]["regression_coexisting"]["guide_count"], 2)
        differences = self.report_differences(first, second)
        if differences:
            print("\n".join(f"REPORT_DIFF {item}" for item in differences), file=sys.stderr)
        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_repository_audit_classifies_v320_as_production_reachable(self) -> None:
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
            "content/v320/special-needs-regression-coexisting-ar.json",
            "scripts/publish_special_needs_regression_coexisting_v320.py",
        )
        for path in required:
            self.assertIn(path, by_path)
            self.assertEqual(by_path[path]["category"], "production-reachable", path)


if __name__ == "__main__":
    unittest.main()
