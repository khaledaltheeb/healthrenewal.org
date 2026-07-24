from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


seo = load("seo_v201", "scripts/publish_content_discovery_v201.py")
courses = load("courses_v201", "scripts/publish_authorized_courses_v201.py")

PAGE = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
<title>{title} | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="{description}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}">
</head>
<body><main><h1>{h1}</h1><p>{body}</p></main></body>
</html>
"""


class ContentDiscoveryTests(unittest.TestCase):
    def test_enriches_and_builds_public_discovery_indexes_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text(
                PAGE.format(
                    title="منصة عربية للصحة النفسية",
                    description="موسوعة عربية موثوقة في الصحة النفسية وعلم النفس.",
                    robots="index,follow",
                    canonical=seo.BASE_URL,
                    h1="الصحة النفسية وعلم النفس",
                    body="محتوى عربي منظم للأسرة والطفل.",
                ),
                encoding="utf-8",
            )
            autism = site / "special-needs" / "autism" / "index.html"
            autism.parent.mkdir(parents=True)
            autism.write_text(
                PAGE.format(
                    title="دليل اضطراب طيف التوحد",
                    description="دليل موسع لفهم التوحد والتدخل المبكر والدعم الأسري والتربية الدامجة.",
                    robots="index,follow",
                    canonical=seo.BASE_URL + "special-needs/autism/",
                    h1="اضطراب طيف التوحد",
                    body="شرح التوحد للأشخاص ذوي الاحتياجات الخاصة دون وصم.",
                ),
                encoding="utf-8",
            )
            private = site / "private" / "index.html"
            private.parent.mkdir()
            private.write_text(
                PAGE.format(
                    title="خاص",
                    description="صفحة خاصة لا تظهر في الفهرس العام.",
                    robots="noindex,nofollow",
                    canonical=seo.BASE_URL + "private/",
                    h1="خاص",
                    body="خاص",
                ),
                encoding="utf-8",
            )

            first = seo.publish(site)
            self.assertEqual(first["pages_indexed"], 2)
            enriched = autism.read_text(encoding="utf-8")
            self.assertIn('name="keywords"', enriched)
            self.assertIn(seo.TOPICAL_MARKER, enriched)
            self.assertIn("اضطراب طيف التوحد", enriched)
            self.assertIn("التربية الدامجة", enriched)

            index = json.loads((site / "api" / "v1" / "content-index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["total"], 2)
            self.assertFalse(any(item["path"] == "/private/" for item in index["items"]))
            autism_item = next(item for item in index["items"] if item["path"] == "/special-needs/autism/")
            self.assertIn("التوحد", " ".join(autism_item["tags"]))

            taxonomy = json.loads((site / "api" / "v1" / "taxonomy.json").read_text(encoding="utf-8"))
            self.assertEqual(taxonomy["totalPages"], 2)
            self.assertIsInstance(taxonomy["languages"], list)
            self.assertIsInstance(taxonomy["sections"], list)
            self.assertIsInstance(taxonomy["tags"], list)

            before = autism.read_text(encoding="utf-8")
            second = seo.publish(site)
            self.assertEqual(second["pages_changed"], 0)
            self.assertEqual(before, autism.read_text(encoding="utf-8"))

    def test_repository_api_placeholders_match_public_contract(self):
        content_index = json.loads((ROOT / "api" / "v1" / "content-index.json").read_text(encoding="utf-8"))
        taxonomy = json.loads((ROOT / "api" / "v1" / "taxonomy.json").read_text(encoding="utf-8"))
        catalog = json.loads((ROOT / "api" / "v1" / "courses.json").read_text(encoding="utf-8"))

        self.assertIsInstance(content_index["total"], int)
        self.assertIsInstance(content_index["items"], list)

        self.assertIsInstance(taxonomy["totalPages"], int)
        self.assertIsInstance(taxonomy["languages"], list)
        self.assertIsInstance(taxonomy["sections"], list)
        self.assertIsInstance(taxonomy["tags"], list)
        self.assertNotIn("topics", taxonomy)

        self.assertIsInstance(catalog["totalProviders"], int)
        self.assertIsInstance(catalog["totalCourses"], int)
        self.assertIsInstance(catalog["providers"], list)
        self.assertIsInstance(catalog["courses"], list)
        self.assertTrue(catalog["integrationPolicy"]["authorizationRequired"])
        self.assertTrue(catalog["integrationPolicy"]["protectedCourseContentExcluded"])
        self.assertTrue(catalog["integrationPolicy"]["authorizationEvidenceRedacted"])


class AuthorizedCoursesTests(unittest.TestCase):
    def valid_feed(self):
        return {
            "feedVersion": "1.0",
            "provider": {
                "id": "example-center",
                "name": "Example Center",
                "website": "https://example.org",
                "contactEmail": "private@example.org",
            },
            "authorization": {
                "status": "authorized",
                "evidenceUrl": "https://example.org/authorization",
                "license": "Metadata reuse permission",
                "verifiedAt": "2026-07-01",
                "expiresAt": "2027-07-01",
            },
            "courses": [
                {
                    "id": "autism-family-101",
                    "title": "دعم الأسرة في اضطراب طيف التوحد",
                    "summary": "دورة تعريفية للأسر.",
                    "language": "ar",
                    "canonicalUrl": "https://example.org/courses/autism-family-101",
                    "enrollmentUrl": "https://example.org/enroll/autism-family-101",
                    "deliveryMode": "online",
                    "status": "open",
                    "updatedAt": "2026-07-20T10:00:00Z",
                    "price": 25,
                    "currency": "JOD",
                    "rights": {
                        "metadataReuse": True,
                        "contentReuse": False,
                        "attributionText": "المصدر: Example Center",
                    },
                }
            ],
        }

    def publish_feed(self, feed: dict):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        site = root / "site"
        feeds = root / "feeds"
        site.mkdir()
        feeds.mkdir()
        (feeds / "example.json").write_text(
            json.dumps(feed, ensure_ascii=False),
            encoding="utf-8",
        )
        return temp, site, feeds

    def test_publishes_only_authorized_metadata(self):
        temp, site, feeds = self.publish_feed(self.valid_feed())
        with temp:
            result = courses.publish(site, feeds, today=date(2026, 7, 25))
            self.assertEqual(result, {"version": 201, "providers": 1, "courses": 1})
            payload = json.loads((site / "api" / "v1" / "courses.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["totalCourses"], 1)
            self.assertNotIn("contactEmail", payload["providers"][0])
            self.assertNotIn("evidenceUrl", payload["providers"][0]["authorization"])
            self.assertNotIn("evidenceUrl", payload["courses"][0]["authorization"])
            self.assertTrue(payload["providers"][0]["authorization"]["evidenceVerified"])
            self.assertTrue(payload["integrationPolicy"]["authorizationEvidenceRedacted"])
            self.assertEqual(payload["courses"][0]["currency"], "JOD")
            self.assertFalse(payload["courses"][0]["rights"]["contentReuse"])

    def test_rejects_expired_authorization(self):
        feed = self.valid_feed()
        feed["authorization"]["expiresAt"] = "2026-07-24"
        temp, site, feeds = self.publish_feed(feed)
        with temp, self.assertRaisesRegex(ValueError, "authorization.expired"):
            courses.publish(site, feeds, today=date(2026, 7, 25))

    def test_rejects_missing_attribution_nonfinite_price_and_naive_datetime(self):
        cases = [
            (
                "missing attribution",
                lambda feed: feed["courses"][0]["rights"].pop("attributionText"),
                "attribution_required",
            ),
            (
                "nonfinite price",
                lambda feed: feed["courses"][0].__setitem__("price", float("inf")),
                "price_invalid",
            ),
            (
                "naive datetime",
                lambda feed: feed["courses"][0].__setitem__("updatedAt", "2026-07-20T10:00:00"),
                "timezone_required",
            ),
        ]
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                feed = self.valid_feed()
                mutate(feed)
                temp, site, feeds = self.publish_feed(feed)
                with temp, self.assertRaisesRegex(ValueError, expected):
                    courses.publish(site, feeds, today=date(2026, 7, 25))


if __name__ == "__main__":
    unittest.main()
