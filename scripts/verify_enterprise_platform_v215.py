from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site/"


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    homepage = SITE / "index.html"
    developers = SITE / "developers" / "index.html"
    if not homepage.is_file() or not developers.is_file():
        raise SystemExit("Homepage or developers page is missing")

    home = homepage.read_text(encoding="utf-8")
    dev = developers.read_text(encoding="utf-8")
    required_home = [
        'assets/logo-mark-v215.svg',
        'assets/logo-card-v215.svg',
        'rel="icon"',
        'property="og:image"',
        'name="twitter:image"',
        'href="developers/"',
        'application/ld+json',
        'منصة الصحة النفسية وذوي الاحتياجات الخاصة',
    ]
    missing_home = [item for item in required_home if item not in home]
    if missing_home:
        raise SystemExit(f"Homepage institutional markers missing: {missing_home}")
    if home.count('<h1>') != 1:
        raise SystemExit(f"Homepage H1 count is {home.count('<h1>')}")
    forbidden_public_planning = [
        "خطة نمو قابلة للقياس",
        "الأهداف الدنيا للمحتوى",
        "هدف توسع",
        "العدد الحالي يثبت",
        "ما سيتم إنجازه",
        "قيد الإعداد",
    ]
    found = [item for item in forbidden_public_planning if item in home]
    if found:
        raise SystemExit(f"Internal planning language leaked to homepage: {found}")

    required_dev = [
        '<html lang="ar" dir="rtl">',
        '<h1>',
        '/api/v1/catalog.json',
        '/api/v1/courses.json',
        '/api/v1/course-import.schema.json',
        '/api/v1/openapi.json',
        'written_permission_verified' if False else 'الإذن الكتابي',
    ]
    missing_dev = [item for item in required_dev if item not in dev]
    if missing_dev:
        raise SystemExit(f"Developers page markers missing: {missing_dev}")
    if dev.count('<h1>') != 1 or len(re.findall(r'<h2\b', dev)) < 2:
        raise SystemExit("Developers page heading hierarchy is incomplete")

    catalog = load_json(SITE / "api" / "v1" / "catalog.json")
    courses = load_json(SITE / "api" / "v1" / "courses.json")
    schema = load_json(SITE / "api" / "v1" / "course-import.schema.json")
    openapi = load_json(SITE / "api" / "v1" / "openapi.json")
    report = load_json(SITE / "api" / "enterprise-platform-v215.json")

    if catalog.get("api_version") != "v1" or catalog.get("page_count", 0) < 100:
        raise SystemExit(f"Catalog is incomplete: {catalog}")
    if len(catalog.get("core_sections", [])) < 7 or len(catalog.get("endpoints", {})) != 4:
        raise SystemExit("Catalog core sections or endpoints are incomplete")
    if courses.get("policy", {}).get("allowed_rights_status") != ["written_permission_verified"]:
        raise SystemExit("Course rights policy is not strict")
    for item in courses.get("items", []):
        if item.get("rights_status") != "written_permission_verified":
            raise SystemExit(f"Unauthorized course in API: {item.get('id')}")
        if not item.get("permission_reference") or not item.get("source_url"):
            raise SystemExit(f"Course permission evidence missing: {item.get('id')}")
    if schema.get("properties", {}).get("rights_status", {}).get("const") != "written_permission_verified":
        raise SystemExit("Course import schema does not enforce written permission")
    if openapi.get("openapi") != "3.1.0" or len(openapi.get("paths", {})) != 4:
        raise SystemExit("OpenAPI contract is incomplete")
    if report.get("course_rights_gate") != "written_permission_verified" or not report.get("developers_page"):
        raise SystemExit("Enterprise platform report is incomplete")

    sitemap = SITE / "sitemap-developers.xml"
    index = SITE / "sitemap.xml"
    if not sitemap.is_file() or not index.is_file():
        raise SystemExit("Developers sitemap integration is missing")
    urls = [(node.text or "").strip() for node in ET.parse(sitemap).getroot().findall("{*}url/{*}loc")]
    if urls != [f"{BASE}developers/"]:
        raise SystemExit(f"Unexpected developers sitemap URLs: {urls}")
    sitemap_refs = [(node.text or "").strip() for node in ET.parse(index).getroot().findall("{*}sitemap/{*}loc")]
    if sitemap_refs.count(f"{BASE}sitemap-developers.xml") != 1:
        raise SystemExit("Developers sitemap must appear exactly once in sitemap index")

    for asset in ("logo-mark-v215.svg", "logo-card-v215.svg"):
        text = (SITE / "assets" / asset).read_text(encoding="utf-8")
        if "<title" not in text or "<desc" not in text:
            raise SystemExit(f"Logo asset lacks accessible title/description: {asset}")

    print(json.dumps({
        "status": "passed",
        "pages": catalog["page_count"],
        "api_endpoints": len(openapi["paths"]),
        "courses": courses["course_count"],
        "logo_assets": 2,
        "planning_leaks": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
