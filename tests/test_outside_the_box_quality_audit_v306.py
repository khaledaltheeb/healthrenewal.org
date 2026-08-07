from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PUBLISHER = ROOT / "scripts/publish_outside_the_box_v254.py"
TEN_PUBLISHER = ROOT / "scripts/publish_outside_the_box_ten_plans_v302.py"
REFERENCE_PUBLISHER = ROOT / "scripts/publish_outside_the_box_reference_assets_v303.py"
REVIEW_PUBLISHER = ROOT / "scripts/publish_outside_the_box_review_governance_v305.py"
AUDITOR = ROOT / "scripts/audit_outside_the_box_quality_v306.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OutsideBoxQualityAuditV306(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="outside-quality-v306-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        for route, title in (
            ("special-needs", "مركز ذوي الاحتياجات الخاصة"),
            ("provider-assessment-demo", "منصة مقدم الخدمة"),
            ("trust", "الثقة والمنهجية"),
        ):
            target = self.site / route
            target.mkdir(parents=True)
            (target / "index.html").write_text(
                f'<!doctype html><html lang="ar" dir="rtl"><head><title>{title}</title></head><body><main><h1>{title}</h1></main></body></html>',
                encoding="utf-8",
            )
        (self.site / "assets/brand").mkdir(parents=True)
        (self.site / "assets/brand/logo-mark.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>شعار</title></svg>',
            encoding="utf-8",
        )
        for relative_asset in (
            "favicon.ico",
            "favicon-32x32.png",
            "favicon-16x16.png",
            "apple-touch-icon.png",
        ):
            shutil.copy2(ROOT / relative_asset, self.site / relative_asset)
        (self.site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<header><nav class="nav"><a href="special-needs/">المركز</a></nav></header>'
            '<main><h1>الرئيسية</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://example.test/sitemap-core.xml</loc></sitemap></sitemapindex>',
            encoding="utf-8",
        )
        (self.site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        self.base = load_module(BASE_PUBLISHER, "outside_base_quality_v306")
        self.ten = load_module(TEN_PUBLISHER, "outside_ten_quality_v306")
        self.references = load_module(REFERENCE_PUBLISHER, "outside_refs_quality_v306")
        self.review = load_module(REVIEW_PUBLISHER, "outside_review_quality_v306")
        self.audit = load_module(AUDITOR, "outside_audit_v306")

    def publish_dependencies(self) -> None:
        self.base.publish(self.site)
        self.ten.publish(self.site)
        self.references.publish(self.site)
        self.review.publish(self.site)

    def test_audit_covers_pages_plans_links_seo_and_apis(self) -> None:
        self.publish_dependencies()
        report = self.audit.publish(self.site)
        self.assertEqual(report["status"], "passed-with-disclosed-warnings")
        self.assertEqual(report["critical_error_count"], 0)
        self.assertEqual(report["condition_pages_audited"], 100)
        self.assertEqual(report["plan_cards_audited"], 1000)
        self.assertEqual(report["review_markers_audited"], 100)
        self.assertEqual(report["broken_internal_link_count"], 0)
        self.assertEqual(report["unique_canonical_count"], 100)
        self.assertTrue(all(report["api_checks"].values()))
        warning_codes = {item["code"] for item in report["warnings"]}
        self.assertIn("source-contract-migration-incomplete", warning_codes)
        self.assertIn("independent-review-incomplete", warning_codes)

        page = (self.site / "outside-the-box/quality-audit/index.html").read_text(encoding="utf-8")
        self.assertIn("تدقيق الجودة والتنسيق والربط", page)
        self.assertIn("لا يعني اعتمادًا سريريًا", page)
        self.assertEqual(page.count("<h1"), 1)
        self.assertIn('rel="canonical"', page)
        self.assertIn('<html lang="ar" dir="rtl">', page)

        hub = (self.site / "outside-the-box/index.html").read_text(encoding="utf-8")
        review = (self.site / "outside-the-box/review-governance/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count("outside-the-box-quality-audit-v306-hub:start"), 1)
        self.assertEqual(review.count("outside-the-box-quality-audit-v306-review:start"), 1)
        self.assertIn("quality-audit/", hub)
        self.assertIn("../quality-audit/", review)

    def test_quality_report_is_integrated_into_apis_and_sitemap(self) -> None:
        self.publish_dependencies()
        self.audit.publish(self.site)
        for relative in (
            "api/outside-the-box-v254.json",
            "api/outside-the-box-ten-plans-v302.json",
            "api/outside-the-box-review-governance-v305.json",
        ):
            payload = json.loads((self.site / relative).read_text(encoding="utf-8"))
            summary = payload["quality_audit"]
            self.assertEqual(summary["version"], 306)
            self.assertEqual(summary["critical_error_count"], 0)
            self.assertEqual(summary["condition_pages_audited"], 100)
            self.assertEqual(summary["plan_cards_audited"], 1000)
            self.assertEqual(summary["broken_internal_link_count"], 0)
        sitemap = (self.site / "sitemap-outside-the-box.xml").read_text(encoding="utf-8")
        self.assertIn("outside-the-box/quality-audit/", sitemap)
        report = json.loads((self.site / "api/outside-the-box-quality-audit-v306.json").read_text(encoding="utf-8"))
        self.assertEqual(report["critical_error_count"], 0)
        self.assertEqual(report["condition_pages_audited"], 100)

    def test_audit_publication_is_idempotent(self) -> None:
        self.publish_dependencies()
        self.audit.publish(self.site)
        tracked = [
            self.site / "outside-the-box/index.html",
            self.site / "outside-the-box/review-governance/index.html",
            self.site / "outside-the-box/quality-audit/index.html",
            self.site / "api/outside-the-box-quality-audit-v306.json",
            self.site / "api/outside-the-box-v254.json",
            self.site / "api/outside-the-box-ten-plans-v302.json",
            self.site / "api/outside-the-box-review-governance-v305.json",
            self.site / "sitemap-outside-the-box.xml",
        ]
        before = [digest(path) for path in tracked]
        self.audit.publish(self.site)
        after = [digest(path) for path in tracked]
        self.assertEqual(before, after)

    def test_auditor_rejects_a_broken_internal_link(self) -> None:
        self.publish_dependencies()
        page = self.site / "outside-the-box/autism/index.html"
        text = page.read_text(encoding="utf-8")
        text = text.replace("</main>", '<a href="missing-internal-route/">رابط مكسور</a></main>', 1)
        page.write_text(text, encoding="utf-8")
        report = self.audit.audit(self.site)
        self.assertGreater(report["critical_error_count"], 0)
        self.assertGreater(report["broken_internal_link_count"], 0)
        with self.assertRaises(ValueError):
            self.audit.publish(self.site)


if __name__ == "__main__":
    unittest.main()
