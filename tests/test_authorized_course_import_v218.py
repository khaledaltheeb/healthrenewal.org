from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / "scripts" / "import_authorized_courses_v218.py"
VERIFIER = ROOT / "scripts" / "verify_authorized_course_import_v218.py"


class AuthorizedCourseImportTests(unittest.TestCase):
    def make_site(self, root: Path, *, sitemap_index: bool = True) -> Path:
        site = root / "site"
        (site / "api" / "v1").mkdir(parents=True)
        if sitemap_index:
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
                encoding="utf-8",
            )
        else:
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
                encoding="utf-8",
            )
        # Production copies these public contracts before running the importer.
        for name in ("platform.json", "openapi.json", "courses.schema.json", "course-provider-registry.schema.json"):
            (site / "api" / "v1" / name).write_bytes((ROOT / "api" / "v1" / name).read_bytes())
        return site

    def empty_registry(self, root: Path) -> Path:
        path = root / "registry.json"
        path.write_text(
            json.dumps(
                {
                    "registryVersion": "1.0",
                    "updatedAt": date.today().isoformat(),
                    "policy": "permission_required",
                    "providers": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def provider_registry(self, root: Path) -> Path:
        verified = date.today() - timedelta(days=1)
        expires = date.today() + timedelta(days=365)
        path = root / "registry.json"
        path.write_text(
            json.dumps(
                {
                    "registryVersion": "1.0",
                    "updatedAt": date.today().isoformat(),
                    "policy": "permission_required",
                    "providers": [
                        {
                            "id": "example-academy",
                            "name": "Example Academy",
                            "website": "https://courses.example.org/",
                            "status": "authorized",
                            "authorization": {
                                "evidenceUrl": "https://courses.example.org/authorization",
                                "license": "Metadata reuse agreement",
                                "verifiedAt": verified.isoformat(),
                                "expiresAt": expires.isoformat(),
                            },
                            "feed": {
                                "url": "https://courses.example.org/feed.json",
                                "format": "authorized-course-feed-v1",
                                "allowedHosts": ["courses.example.org"],
                                "maxBytes": 100000,
                                "sha256": None,
                            },
                            "rights": {
                                "metadataReuse": True,
                                "contentReuse": False,
                                "attributionRequired": True,
                                "attributionText": "بيانات الدورة مقدمة بإذن من Example Academy.",
                            },
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def valid_feed(self, root: Path, *, content_reuse: bool = False) -> Path:
        feeds = root / "feeds"
        feeds.mkdir()
        verified = date.today() - timedelta(days=1)
        payload = {
            "feedVersion": "1.0",
            "provider": {
                "id": "example-academy",
                "name": "Example Academy",
                "website": "https://courses.example.org/",
            },
            "authorization": {
                "status": "authorized",
                "evidenceUrl": "https://courses.example.org/authorization",
                "license": "Metadata reuse agreement",
                "verifiedAt": verified.isoformat(),
                "expiresAt": (date.today() + timedelta(days=365)).isoformat(),
            },
            "courses": [
                {
                    "id": "mental-health-foundations",
                    "title": "أساسيات التثقيف في الصحة النفسية",
                    "summary": "دورة تعليمية تمهيدية؛ التسجيل والمحتوى لدى المزود الأصلي.",
                    "language": "ar",
                    "canonicalUrl": "https://courses.example.org/courses/mental-health-foundations",
                    "enrollmentUrl": "https://courses.example.org/enroll/mental-health-foundations",
                    "providerName": "Example Academy",
                    "instructors": ["مدرب تجريبي"],
                    "categories": ["الصحة النفسية"],
                    "audience": ["المهتمون بالتثقيف النفسي"],
                    "deliveryMode": "online",
                    "price": 25,
                    "currency": "JOD",
                    "startsAt": None,
                    "endsAt": None,
                    "duration": "8 ساعات",
                    "status": "open",
                    "updatedAt": "2026-07-25T00:00:00Z",
                    "rights": {
                        "metadataReuse": True,
                        "contentReuse": content_reuse,
                        "attributionText": "بيانات الدورة مقدمة بإذن من Example Academy.",
                    },
                }
            ],
        }
        (feeds / "example-academy.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return feeds

    def run_import(self, site: Path, registry: Path, feeds: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("COURSE_IMPORT_NETWORK_ENABLED", None)
        env.pop("COURSE_IMPORT_APPROVED_PROVIDERS", None)
        return subprocess.run(
            [sys.executable, str(IMPORTER), str(site), "--registry", str(registry), "--feeds-dir", str(feeds), *extra],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_empty_registry_publishes_safe_empty_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            site = self.make_site(root)
            result = self.run_import(site, self.empty_registry(root), root / "feeds")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            catalog = json.loads((site / "api" / "v1" / "courses.json").read_text(encoding="utf-8"))
            self.assertEqual(catalog["status"], "no-authorized-feeds")
            self.assertEqual(catalog["courseCount"], 0)
            self.assertFalse(catalog["contentReuse"])
            verify = subprocess.run([sys.executable, str(VERIFIER), str(site)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr + verify.stdout)

    def test_valid_local_authorized_feed_imports_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            site = self.make_site(root, sitemap_index=False)
            result = self.run_import(site, self.provider_registry(root), self.valid_feed(root))
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            catalog = json.loads((site / "api" / "v1" / "courses.json").read_text(encoding="utf-8"))
            self.assertEqual(catalog["providerCount"], 1)
            self.assertEqual(catalog["courseCount"], 1)
            course = catalog["courses"][0]
            self.assertEqual(course["globalId"], "example-academy:mental-health-foundations")
            self.assertNotIn("lessons", course)
            self.assertNotIn("content", course)
            self.assertEqual(course["currency"], "JOD")

    def test_remote_fetch_is_blocked_without_explicit_environment_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            site = self.make_site(root)
            result = self.run_import(site, self.provider_registry(root), root / "missing-feeds", "--fetch-remote")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires explicit environment approval", result.stderr + result.stdout)

    def test_feed_rejects_course_content_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            site = self.make_site(root)
            result = self.run_import(site, self.provider_registry(root), self.valid_feed(root, content_reuse=True))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Course rights are invalid", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
