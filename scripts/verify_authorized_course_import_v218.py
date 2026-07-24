#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site"


def load(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Missing required JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return value


def locations(path: Path) -> tuple[str, list[str]]:
    root = ET.parse(path).getroot()
    mode = root.tag.rsplit("}", 1)[-1]
    if mode == "urlset":
        nodes = root.findall("{*}url/{*}loc")
    elif mode == "sitemapindex":
        nodes = root.findall("{*}sitemap/{*}loc")
    else:
        raise SystemExit(f"Unsupported sitemap root: {mode}")
    values = [(node.text or "").strip() for node in nodes if node.text and node.text.strip()]
    if len(values) != len(set(values)):
        raise SystemExit(f"Duplicate sitemap locations in {path}")
    return mode, values


def main() -> int:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site output: {SITE}")
    registry_schema = load(SITE / "api" / "v1" / "course-provider-registry.schema.json")
    course_schema = load(SITE / "api" / "v1" / "courses.schema.json")
    catalog = load(SITE / "api" / "v1" / "courses.json")
    report = load(SITE / "api" / "course-import-v218.json")
    platform = load(SITE / "api" / "v1" / "platform.json")
    openapi = load(SITE / "api" / "v1" / "openapi.json")

    assert registry_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    provider = registry_schema["properties"]["providers"]["items"]
    assert provider["properties"]["rights"]["properties"]["metadataReuse"]["const"] is True
    assert provider["properties"]["rights"]["properties"]["contentReuse"]["const"] is False
    assert course_schema["properties"]["authorization"]["properties"]["status"]["const"] == "authorized"
    assert course_schema["properties"]["courses"]["items"]["properties"]["rights"]["properties"]["metadataReuse"]["const"] is True

    assert report.get("version") == 218 and report.get("status") == "passed", report
    assert report.get("networkApprovalRequired") is True, report
    assert report.get("metadataOnly") is True and report.get("contentReuse") is False, report
    assert report.get("remoteFetchEnabled") is False, report
    assert catalog.get("providerCount") == report.get("authorizedProviders"), (catalog, report)
    assert catalog.get("courseCount") == report.get("courseCount"), (catalog, report)
    assert catalog.get("policy") == "permission_required", catalog
    assert catalog.get("contentReuse") is False, catalog
    courses = catalog.get("courses")
    assert isinstance(courses, list), catalog
    for course in courses:
        assert course.get("globalId") and course.get("providerId") and course.get("id"), course
        assert course.get("canonicalUrl", "").startswith("https://"), course
        assert course.get("enrollmentUrl", "").startswith("https://"), course
        assert "content" not in course and "lessons" not in course and "video" not in course, course

    paths = openapi.get("paths", {})
    for endpoint in (
        "/api/v1/courses.json",
        "/api/v1/courses.schema.json",
        "/api/v1/course-provider-registry.schema.json",
    ):
        assert endpoint in paths, (endpoint, paths.keys())
    endpoints = platform.get("endpoints", {})
    assert endpoints.get("courseCatalog", "").endswith("/api/v1/courses.json"), endpoints
    assert endpoints.get("courseProviderRegistrySchema", "").endswith("/api/v1/course-provider-registry.schema.json"), endpoints
    assert platform.get("integrationPolicy", {}).get("externalCourseImport") == "permission_required"

    page = SITE / "courses" / "index.html"
    source = page.read_text(encoding="utf-8")
    for marker in (
        '<html lang="ar" dir="rtl">',
        '<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/courses/">',
        '<script type="application/ld+json">',
        "لا ننسخ محتوى الدورة",
        "لا يعني الإدراج اعتماد المنصة",
        "/pterminology-site/api/",
        "/pterminology-site/trust/",
    ):
        assert marker in source, marker
    assert source.count("<h1") == 1
    assert len(re.findall(r"<h2\b", source)) >= 2
    assert "fetch(" not in source and "XMLHttpRequest" not in source and "sendBeacon" not in source

    child_mode, child_urls = locations(SITE / "sitemap-courses.xml")
    assert child_mode == "urlset" and child_urls == [f"{BASE}/courses/"], (child_mode, child_urls)
    main_mode, main_urls = locations(SITE / "sitemap.xml")
    if main_mode == "sitemapindex":
        assert main_urls.count(f"{BASE}/sitemap-courses.xml") == 1, main_urls
    else:
        assert main_urls.count(f"{BASE}/courses/") == 1, main_urls

    result = {
        "version": 218,
        "status": "passed",
        "registeredProviders": report.get("registeredProviders"),
        "authorizedProviders": report.get("authorizedProviders"),
        "courses": len(courses),
        "metadataOnly": True,
        "networkDefault": "disabled",
        "sitemapMode": main_mode,
        "apiEndpoints": 3,
    }
    (SITE / "api" / "course-import-verification-v218.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
