from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_section_directory_v221.py"
spec = importlib.util.spec_from_file_location("section_directory_v221", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def page(title: str, route: str, *, robots: str = "index,follow") -> str:
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        f'<title>{title}</title>'
        f'<meta name="description" content="وصف مؤسسي موسع لقسم {title} داخل المنصة العربية.">'
        f'<meta name="robots" content="{robots}">'
        f'<link rel="canonical" href="{module.BASE}{route}">'
        '</head><body><main><h1>'
        + title
        + '</h1></main></body></html>'
    )


class SectionDirectoryV221Tests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        site = root / "_site"
        site.mkdir()
        (site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>الرئيسية</title>'
            '<meta name="description" content="الصفحة الرئيسية">'
            '<meta name="robots" content="index,follow">'
            f'<link rel="canonical" href="{module.BASE}">'
            '</head><body><nav><a href="encyclopedia/">الموسوعة</a></nav>'
            '<main><h1>المنصة</h1></main></body></html>',
            encoding="utf-8",
        )
        routes = {
            "encyclopedia": "الموسوعة النفسية",
            "special-needs": "ذوو الاحتياجات الخاصة",
            "care-guides": "أدلة التعامل",
            "api": "واجهة API",
            "comparisons": "المقارنات",
            "library": "المكتبة",
            "daily-tools": "الأدوات التفاعلية",
            "assessment-lab": "مختبر المقاييس",
            "cognitive-lab": "مختبر القدرات",
            "developers": "واجهة المطورين",
        }
        for route, title in routes.items():
            directory = site / route
            directory.mkdir(parents=True)
            (directory / "index.html").write_text(page(title, route + "/"), encoding="utf-8")
        hidden = site / "private-preview"
        hidden.mkdir()
        (hidden / "index.html").write_text(
            page("معاينة خاصة", "private-preview/", robots="noindex,nofollow"),
            encoding="utf-8",
        )
        assets = site / "assets"
        assets.mkdir()
        (assets / "index.html").write_text(page("أصول", "assets/"), encoding="utf-8")

        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )
        api = site / "api/v1"
        api.mkdir(parents=True, exist_ok=True)
        (api / "sections.json").write_text(
            json.dumps({"api_version": "v1", "count": 1, "sections": [{"id": "legacy"}]}),
            encoding="utf-8",
        )
        (api / "openapi.json").write_text(
            json.dumps({
                "openapi": "3.1.0",
                "paths": {"/api/v1/health.json": {"get": {"responses": {"200": {"description": "ok"}}}}},
                "components": {"schemas": {}},
            }),
            encoding="utf-8",
        )
        (api / "platform.json").write_text(
            json.dumps({
                "apiVersion": "1.0.0",
                "resources": [{"id": "existing", "url": module.BASE + "encyclopedia/"}],
                "endpoints": {"platform": module.BASE + "api/v1/platform.json"},
            }),
            encoding="utf-8",
        )
        report = root / ".build/reports"
        report.mkdir(parents=True)
        (report / "public-api-v215.json").write_text(
            json.dumps({"schema_version": 215, "endpoints": 1}),
            encoding="utf-8",
        )
        return site

    def test_directory_is_separate_idempotent_and_public_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = self.fixture(root)
            legacy = site / "api/v1/sections.json"
            legacy_hash = hashlib.sha256(legacy.read_bytes()).hexdigest()

            first = module.publish(site, root)
            second = module.publish(site, root)
            self.assertEqual(first["schema_version"], 221)
            self.assertEqual(second["section_count"], first["section_count"])
            self.assertTrue(first["legacy_sections_endpoint_preserved"])
            self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(), legacy_hash)

            homepage = (site / "index.html").read_text(encoding="utf-8")
            self.assertEqual(homepage.count(module.START), 1)
            self.assertEqual(homepage.count('href="sections/"'), 2)
            self.assertEqual(homepage.count('id="section-directory-style-v221"'), 1)
            for route in module.FEATURED:
                self.assertIn(f'href="{route}"', homepage)

            directory = (site / "sections/index.html").read_text(encoding="utf-8")
            self.assertIn("دليل جميع أقسام المنصة", directory)
            self.assertIn("BreadcrumbList", directory)
            self.assertNotIn("معاينة خاصة", directory)
            self.assertNotIn(">أصول<", directory)
            self.assertFalse(any(value in directory for value in module.BANNED))

            payload = json.loads((site / "api/v1/section-directory.json").read_text(encoding="utf-8"))
            routes = {item["route"] for item in payload["items"]}
            self.assertIn("encyclopedia/", routes)
            self.assertNotIn("private-preview/", routes)
            self.assertNotIn("assets/", routes)
            self.assertEqual(payload["section_count"], len(payload["items"]))

            openapi = json.loads((site / "api/v1/openapi.json").read_text(encoding="utf-8"))
            self.assertIn("/api/v1/health.json", openapi["paths"])
            self.assertIn("/api/v1/section-directory.json", openapi["paths"])
            platform = json.loads((site / "api/v1/platform.json").read_text(encoding="utf-8"))
            resources = [item for item in platform["resources"] if item.get("id") == "section-directory"]
            self.assertEqual(len(resources), 1)
            self.assertEqual(
                platform["endpoints"]["sectionDirectory"],
                module.BASE + "api/v1/section-directory.json",
            )

            tree = ET.parse(site / "sitemap.xml")
            links = [
                (node.text or "").strip()
                for node in tree.getroot().findall("{*}sitemap/{*}loc")
            ]
            self.assertEqual(links.count(module.BASE + "sitemap-sections.xml"), 1)
            public_report = json.loads(
                (root / ".build/reports/public-api-v215.json").read_text(encoding="utf-8")
            )
            self.assertTrue(public_report["section_directory"])
            self.assertEqual(public_report["section_directory_schema_version"], 221)


if __name__ == "__main__":
    unittest.main()
