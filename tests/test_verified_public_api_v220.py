from __future__ import annotations

import importlib.util
import json
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


VERIFIER = load_module(
    "verified_public_api_v220",
    ROOT / "scripts" / "publish_verified_public_api_v220.py",
)

CORE = (
    ("encyclopedia", "الموسوعة النفسية العربية", "encyclopedia/"),
    ("special-needs", "ذوو الاحتياجات الخاصة والتربية الدامجة", "special-needs/"),
    ("care-guides", "أدلة التعامل العملي", "care-guides/"),
    ("tips", "النصائح النفسية العملية", "tips/"),
    ("assessment-lab", "المقاييس والاستكشاف", "assessment-lab/"),
    ("cognitive-lab", "القدرات المعرفية", "cognitive-lab/"),
    ("magazine", "المجلة والأبحاث", "magazine/"),
)


class VerifiedPublicApiV220Tests(unittest.TestCase):
    def write_page(self, site: Path, route: str) -> None:
        page = site / route / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>صفحة اختبار</title>'
            f'<link rel="canonical" href="{VERIFIER.BASE_URL}{route}"></head>'
            '<body><h1>عنوان الصفحة</h1></body></html>',
            encoding="utf-8",
        )

    def prepare_site(self, root: Path, *, omit: str | None = None) -> Path:
        site = root / "site"
        api = site / "api" / "v1"
        api.mkdir(parents=True)
        sections = []
        for section_id, name_ar, route in CORE:
            sections.append(
                {
                    "id": section_id,
                    "name_ar": name_ar,
                    "url": VERIFIER.BASE_URL + route,
                }
            )
            if route != omit:
                self.write_page(site, route)
        (api / "sections.json").write_text(
            json.dumps(
                {"api_version": "v1", "count": len(sections), "sections": sections},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (api / "site.json").write_text(
            json.dumps({"name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة"}, ensure_ascii=False),
            encoding="utf-8",
        )
        return site

    def test_verifies_core_routes_and_adds_only_existing_optional_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = self.prepare_site(Path(temp))
            self.write_page(site, "daily-tools/")
            self.write_page(site, "learning-paths/")
            report = VERIFIER.verify_and_expand_sections(site)
            payload = json.loads((site / "api/v1/sections.json").read_text(encoding="utf-8"))
            ids = [item["id"] for item in payload["sections"]]
            self.assertEqual(payload["contract_version"], 220)
            self.assertTrue(payload["all_routes_verified"])
            self.assertEqual(payload["count"], len(CORE) + 2)
            self.assertIn("daily-tools", ids)
            self.assertIn("learning-paths", ids)
            self.assertNotIn("partners", ids)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue(report["all_routes_verified"])
            self.assertEqual(
                set(report["optional_sections_added"]),
                {"daily-tools", "learning-paths"},
            )
            site_payload = json.loads((site / "api/v1/site.json").read_text(encoding="utf-8"))
            self.assertEqual(site_payload["verified_section_count"], len(CORE) + 2)
            self.assertEqual(site_payload["section_route_contract"], 220)

    def test_missing_core_route_fails_before_publication_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = self.prepare_site(Path(temp), omit="assessment-lab/")
            with self.assertRaises(VERIFIER.VerifiedApiError):
                VERIFIER.verify_and_expand_sections(site)

    def test_section_url_cannot_escape_platform_base(self) -> None:
        with self.assertRaises(VERIFIER.VerifiedApiError):
            VERIFIER.route_from_url("https://example.org/encyclopedia/")
        with self.assertRaises(VERIFIER.VerifiedApiError):
            VERIFIER.route_from_url(VERIFIER.BASE_URL + "../private/")

    def test_developer_sitemap_registration_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp) / "site"
            site.mkdir()
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
                encoding="utf-8",
            )
            (site / "sitemap-developers.xml").write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<url><loc>{VERIFIER.BASE_URL}developers/</loc></url></urlset>',
                encoding="utf-8",
            )
            VERIFIER.register_developers_sitemap(site)
            VERIFIER.register_developers_sitemap(site)
            text = (site / "sitemap.xml").read_text(encoding="utf-8")
            self.assertEqual(text.count("sitemap-developers.xml"), 1)

    def test_health_and_daily_tool_wrappers_are_connected(self) -> None:
        health = (ROOT / "scripts/enforce_health_publication_gate_v192.py").read_text(encoding="utf-8")
        daily = (ROOT / "scripts/verify_daily_tools_v24.py").read_text(encoding="utf-8")
        self.assertIn("publish_verified(SITE)", health)
        self.assertIn("verify_and_expand_sections(site)", daily)
        self.assertIn("public_api_routes_verified", health)
        self.assertIn("api_sections_refreshed", daily)


if __name__ == "__main__":
    unittest.main()
