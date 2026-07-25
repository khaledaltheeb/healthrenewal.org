from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.upgrade_public_api_manifest_v231 import (
    API_VERSION,
    ENDPOINTS,
    PROHIBITED_PUBLIC_TERMS,
    SCHEMA_VERSION,
    SECTION_DEFINITIONS,
    PublicApiManifestError,
    upgrade,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_fixture(root: Path) -> Path:
    site = root / "_site"
    for item in SECTION_DEFINITIONS:
        page = site / item["route"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            f'<!doctype html><html lang="ar" dir="rtl"><head><title>{item["name_ar"]}</title></head><body><main><h1>{item["name_ar"]}</h1></main></body></html>',
            encoding="utf-8",
        )

    api = site / "api" / "v1"
    api.mkdir(parents=True, exist_ok=True)
    write_json(
        api / "platform.json",
        {
            "apiVersion": "1.0.0",
            "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "licenseNotice": "حقوق كل مورد تخضع لمصدره وترخيصه.",
            "disclaimer": "المحتوى للتثقيف العام.",
            "integrationPolicy": {
                "externalCourseImport": "permission_required",
                "prohibited": ["copying protected course materials"],
            },
        },
    )
    write_json(api / "sections.json", {"api_version": "v1", "count": 1, "sections": []})
    write_json(
        api / "openapi.json",
        {
            "openapi": "3.1.0",
            "info": {"title": "واجهة قديمة", "version": "1.0.0"},
            "paths": {
                "/api/v1/health.json": {"get": {"responses": {"200": {"description": "ok"}}}},
                "/api/v1/courses.json": {"get": {"responses": {"200": {"description": "ok"}}}},
            },
            "components": {"schemas": {"Course": {"type": "object"}}},
        },
    )
    for name, payload in {
        "health.json": {"status": "ok"},
        "site.json": {"name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة"},
        "courses.json": {"api_version": "v1", "count": 0, "courses": []},
        "sources.json": {"api_version": "v1", "count": 0, "sources": []},
        "content-index.json": {"api_version": "v1", "total": 0, "shards": []},
        "taxonomy.json": {"api_version": "v1", "total_pages": 0},
        "courses.schema.json": {"type": "object"},
        "courses.example.json": {"schema_version": 215, "courses": []},
    }.items():
        write_json(api / name, payload)

    developers = site / "developers" / "index.html"
    developers.parent.mkdir(parents=True, exist_ok=True)
    developers.write_text(
        '<!doctype html><html lang="ar" dir="rtl"><body><main><div class="status"><span>الإصدار: v1</span></div><section class="panel"><table><tbody></tbody></table></section></main></body></html>',
        encoding="utf-8",
    )
    return site


class PublicApiManifestV231Tests(unittest.TestCase):
    def test_upgrades_manifest_sections_openapi_and_developers_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = make_fixture(root)
            api = site / "api" / "v1"
            courses_before = (api / "courses.json").read_bytes()
            sources_before = (api / "sources.json").read_bytes()

            report = upgrade(site, root)
            platform = json.loads((api / "platform.json").read_text(encoding="utf-8"))
            sections = json.loads((api / "sections.json").read_text(encoding="utf-8"))
            openapi = json.loads((api / "openapi.json").read_text(encoding="utf-8"))
            developers = (site / "developers" / "index.html").read_text(encoding="utf-8")

            self.assertEqual(report["status"], "passed")
            self.assertEqual(platform["apiVersion"], API_VERSION)
            self.assertEqual(platform["schemaVersion"], SCHEMA_VERSION)
            self.assertEqual(platform["integrationPolicy"]["defaultDecision"], "deny")
            self.assertTrue(platform["privacyBoundary"]["publicMetadataOnly"])
            self.assertEqual(set(platform["endpoints"]), set(ENDPOINTS))
            self.assertEqual(sections["count"], len(SECTION_DEFINITIONS))
            self.assertEqual(
                {item["id"] for item in sections["sections"]},
                {item["id"] for item in SECTION_DEFINITIONS},
            )
            self.assertIn("/api/v1/platform.json", openapi["paths"])
            self.assertIn("/api/v1/sections.json", openapi["paths"])
            self.assertIn("PlatformManifest", openapi["components"]["schemas"])
            self.assertIn("SectionsIndex", openapi["components"]["schemas"])
            self.assertIn("Course", openapi["components"]["schemas"])
            self.assertEqual(developers.count("data-platform-manifest-v231"), 1)
            self.assertIn("الإصدار: v1.1", developers)
            self.assertEqual((api / "courses.json").read_bytes(), courses_before)
            self.assertEqual((api / "sources.json").read_bytes(), sources_before)
            self.assertTrue((site / "api" / "public-api-manifest-v231.json").is_file())
            self.assertTrue((root / ".build" / "reports" / "public-api-manifest-v231.json").is_file())

    def test_platform_resources_match_the_openapi_resource_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = make_fixture(root)
            upgrade(site, root)
            api = site / "api" / "v1"
            platform = json.loads((api / "platform.json").read_text(encoding="utf-8"))
            openapi = json.loads((api / "openapi.json").read_text(encoding="utf-8"))
            manifest_schema = openapi["components"]["schemas"]["PlatformManifest"]
            reference = manifest_schema["properties"]["resources"]["items"]["$ref"]
            resource_schema = openapi["components"]["schemas"][reference.rsplit("/", 1)[-1]]
            required = set(resource_schema["required"])
            for resource in platform["resources"]:
                self.assertTrue(required.issubset(resource), (required, resource))

    def test_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = make_fixture(root)
            upgrade(site, root)
            tracked = [
                site / "api" / "v1" / "platform.json",
                site / "api" / "v1" / "sections.json",
                site / "api" / "v1" / "openapi.json",
                site / "developers" / "index.html",
            ]
            before = {path: path.read_bytes() for path in tracked}
            second = upgrade(site, root)
            after = {path: path.read_bytes() for path in tracked}
            self.assertEqual(before, after)
            self.assertFalse(second["developers_page_changed"])

    def test_missing_published_route_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = make_fixture(root)
            missing = site / "library" / "index.html"
            missing.unlink()
            with self.assertRaisesRegex(PublicApiManifestError, "published section routes are missing"):
                upgrade(site, root)

    def test_missing_endpoint_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = make_fixture(root)
            (site / "api" / "v1" / "taxonomy.json").unlink()
            with self.assertRaisesRegex(PublicApiManifestError, "public API endpoint files are missing"):
                upgrade(site, root)

    def test_public_outputs_avoid_prohibited_terminology(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = make_fixture(root)
            upgrade(site, root)
            combined = "\n".join(
                (site / "api" / "v1" / name).read_text(encoding="utf-8")
                for name in ("platform.json", "sections.json", "openapi.json")
            )
            for term in PROHIBITED_PUBLIC_TERMS:
                self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
