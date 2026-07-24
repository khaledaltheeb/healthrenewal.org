from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


IMPORTER = load_module("course_importer_v215", ROOT / "scripts" / "import_authorized_courses_v215.py")
PUBLISHER = load_module("public_api_v215", ROOT / "scripts" / "publish_public_api_v215.py")
SEO_AUDIT = load_module("seo_audit_v215", ROOT / "scripts" / "audit_seo_semantics_v215.py")


class PublicApiV215Tests(unittest.TestCase):
    def approved_source(self) -> dict:
        return {"id":"example-provider","provider":"Example Provider","enabled":True,"permission_status":"approved","permission_reference":"written-permission-2026-07-20","permission_granted_at":"2026-07-20","license_url":"https://courses.example.org/license","allowed_actions":["import_catalog"],"format":"json","feed_url":"https://courses.example.org/feed.json","allowed_hosts":["courses.example.org"],"course_hosts":["courses.example.org"]}

    def test_homepage_keeps_controlled_keywords_and_hides_internal_copy(self) -> None:
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        taxonomy = json.loads((ROOT / "content" / "seo" / "keyword-taxonomy-v215.json").read_text(encoding="utf-8"))
        match = re.search(r'<meta name="keywords" content="([^"]+)">', text)
        self.assertIsNotNone(match)
        self.assertLessEqual(len([item for item in match.group(1).split(",") if item.strip()]), taxonomy["policy"]["maximum_meta_keywords"])
        for phrase in taxonomy["forbidden_public_phrases"]:
            self.assertNotIn(phrase, text)

    def test_importer_rejects_enabled_source_without_permission(self) -> None:
        source = self.approved_source(); source["permission_status"] = "requested"
        with self.assertRaises(IMPORTER.CourseImportError): IMPORTER.validate_source(source)

    def test_course_normalization_strips_html_and_enforces_hosts(self) -> None:
        source = IMPORTER.validate_source(self.approved_source())
        course = IMPORTER.normalize_course({"id":"course-1","title_ar":"<b>دورة دعم الأسرة</b>","description_ar":"<p>محتوى تعليمي منظم.</p>","url":"https://courses.example.org/course-1","language":"ar"}, source)
        self.assertEqual(course["title_ar"], "دورة دعم الأسرة")
        self.assertEqual(course["permission_status"], "approved")
        self.assertNotIn("<", course["description_ar"])

    def test_publisher_preserves_existing_api_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); site = root / "site"; site.mkdir()
            manifest = root / "manifest.json"; imported = root / "imported.json"
            api = site / "api" / "v1"; api.mkdir(parents=True)
            (api / "openapi.json").write_text(json.dumps({"openapi":"3.1.0","info":{"title":"Original API","version":"0.9.0"},"paths":{"/api/v1/platform.json":{"get":{"summary":"Existing platform endpoint"}}},"components":{"schemas":{"Platform":{"type":"object"}}}}), encoding="utf-8")
            manifest.write_text(json.dumps({"schema_version":215,"policy":"deny-by-default","sources":[self.approved_source()]}), encoding="utf-8")
            imported.write_text(json.dumps({"schema_version":215,"status":"ready","sources_processed":1,"courses":[{"id":"example-provider:course-1","source_id":"example-provider","provider":"Example Provider","title_ar":"دورة دعم الأسرة","title":"Family Support","description_ar":"وصف عربي.","description":"English description.","url":"https://courses.example.org/course-1","language":"ar","format":"online","duration":"4 hours","price_text":"","updated_at":None,"license_url":"https://courses.example.org/license","permission_status":"approved"}]}), encoding="utf-8")
            report = PUBLISHER.publish(site=site, manifest_path=manifest, import_path=imported)
            openapi = json.loads((api / "openapi.json").read_text(encoding="utf-8"))
            self.assertIn("/api/v1/platform.json", openapi["paths"])
            self.assertIn("/api/v1/health.json", openapi["paths"])
            self.assertIn("Platform", openapi["components"]["schemas"])
            self.assertIn("Course", openapi["components"]["schemas"])
            self.assertTrue(report["preserved_existing_paths"])
            self.assertTrue((site / "developers" / "index.html").is_file())
            self.assertTrue((site / "sitemap-developers.xml").is_file())

    def test_seo_audit_blocks_public_execution_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp) / "site"; site.mkdir()
            (site / "index.html").write_text('<!doctype html><html lang="ar" dir="rtl"><head><title>عنوان عربي تجريبي واضح للصحة النفسية</title><meta name="keywords" content="الصحة النفسية,علم النفس"><meta name="description" content="وصف عربي موسع وواضح يشرح محتوى الصفحة والغرض منها ويقدم قيمة للقارئ ضمن حدود مهنية دقيقة ومفهومة."><link rel="canonical" href="https://example.org/"><meta property="og:title" content="عنوان"><meta property="og:description" content="وصف"><meta name="twitter:card" content="summary"><script type="application/ld+json">{}</script></head><body><h1>عنوان</h1><p>خطة نمو قابلة للقياس</p></body></html>', encoding="utf-8")
            report = SEO_AUDIT.audit_site(site=site, report_path=Path(temp) / "report.json", taxonomy_path=ROOT / "content" / "seo" / "keyword-taxonomy-v215.json")
            self.assertGreater(report["critical_error_count"], 0)


if __name__ == "__main__":
    unittest.main()
