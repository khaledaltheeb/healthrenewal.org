from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_v254.py"
TEN_PLAN_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_ten_plans_v302.py"
REFERENCE_PUBLISHER = ROOT / "scripts" / "publish_outside_the_box_reference_assets_v303.py"
INSTRUMENTS = ROOT / "content" / "v254" / "outside-the-box-instruments-ar.json"
BASE = "https://healthrenewal.org/"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class OutsideTheBoxReferenceAssetsV303(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="outside-reference-v303-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "provider-assessment-demo").mkdir(parents=True)
        (self.site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<header><nav class="nav"><a href="special-needs/">المركز</a></nav></header>'
            '<main><h1>الرئيسية</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<main><h1>مركز ذوي الاحتياجات الخاصة</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "provider-assessment-demo/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head></head><body>'
            '<main><h1>منصة مقدم الخدمة</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://example.test/sitemap-core.xml</loc></sitemap>'
            "</sitemapindex>",
            encoding="utf-8",
        )
        (self.site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        self.base = load(BASE_PUBLISHER, "outside_reference_base_v254")
        self.ten = load(TEN_PLAN_PUBLISHER, "outside_reference_ten_v302")
        self.reference = load(REFERENCE_PUBLISHER, "outside_reference_v303")

    def publish(self) -> dict:
        self.base.publish(self.site)
        self.ten.publish(self.site)
        return self.reference.publish(self.site)

    def test_publishes_complete_reference_assets_without_protected_content(self) -> None:
        report = self.publish()
        self.assertEqual(report["version"], 303)
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["protected_test_items_published"])
        self.assertFalse(report["scoring_keys_published"])
        self.assertFalse(report["normative_tables_published"])
        self.assertFalse(report["external_clinical_review_completed"])

        evidence = self.site / "outside-the-box/evidence-standard/index.html"
        registry = self.site / "outside-the-box/instruments/index.html"
        evidence_api = self.site / "api/outside-the-box-evidence-standard-v301.json"
        report_api = self.site / "api/outside-the-box-reference-assets-v303.json"
        for path in (evidence, registry, evidence_api, report_api):
            self.assertTrue(path.is_file(), path)

        instruments = json.loads(INSTRUMENTS.read_text(encoding="utf-8"))
        page = registry.read_text(encoding="utf-8")
        expected_count = len(instruments["universal"]) + sum(
            len(tools) for tools in instruments["clusters"].values()
        )
        self.assertEqual(report["instrument_count"], expected_count)
        self.assertIn(instruments["rights_notice"], page)
        self.assertIn(instruments["review_status"], page)
        for tools in [instruments["universal"], *instruments["clusters"].values()]:
            for tool in tools:
                self.assertIn(tool["name"], page)
                self.assertIn(tool["owner"], page)
                self.assertIn(tool["use"], page)
                self.assertIn(tool["access"], page)
                self.assertIn(tool["caution"], page)

    def test_registers_reference_urls_and_resolves_cross_links(self) -> None:
        self.publish()
        urls = {
            (node.text or "").strip()
            for node in ET.parse(self.site / "sitemap-outside-the-box.xml")
            .getroot()
            .findall("{*}url/{*}loc")
            if node.text
        }
        self.assertIn(BASE + "outside-the-box/evidence-standard/", urls)
        self.assertIn(BASE + "outside-the-box/instruments/", urls)
        self.assertEqual(len(urls), len(set(urls)))

        evidence = (
            self.site / "outside-the-box/evidence-standard/index.html"
        ).read_text(encoding="utf-8")
        registry = (
            self.site / "outside-the-box/instruments/index.html"
        ).read_text(encoding="utf-8")
        self.assertIn('/outside-the-box/instruments/', evidence)
        self.assertIn('/api/outside-the-box-evidence-standard-v301.json', evidence)
        self.assertIn('../evidence-standard/', registry)
        self.assertIn('../ten-plan-methodology/', registry)

    def test_reference_publication_is_idempotent(self) -> None:
        first = self.publish()
        snapshots = {
            path: path.read_bytes()
            for path in (
                self.site / "outside-the-box/evidence-standard/index.html",
                self.site / "outside-the-box/instruments/index.html",
                self.site / "api/outside-the-box-evidence-standard-v301.json",
                self.site / "api/outside-the-box-reference-assets-v303.json",
                self.site / "sitemap-outside-the-box.xml",
            )
        }
        second = self.reference.publish(self.site)
        self.assertEqual(first, second)
        for path, before in snapshots.items():
            self.assertEqual(before, path.read_bytes(), path)


if __name__ == "__main__":
    unittest.main()
