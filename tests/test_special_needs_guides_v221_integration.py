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
PRODUCTION_MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"
BASE = "https://healthrenewal.org"
VERSIONS = (209, 210, 211, 212, 214)
CONDITION_SOURCE_FILES = {
    "content/v302/special-needs-condition-hubs-ar.json",
    "content/v302/special-needs-providers-ar.json",
    "content/v302/autism-ar.json",
    "content/v302/down-syndrome-ar.json",
    "content/v305/special-needs-condition-postlaunch-ar.json",
    "content/v307/special-needs-condition-trust-ar.json",
    "content/v310/special-needs-condition-source-maintenance-ar.json",
    "content/v312/special-needs-condition-source-url-overrides.json",
    "content/v314/special-needs-condition-age-guides-ar.json",
    "content/v316/special-needs-diagnostic-decision-guides-ar.json",
}
SPECIAL_NEEDS_CONTENT_PREFIXES = (
    "content/v209/special-needs-guides/",
    "content/v210/special-needs-guides/",
    "content/v211/special-needs-guides/",
    "content/v212/special-needs-guides/",
    "content/v214/special-needs-guides/",
    "content/v221/special-needs",
)
SPECIAL_NEEDS_PUBLISHERS = {
    "scripts/publish_special_needs_hub_v235.py",
    "scripts/publish_special_needs_hub_v235_compat.py",
    "scripts/publish_special_needs_condition_hubs_v302.py",
    "scripts/publish_special_needs_condition_postlaunch_v305.py",
    "scripts/publish_special_needs_condition_trust_v307.py",
    "scripts/validate_special_needs_provider_directory_v308.py",
    "scripts/audit_special_needs_condition_sources_v310.py",
    "scripts/publish_special_needs_condition_age_guides_v314.py",
    "scripts/publish_special_needs_diagnostic_decision_guides_v316.py",
    "scripts/publish_special_needs_guides_v214.py",
    "scripts/publish_special_needs_guides_v217.py",
    "scripts/publish_special_needs_guides_v217_core.py",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpecialNeedsGuidesV221Integration(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="special-needs-v221-"))
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

    def test_manifest_lists_25_existing_sources(self) -> None:
        manifest = json.loads(PRODUCTION_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 221)
        self.assertEqual(manifest["status"], "production-integrated")
        self.assertEqual(manifest["review_status"], "internally-reviewed")
        self.assertEqual(manifest["external_review"], "recommended-not-completed")
        self.assertEqual(manifest["batches"], list(VERSIONS))
        self.assertEqual(len(manifest["source_files"]), 25)
        self.assertEqual(len(set(manifest["source_files"])), 25)
        self.assertTrue(all((ROOT / path).is_file() for path in manifest["source_files"]))
        self.assertEqual(manifest["blocked_review_files_excluded"], 3)

    def test_all_guides_condition_layers_are_stable_and_discoverable(self) -> None:
        first = self.run_publisher()
        self.assertEqual(first["version"], 221)
        self.assertEqual(first["batches"], list(VERSIONS))
        self.assertEqual(first["batch_count"], 5)
        self.assertEqual(first["guide_count"], 25)
        self.assertEqual(first["production_source_file_count"], 25)
        self.assertEqual(first["review_status"], "internally-reviewed")
        self.assertFalse(first["external_review_completed"])
        self.assertEqual(first["condition_hubs_contract"], 302)
        self.assertEqual(first["condition_age_guides_contract"], 314)
        self.assertEqual(first["diagnostic_decision_guides_contract"], 316)
        self.assertEqual(first["condition_hubs"]["condition_slugs"], ["autism", "down-syndrome"])
        self.assertEqual(first["condition_hubs"]["source_count"], 17)

        age_guides = first["condition_hubs"]["age_guides"]
        self.assertEqual(age_guides["version"], 314)
        self.assertEqual(age_guides["guide_count"], 2)
        self.assertEqual(age_guides["guide_slugs"], ["autism-signs-by-age", "down-syndrome-health-by-age"])
        self.assertEqual(age_guides["stage_count"], 8)
        self.assertEqual(age_guides["source_count"], 7)
        self.assertEqual(age_guides["parent_links_added"], 2)
        self.assertTrue(age_guides["sitemap_registered"])
        self.assertFalse(age_guides["external_clinical_review_completed"])

        decision_guides = first["condition_hubs"]["diagnostic_decision_guides"]
        self.assertEqual(decision_guides["version"], 316)
        self.assertEqual(decision_guides["status"], "passed")
        self.assertEqual(decision_guides["guide_count"], 2)
        self.assertEqual(
            decision_guides["guide_slugs"],
            ["autism-screening-vs-diagnosis", "down-syndrome-prenatal-screening-vs-diagnosis"],
        )
        self.assertEqual(decision_guides["section_count"], 10)
        self.assertEqual(decision_guides["source_count"], 8)
        self.assertEqual(decision_guides["decision_step_count"], 10)
        self.assertEqual(decision_guides["parent_links_added"], 2)
        self.assertTrue(decision_guides["sitemap_registered"])
        self.assertFalse(decision_guides["external_clinical_review_completed"])
        self.assertEqual(decision_guides["next_review_due"], "2027-01-27")

        source_maintenance = first["condition_hubs"]["source_maintenance"]
        self.assertEqual(source_maintenance["version"], 310)
        self.assertEqual(source_maintenance["source_count"], 17)
        self.assertGreaterEqual(source_maintenance["distinct_host_count"], 3)
        self.assertEqual(source_maintenance["overdue_source_count"], 0)
        self.assertEqual(first["condition_hubs"]["postlaunch"]["related_link_count"], 16)
        self.assertEqual(first["condition_hubs"]["trust"]["faq_count"], 8)
        self.assertTrue(first["condition_hubs"]["trust"]["faq_schema_visible_match"])
        governance = first["condition_hubs"]["provider_governance"]
        self.assertEqual(governance["version"], 308)
        self.assertEqual(governance["record_count"], 0)
        self.assertEqual(governance["published_count"], 0)
        self.assertFalse(governance["sponsored_publication_enabled"])

        hub_path = self.site / "special-needs/index.html"
        hub = hub_path.read_text(encoding="utf-8")
        for version in VERSIONS:
            self.assertEqual(hub.count(f"special-needs-guides-v{version}:start"), 1)
            self.assertEqual(hub.count(f"special-needs-guides-v{version}:end"), 1)
        for slug in first["guide_slugs"]:
            self.assertTrue((self.site / "special-needs" / slug / "index.html").is_file())
            self.assertEqual(hub.count(f"/special-needs/{slug}/"), 1)

        parent_children = {
            "autism": ("autism-signs-by-age", "autism-screening-vs-diagnosis"),
            "down-syndrome": (
                "down-syndrome-health-by-age",
                "down-syndrome-prenatal-screening-vs-diagnosis",
            ),
        }
        for parent, children in parent_children.items():
            parent_path = self.site / "special-needs" / parent / "index.html"
            self.assertTrue(parent_path.is_file())
            self.assertEqual(hub.count(f"/special-needs/{parent}/"), 1)
            parent_page = parent_path.read_text(encoding="utf-8")
            self.assertIn('"@type": "FAQPage"', parent_page)
            self.assertIn('id="quality-and-faq"', parent_page)
            self.assertIn('id="provider-listing-policy"', parent_page)

            age_slug, decision_slug = children
            self.assertEqual(parent_page.count(f'data-age-guide="{age_slug}"'), 1)
            self.assertEqual(parent_page.count(f'/special-needs/{age_slug}/'), 1)
            self.assertEqual(parent_page.count(f'data-diagnostic-guide="{decision_slug}"'), 1)
            self.assertEqual(parent_page.count(f'/special-needs/{decision_slug}/'), 1)

            age_page = (self.site / "special-needs" / age_slug / "index.html").read_text(encoding="utf-8")
            self.assertEqual(age_page.count("<h1"), 1)
            self.assertEqual(age_page.count('class="stage"'), 4)
            self.assertIn("MedicalWebPage", age_page)

            decision_page = (self.site / "special-needs" / decision_slug / "index.html").read_text(encoding="utf-8")
            self.assertEqual(decision_page.count("<h1"), 1)
            self.assertEqual(decision_page.count('class="section-card"'), 5)
            self.assertIn("MedicalWebPage", decision_page)
            self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", decision_page)

        autism_decision = (
            self.site / "special-needs" / "autism-screening-vs-diagnosis" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("النتيجة الإيجابية تعني زيادة الحاجة إلى تقييم أعمق", autism_decision)
        self.assertIn("لا يعتمد على أداة تشخيصية واحدة وحدها", autism_decision)
        prenatal_decision = (
            self.site / "special-needs" / "down-syndrome-prenatal-screening-vs-diagnosis" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("للمريضة الحق في قبول التحري أو الاختبار التشخيصي أو رفضهما", prenatal_decision)
        self.assertIn("لا تفسر نتيجة تحرٍ إيجابية على أنها تشخيص مؤكد", prenatal_decision)

        locations = [
            node.text
            for node in ET.parse(self.site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
            if node.text
        ]
        expected = {f"{BASE}/special-needs/{slug}/" for slug in first["guide_slugs"]}
        expected.update(
            f"{BASE}/special-needs/{slug}/"
            for slug in (
                "autism",
                "down-syndrome",
                "autism-signs-by-age",
                "down-syndrome-health-by-age",
                "autism-screening-vs-diagnosis",
                "down-syndrome-prenatal-screening-vs-diagnosis",
            )
        )
        self.assertTrue(expected.issubset(set(locations)))
        self.assertEqual(len(locations), len(set(locations)))

        tracked = [
            hub_path,
            self.site / "sitemap.xml",
            self.site / "sitemap-special-needs.xml",
            self.site / "api/special-needs-guides-v214.json",
            self.site / "api/special-needs-guides-v217.json",
            self.site / "api/special-needs-guides-v221.json",
            self.site / "api/special-needs-condition-hubs-v302.json",
            self.site / "api/special-needs-condition-postlaunch-v305.json",
            self.site / "api/special-needs-condition-trust-v307.json",
            self.site / "api/special-needs-provider-governance-v308.json",
            self.site / "api/special-needs-condition-source-maintenance-v310.json",
            self.site / "api/special-needs-condition-age-guides-v314.json",
            self.site / "api/special-needs-diagnostic-decision-guides-v316.json",
            self.site / "special-needs/autism/index.html",
            self.site / "special-needs/down-syndrome/index.html",
            self.site / "special-needs/autism-signs-by-age/index.html",
            self.site / "special-needs/down-syndrome-health-by-age/index.html",
            self.site / "special-needs/autism-screening-vs-diagnosis/index.html",
            self.site / "special-needs/down-syndrome-prenatal-screening-vs-diagnosis/index.html",
        ]
        before = [digest(path) for path in tracked]
        second = self.run_publisher()
        after = [digest(path) for path in tracked]
        self.assertEqual(second["guide_count"], 25)
        self.assertEqual(second["condition_hubs"]["age_guides"]["guide_count"], 2)
        self.assertEqual(second["condition_hubs"]["diagnostic_decision_guides"]["guide_count"], 2)
        self.assertEqual(before, after)

    def test_repository_audit_sees_special_needs_sources_and_preserves_blocks(self) -> None:
        result = subprocess.run(
            ["python3", str(AUDITOR), "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads((ROOT / "_audit/unpublished-content-v201.json").read_text(encoding="utf-8"))
        by_path = {item["path"]: item for item in report["items"]}

        manifest = json.loads(PRODUCTION_MANIFEST.read_text(encoding="utf-8"))
        required_sources = set(manifest["source_files"]) | CONDITION_SOURCE_FILES
        for path in sorted(required_sources):
            self.assertIn(path, by_path)
            self.assertEqual(by_path[path]["category"], "production-reachable", path)

        scoped_failures = [
            item
            for item in report["items"]
            if item["category"] in {"unwired-content", "source-only", "unwired-publisher"}
            and (
                item["path"].startswith(SPECIAL_NEEDS_CONTENT_PREFIXES)
                or item["path"] in SPECIAL_NEEDS_PUBLISHERS
                or item["path"] in CONDITION_SOURCE_FILES
            )
        ]
        self.assertEqual(scoped_failures, [], "\n".join(item["path"] for item in scoped_failures))

        blocked = {
            "content/v73/special-needs-executable-instructions-ar.json",
            "data/disability-dignity-safety.json",
            "data/urgent-help-governance.json",
        }
        for path in blocked:
            self.assertEqual(by_path[path]["category"], "blocked-review")
            self.assertEqual(by_path[path]["recommended_action"], "do-not-publish")


if __name__ == "__main__":
    unittest.main()
