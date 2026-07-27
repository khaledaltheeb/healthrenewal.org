from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_v254.py"
TEN_PLAN_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_ten_plans_v302.py"
REVIEW_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_review_governance_v305.py"
GOVERNANCE = ROOT / "content" / "v305" / "outside-the-box-review-governance-ar.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReviewGovernanceSourceV305(unittest.TestCase):
    def test_contract_is_explicit_and_non_accrediting(self) -> None:
        contract = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
        self.assertEqual(contract["version"], 305)
        self.assertEqual(contract["scope"]["condition_count"], 100)
        self.assertEqual(contract["scope"]["total_plan_instances"], 1000)
        self.assertFalse(contract["scope"]["external_review_completed"])
        self.assertFalse(contract["scope"]["global_accreditation_claim"])
        self.assertEqual(len(contract["claim_domains"]), 6)
        self.assertGreaterEqual(len(contract["reviewer_roles"]), 9)
        self.assertGreaterEqual(len(contract["required_review_record_fields"]), 17)
        self.assertGreaterEqual(len(contract["acceptance_gates"]), 10)
        self.assertFalse(contract["publication_policy"]["allow_silent_corrections"])
        self.assertFalse(contract["publication_policy"]["allow_self_review_as_independent_review"])
        self.assertFalse(contract["publication_policy"]["allow_proprietary_test_content"])

    def test_register_generation_covers_every_claim_and_plan(self) -> None:
        module = load_module(REVIEW_PUBLISHER, "outside_review_source_v305")
        data, framework, governance = module.load_sources()
        report = module.build_register(data, framework, governance)
        self.assertEqual(report["condition_count"], 100)
        self.assertEqual(report["claim_review_count"], 600)
        self.assertEqual(report["plan_review_count"], 1000)
        self.assertEqual(report["independent_reviews_recorded"], 0)
        self.assertFalse(report["external_review_completed"])
        self.assertEqual(len(report["conditions"]), 100)
        self.assertEqual([item["rank"] for item in report["conditions"]], list(range(1, 101)))
        self.assertEqual(len({item["slug"] for item in report["conditions"]}), 100)
        for condition in report["conditions"]:
            self.assertEqual(condition["status"], "awaiting-independent-review")
            self.assertEqual(len(condition["claim_reviews"]), 6)
            self.assertEqual(len(condition["plan_reviews"]), 10)
            self.assertEqual([item["order"] for item in condition["plan_reviews"]], list(range(1, 11)))
            self.assertTrue(all(len(item["source_keys"]) >= 2 for item in condition["claim_reviews"]))
            self.assertTrue(all(len(item["source_keys"]) >= 2 for item in condition["plan_reviews"]))
            self.assertTrue(all(item["reviews"] == [] for item in condition["claim_reviews"]))
            self.assertTrue(all(item["reviews"] == [] for item in condition["plan_reviews"]))


class ReviewGovernancePublisherV305(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="outside-review-v305-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "provider-assessment-demo").mkdir(parents=True)
        (self.site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<header><nav class="nav"><a href="special-needs/">المركز</a></nav></header>'
            '<main><h1>الرئيسية</h1></main></body></html>', encoding="utf-8"
        )
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body><main><h1>المركز</h1></main></body></html>', encoding="utf-8"
        )
        (self.site / "provider-assessment-demo/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body><main><h1>مقدم الخدمة</h1></main></body></html>', encoding="utf-8"
        )
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://example.test/sitemap-core.xml</loc></sitemap></sitemapindex>', encoding="utf-8"
        )
        (self.site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        self.base = load_module(BASE_PUBLISHER, "outside_base_for_review_v305")
        self.ten = load_module(TEN_PLAN_PUBLISHER, "outside_ten_for_review_v305")
        self.review = load_module(REVIEW_PUBLISHER, "outside_review_v305")

    def publish(self) -> dict:
        self.base.publish(self.site)
        self.ten.publish(self.site)
        return self.review.publish(self.site)

    def test_publishes_dashboard_register_api_and_condition_links(self) -> None:
        report = self.publish()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["condition_count"], 100)
        self.assertEqual(report["claim_review_count"], 600)
        self.assertEqual(report["plan_review_count"], 1000)
        dashboard = (self.site / "outside-the-box/review-governance/index.html").read_text(encoding="utf-8")
        self.assertEqual(dashboard.count("data-review-condition="), 100)
        self.assertIn("صفر موافقات تخصصية مستقلة", dashboard)
        self.assertIn("مسار الملاحظة والتدقيق والتصحيح", dashboard)
        for item in report["conditions"]:
            text = (self.site / "outside-the-box" / item["slug"] / "index.html").read_text(encoding="utf-8")
            self.assertEqual(text.count("outside-the-box-review-governance-v305-condition:start"), 1)
            self.assertIn(f'../review-governance/#condition-{item["slug"]}', text)
            self.assertIn("0</dd>", text)
        api = json.loads((self.site / "api/outside-the-box-review-governance-v305.json").read_text(encoding="utf-8"))
        self.assertEqual(len(api["conditions"]), 100)
        self.assertEqual(sum(len(item["plan_reviews"]) for item in api["conditions"]), 1000)
        template = json.loads((self.site / "api/outside-the-box-review-submission-template-v305.json").read_text(encoding="utf-8"))
        self.assertEqual(template["version"], 305)
        self.assertIn("reviewer_attestation", template)

    def test_integrates_sitemap_and_existing_apis(self) -> None:
        self.publish()
        sitemap = (self.site / "sitemap-outside-the-box.xml").read_text(encoding="utf-8")
        self.assertIn("outside-the-box/review-governance/", sitemap)
        base = json.loads((self.site / "api/outside-the-box-v254.json").read_text(encoding="utf-8"))
        plans = json.loads((self.site / "api/outside-the-box-ten-plans-v302.json").read_text(encoding="utf-8"))
        for api in (base, plans):
            summary = api["scientific_review_governance"]
            self.assertEqual(summary["version"], 305)
            self.assertEqual(summary["condition_count"], 100)
            self.assertEqual(summary["claim_review_count"], 600)
            self.assertEqual(summary["plan_review_count"], 1000)
            self.assertEqual(summary["independent_reviews_recorded"], 0)
            self.assertFalse(summary["external_review_completed"])

    def test_publication_is_idempotent(self) -> None:
        self.publish()
        tracked = [
            self.site / "outside-the-box/index.html",
            self.site / "outside-the-box/autism/index.html",
            self.site / "outside-the-box/review-governance/index.html",
            self.site / "api/outside-the-box-review-governance-v305.json",
            self.site / "api/outside-the-box-v254.json",
            self.site / "api/outside-the-box-ten-plans-v302.json",
            self.site / "sitemap-outside-the-box.xml",
        ]
        before = [digest(path) for path in tracked]
        self.review.publish(self.site)
        after = [digest(path) for path in tracked]
        self.assertEqual(before, after)

    def test_language_and_claims_remain_responsible(self) -> None:
        self.publish()
        text = "\n".join(path.read_text(encoding="utf-8") for path in (self.site / "outside-the-box").rglob("index.html"))
        for banned in ("معاقين", "اعتماد عالمي مكتمل", "مراجعة خارجية مكتملة", "الخطة تصلح للجميع", "كل المصابين متفوقون"):
            self.assertNotIn(banned, text)
        self.assertIn("لم تُسجل له بعد موافقة تخصصية مستقلة", text)
        self.assertIn("لا يوصف بأنه معتمد سريريًا", text)


if __name__ == "__main__":
    unittest.main()
