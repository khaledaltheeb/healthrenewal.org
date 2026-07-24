from __future__ import annotations

import importlib.util
import sys
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


PUBLISHER = load_module(
    "public_api_permission_revalidation_v218",
    ROOT / "scripts" / "publish_public_api_v215.py",
)


class PublicApiPermissionRevalidationV218Tests(unittest.TestCase):
    def approved_source(self, expires_at: str = "2027-12-31") -> dict:
        return {
            "id": "example-provider",
            "provider": "Example Provider",
            "enabled": True,
            "permission_status": "approved",
            "permission_reference": "private-written-evidence",
            "permission_granted_at": "2026-07-20",
            "permission_duration": "fixed",
            "permission_expires_at": expires_at,
            "license_url": "https://courses.example.org/license",
            "allowed_actions": ["import_catalog"],
            "format": "json",
            "feed_url": "https://courses.example.org/feed.json",
            "allowed_hosts": ["courses.example.org"],
            "course_hosts": ["courses.example.org"],
        }

    def course(self, expires_at="2027-12-31") -> dict:
        return {
            "id": "example-provider:course-1",
            "source_id": "example-provider",
            "provider": "Example Provider",
            "title_ar": "دورة دعم الأسرة",
            "title": "Family Support",
            "description_ar": "وصف عربي.",
            "description": "English description.",
            "url": "https://courses.example.org/course-1",
            "language": "ar",
            "format": "online",
            "duration": "4 hours",
            "price_text": "",
            "updated_at": None,
            "license_url": "https://courses.example.org/license",
            "permission_status": "approved",
            "permission_expires_at": expires_at,
        }

    def test_public_sources_revalidate_permission_and_hide_private_evidence(self) -> None:
        sources = PUBLISHER.public_sources({"sources": [self.approved_source()]})
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["permission_duration"], "fixed")
        self.assertEqual(sources[0]["permission_expires_at"], "2027-12-31")
        self.assertNotIn("permission_reference", sources[0])

        with self.assertRaises(PUBLISHER.PublicApiError):
            PUBLISHER.public_sources(
                {"sources": [self.approved_source("2026-01-01")]}
            )

    def test_publisher_rejects_missing_or_expired_course_permission(self) -> None:
        imported = {
            "schema_version": 215,
            "status": "ready",
            "sources_processed": 1,
            "courses": [self.course()],
        }
        validated = PUBLISHER.validate_courses(imported, {"example-provider"})
        self.assertEqual(len(validated), 1)

        missing = self.course()
        missing.pop("permission_expires_at")
        with self.assertRaises(PUBLISHER.PublicApiError):
            PUBLISHER.validate_courses(
                {**imported, "courses": [missing]},
                {"example-provider"},
            )

        with self.assertRaises(PUBLISHER.PublicApiError):
            PUBLISHER.validate_courses(
                {**imported, "courses": [self.course("2026-01-01")]},
                {"example-provider"},
            )

    def test_openapi_course_schema_exposes_permission_expiry(self) -> None:
        schema = PUBLISHER.course_schema()
        field = schema["properties"]["permission_expires_at"]
        self.assertEqual(field["format"], "date")
        self.assertEqual(field["type"], ["string", "null"])


if __name__ == "__main__":
    unittest.main()
