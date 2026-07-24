from __future__ import annotations

import importlib.util
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


IMPORTER = load_module(
    "course_importer_v215",
    ROOT / "scripts" / "import_authorized_courses_v215.py",
)
PUBLISHER = load_module(
    "public_api_v215",
    ROOT / "scripts" / "publish_public_api_v215.py",
)


class PublicApiV215Tests(unittest.TestCase):
    def approved_source(self) -> dict:
        return {
            "id": "example-provider",
            "provider": "Example Provider",
            "enabled": True,
            "permission_status": "approved",
            "permission_reference": "written-permission-2026-07-20",
            "permission_granted_at": "2026-07-20",
            "permission_duration": "fixed",
            "permission_expires_at": "2027-12-31",
            "license_url": "https://courses.example.org/license",
            "allowed_actions": ["import_catalog"],
            "format": "json",
            "feed_url": "https://courses.example.org/feed.json",
            "allowed_hosts": ["courses.example.org"],
            "course_hosts": ["courses.example.org"],
        }

    def test_homepage_hides_internal_execution_copy(self) -> None:
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        forbidden = (
            "خطة نمو قابلة للقياس",
            "الأهداف الدنيا للمحتوى",
            "هدف توسع",
            "خط أساس المصدر الحالي",
            "مسار مستقبلي للحسابات المؤسسية",
            "built-not-published",
            "ما سيتم إنجازه",
        )
        for phrase in forbidden:
            self.assertNotIn(phrase, text)

    def test_default_manifest_is_closed_empty_and_time_bounded(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "content"
                / "integrations"
                / "course-sources-v215.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["policy"], "deny-by-default")
        self.assertEqual(manifest["security_contract_version"], 218)
        self.assertIn("permission_duration", manifest["required_permission_fields"])
        self.assertIn("permission_expires_at", manifest["required_permission_fields"])
        self.assertEqual(manifest["sources"], [])

    def test_importer_rejects_enabled_source_without_permission(self) -> None:
        source = self.approved_source()
        source["permission_status"] = "requested"
        with self.assertRaises(IMPORTER.CourseImportError):
            IMPORTER.validate_source(source)

    def test_importer_requires_explicit_active_permission_window(self) -> None:
        missing = self.approved_source()
        missing.pop("permission_duration")
        with self.assertRaises(IMPORTER.CourseImportError):
            IMPORTER.validate_source(missing)

        expired = self.approved_source()
        expired["permission_expires_at"] = "2026-01-01"
        with self.assertRaises(IMPORTER.CourseImportError):
            IMPORTER.validate_source(expired)

        perpetual = self.approved_source()
        perpetual["permission_duration"] = "perpetual"
        perpetual["permission_expires_at"] = None
        approved = IMPORTER.validate_source(perpetual)
        self.assertEqual(approved.permission_duration, "perpetual")
        self.assertIsNone(approved.permission_expires_at)

    def test_importer_rejects_feed_outside_allowlist(self) -> None:
        source = self.approved_source()
        source["feed_url"] = "https://unapproved.example.net/feed.json"
        with self.assertRaises(IMPORTER.CourseImportError):
            IMPORTER.validate_source(source)

    def test_importer_rejects_ip_literals_local_hosts_and_wildcards(self) -> None:
        cases = (
            ("127.0.0.1", "https://127.0.0.1/feed.json"),
            ("localhost", "https://localhost/feed.json"),
            ("catalog.local", "https://catalog.local/feed.json"),
            ("*.example.org", "https://courses.example.org/feed.json"),
        )
        for host, feed_url in cases:
            source = self.approved_source()
            source["allowed_hosts"] = [host]
            source["feed_url"] = feed_url
            with self.subTest(host=host), self.assertRaises(
                IMPORTER.CourseImportError
            ):
                IMPORTER.validate_source(source)

    def test_importer_rejects_private_dns_and_redirect_escape(self) -> None:
        source = IMPORTER.validate_source(self.approved_source())
        private_answer = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443))
        ]
        with mock.patch.object(
            IMPORTER.socket, "getaddrinfo", return_value=private_answer
        ):
            with self.assertRaises(IMPORTER.CourseImportError):
                IMPORTER.validate_network_target(
                    source.feed_url, source, "feed URL"
                )

        handler = IMPORTER.SafeRedirectHandler(source)
        with self.assertRaises(IMPORTER.CourseImportError):
            handler.redirect_request(
                None,
                None,
                302,
                "Found",
                {},
                "https://unapproved.example.net/feed.json",
            )

    def test_dns_answers_are_pinned_for_the_connection(self) -> None:
        public_answer = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ]
        private_answer = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("10.0.0.8", 443),
            )
        ]
        with mock.patch.object(
            IMPORTER.socket,
            "getaddrinfo",
            side_effect=[public_answer, private_answer],
        ) as dns:
            resolver = IMPORTER.PinnedDnsResolver()
            self.assertEqual(
                resolver.pin("courses.example.org"),
                ("93.184.216.34",),
            )
            with resolver.active():
                first = IMPORTER.socket.getaddrinfo(
                    "courses.example.org",
                    443,
                    type=socket.SOCK_STREAM,
                )
                second = IMPORTER.socket.getaddrinfo(
                    "courses.example.org",
                    443,
                    type=socket.SOCK_STREAM,
                )
            self.assertEqual(dns.call_count, 1)
            self.assertEqual(first[0][4][0], "93.184.216.34")
            self.assertEqual(second[0][4][0], "93.184.216.34")

    def test_pinned_resolver_blocks_unvalidated_host(self) -> None:
        public_answer = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ]
        with mock.patch.object(
            IMPORTER.socket,
            "getaddrinfo",
            return_value=public_answer,
        ):
            resolver = IMPORTER.PinnedDnsResolver()
            resolver.pin("courses.example.org")
            with resolver.active(), self.assertRaises(socket.gaierror):
                IMPORTER.socket.getaddrinfo(
                    "other.example.org",
                    443,
                    type=socket.SOCK_STREAM,
                )

    def test_empty_manifest_writes_hardened_security_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            output = root / "courses.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 215,
                        "policy": "deny-by-default",
                        "sources": [],
                    }
                ),
                encoding="utf-8",
            )
            result = IMPORTER.import_courses(manifest, output)
            self.assertEqual(result["status"], "no-approved-sources")
            self.assertEqual(result["security_contract_version"], 218)
            self.assertTrue(result["security"]["dns_public_addresses_only"])
            self.assertTrue(
                result["security"]["dns_answers_pinned_during_connection"]
            )
            self.assertTrue(
                result["security"]["redirects_checked_before_request"]
            )
            self.assertTrue(output.is_file())

    def test_course_normalization_strips_html_controls_and_enforces_hosts(self) -> None:
        source = IMPORTER.validate_source(self.approved_source())
        course = IMPORTER.normalize_course(
            {
                "id": "course-1",
                "title_ar": "<b>دورة\u202e دعم الأسرة</b>",
                "description_ar": "<p>محتوى تعليمي منظم.</p>",
                "url": "https://courses.example.org/course-1",
                "language": "ar",
                "updated_at": "2026-07-20T10:00:00Z",
            },
            source,
        )
        self.assertEqual(course["title_ar"], "دورة دعم الأسرة")
        self.assertEqual(course["permission_status"], "approved")
        self.assertEqual(course["permission_expires_at"], "2027-12-31")
        self.assertNotIn("<", course["description_ar"])
        self.assertNotIn("\u202e", course["title_ar"])

    def test_course_normalization_rejects_bad_id_and_naive_timestamp(self) -> None:
        source = IMPORTER.validate_source(self.approved_source())
        base = {
            "title_ar": "دورة دعم الأسرة",
            "url": "https://courses.example.org/course-1",
        }
        with self.assertRaisesRegex(
            IMPORTER.CourseImportError, "course id must use"
        ):
            IMPORTER.normalize_course({**base, "id": "bad/id"}, source)
        with self.assertRaisesRegex(
            IMPORTER.CourseImportError, "must include a timezone"
        ):
            IMPORTER.normalize_course(
                {
                    **base,
                    "id": "course-1",
                    "updated_at": "2026-07-20T10:00:00",
                },
                source,
            )

    def test_json_feed_rejects_non_object_records(self) -> None:
        with self.assertRaisesRegex(
            IMPORTER.CourseImportError,
            "each JSON course record must be an object",
        ):
            IMPORTER.parse_feed(b'{"courses":[{"id":"one"},"bad"]}', "json")

    def test_duplicate_enabled_source_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            output = root / "courses.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 215,
                        "policy": "deny-by-default",
                        "sources": [
                            self.approved_source(),
                            self.approved_source(),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(
                IMPORTER, "fetch_feed", return_value=b"[]"
            ), self.assertRaisesRegex(
                IMPORTER.CourseImportError,
                "duplicate enabled source id",
            ):
                IMPORTER.import_courses(manifest, output)

    def test_publisher_preserves_existing_api_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            site = root / "site"
            site.mkdir()
            manifest = root / "manifest.json"
            imported = root / "imported.json"
            api = site / "api" / "v1"
            api.mkdir(parents=True)

            (api / "openapi.json").write_text(
                json.dumps(
                    {
                        "openapi": "3.1.0",
                        "info": {
                            "title": "Original API",
                            "version": "0.9.0",
                        },
                        "paths": {
                            "/api/v1/platform.json": {
                                "get": {
                                    "summary": "Existing platform endpoint"
                                }
                            }
                        },
                        "components": {
                            "schemas": {"Platform": {"type": "object"}}
                        },
                    }
                ),
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 215,
                        "policy": "deny-by-default",
                        "sources": [self.approved_source()],
                    }
                ),
                encoding="utf-8",
            )
            imported.write_text(
                json.dumps(
                    {
                        "schema_version": 215,
                        "status": "ready",
                        "sources_processed": 1,
                        "courses": [
                            {
                                "id": "example-provider:course-1",
                                "source_id": "example-provider",
                                "provider": "Example Provider",
                                "title_ar": "دورة دعم الأسرة",
                                "title": "Family Support",
                                "description_ar": "وصف عربي.",
                                "description": "English description.",
                                "url": (
                                    "https://courses.example.org/course-1"
                                ),
                                "language": "ar",
                                "format": "online",
                                "duration": "4 hours",
                                "price_text": "",
                                "updated_at": None,
                                "license_url": (
                                    "https://courses.example.org/license"
                                ),
                                "permission_status": "approved",
                                "permission_expires_at": "2027-12-31",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = PUBLISHER.publish(
                site=site,
                manifest_path=manifest,
                import_path=imported,
            )
            openapi = json.loads(
                (api / "openapi.json").read_text(encoding="utf-8")
            )
            self.assertIn("/api/v1/platform.json", openapi["paths"])
            self.assertIn("/api/v1/health.json", openapi["paths"])
            self.assertIn("Platform", openapi["components"]["schemas"])
            self.assertIn("Course", openapi["components"]["schemas"])
            self.assertTrue(report["preserved_existing_paths"])
            self.assertTrue(
                (site / "developers" / "index.html").is_file()
            )
            self.assertTrue(
                (site / "sitemap-developers.xml").is_file()
            )


if __name__ == "__main__":
    unittest.main()
