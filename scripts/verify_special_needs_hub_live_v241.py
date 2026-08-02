#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

VERSION = 241
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
PATHWAY_ANCHORS = (
    "pathway-communication",
    "pathway-inclusive-learning",
    "pathway-daily-skills",
    "pathway-sensory-regulation",
    "pathway-family-care",
    "pathway-safeguarding",
    "pathway-sensory-mobility-access",
    "pathway-adulthood",
)
SCHEMA_TYPES = (
    '"@type": "Organization"',
    '"@type": "WebSite"',
    '"@type": "CollectionPage"',
    '"@type": "BreadcrumbList"',
    '"@type": "ItemList"',
    '"@type": "FAQPage"',
)
LOCAL_SOURCE_MARKERS = (
    "jordan-launches-national-framework-inclusion-and-diversity-education-unesco",
    "jordans-education-strategic-plan-2026-2030",
    "unicef.org/jordan/education",
)


def fail(message: str, detail: Any | None = None) -> None:
    raise AssertionError(message if detail is None else f"{message}: {detail}")


def read(path: Path) -> str:
    if not path.is_file():
        fail("Missing live evidence file", path.as_posix())
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(read(path))
    except json.JSONDecodeError as exc:
        fail("Invalid JSON evidence", {"path": path.as_posix(), "error": str(exc)})
    if not isinstance(data, dict):
        fail("JSON evidence root must be an object", path.as_posix())
    return data


def sitemap_locations(path: Path) -> list[str]:
    try:
        root = ET.fromstring(read(path))
    except ET.ParseError as exc:
        fail("Malformed sitemap", {"path": path.as_posix(), "error": str(exc)})
    if root.tag.rsplit("}", 1)[-1] != "urlset":
        fail("Special-needs sitemap must be a urlset")
    locations = [
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if node.text and node.text.strip()
    ]
    if len(locations) != len(set(locations)):
        fail("Special-needs sitemap contains duplicate URLs")
    return locations


def verify(root: Path, expected_sha: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        fail("Evidence directory does not exist", root.as_posix())

    deployment = read_json(root / "deployment.json")
    deployed_sha = deployment.get("commit")
    if deployment.get("schema_version") not in {29, 30}:
        fail("Unexpected deployment schema", deployment)
    if not isinstance(deployed_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", deployed_sha):
        fail("Deployment SHA must be a full lowercase SHA", deployed_sha)
    if expected_sha and deployed_sha != expected_sha:
        fail("Deployment SHA mismatch", {"deployed": deployed_sha, "expected": expected_sha})

    report = read_json(root / "api" / "special-needs-guides-v221.json")
    required_report = {
        "version": 221,
        "status": "passed",
        "production_status": "integrated",
        "guide_count": 25,
        "batch_count": 5,
        "hub_contract": 235,
        "hub_release": 241,
        "external_review_completed": False,
    }
    for key, expected in required_report.items():
        if report.get(key) != expected:
            fail("Special-needs report contract mismatch", {"key": key, "found": report.get(key), "expected": expected})
    hub_report = report.get("hub")
    if not isinstance(hub_report, dict):
        fail("Special-needs hub report is missing")
    for key, expected in {
        "status": "production-integrated",
        "pathway_count": 8,
        "faq_count": 8,
        "source_count": 10,
        "jordan_source_count": 3,
        "jordan_context_section": True,
        "asha_aac_source_updated": True,
    }.items():
        if hub_report.get(key) != expected:
            fail("Special-needs hub sub-contract mismatch", {"key": key, "found": hub_report.get(key), "expected": expected})

    slugs = report.get("guide_slugs")
    if not isinstance(slugs, list) or len(slugs) != 25 or len(slugs) != len(set(slugs)):
        fail("Special-needs report must list twenty-five unique guide slugs", slugs)

    source = read(root / "special-needs" / "index.html")
    if len(re.findall(r"<h1\b", source, flags=re.I)) != 1:
        fail("Live hub must contain exactly one H1")
    if "noindex" in source.lower():
        fail("Live hub must remain indexable")
    if BANNED.search(source):
        fail("Live hub contains prohibited person-label language")
    required_html = (
        '<html lang="ar" dir="rtl">',
        '<meta name="description"',
        '<meta name="keywords"',
        '<meta name="robots"',
        '<meta name="googlebot"',
        '<meta name="bingbot"',
        f'<link rel="canonical" href="{BASE}/special-needs/">',
        'hreflang="ar"',
        'hreflang="x-default"',
        'property="og:image"',
        'name="twitter:image"',
        'application/ld+json',
        '<strong>10</strong><span>مراجع مؤسسية أصلية</span>',
        'data-special-needs-jordan-sources-v241',
        'data-special-needs-jordan-context-v241',
        'من مبدأ الإدماج إلى طلب مكتوب قابل للمتابعة',
        'لا تمثل هذه الصفحة تفسيرًا قانونيًا',
        'Practice-Portal/Professional-Issues/Augmentative-and-Alternative-Communication',
        'مصفوفة قرار سريعة',
        'معايير جودة الخطة أو الخدمة',
        'المنهجية التحريرية وحدود الاستخدام',
        'الطوارئ المحلية',
        'prefers-reduced-motion',
        'prefers-contrast:more',
        '@media print',
    )
    missing_html = [marker for marker in required_html if marker not in source]
    if missing_html:
        fail("Live hub is missing institutional markers", missing_html)
    missing_schema = [marker for marker in SCHEMA_TYPES if marker not in source]
    if missing_schema:
        fail("Live hub is missing structured-data types", missing_schema)
    missing_sources = [marker for marker in LOCAL_SOURCE_MARKERS if marker not in source]
    if missing_sources:
        fail("Live hub is missing Jordan source links", missing_sources)
    if source.count("data-special-needs-jordan-sources-v241") != 3:
        fail("Jordan source marker count must equal three")
    if source.count("data-special-needs-jordan-context-v241") != 1:
        fail("Jordan context section marker must occur exactly once")
    if "www.asha.org/public/speech/disorders/aac/" in source:
        fail("Legacy ASHA public AAC URL remains in live hub")
    for unsafe in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "eval(", "new Function("):
        if unsafe in source:
            fail("Unsafe or network runtime detected", unsafe)

    for anchor in PATHWAY_ANCHORS:
        if source.count(f'id="{anchor}"') != 1 or f'href="#{anchor}"' not in source:
            fail("Pathway anchor/link contract failed", anchor)

    missing_links: list[str] = []
    duplicate_links: list[str] = []
    for slug in slugs:
        route = f"{BASE_PATH}special-needs/{slug}/"
        count = source.count(route)
        if count == 0:
            missing_links.append(slug)
        elif count != 1:
            duplicate_links.append(slug)
    if missing_links or duplicate_links:
        fail("Guide link uniqueness contract failed", {"missing": missing_links, "duplicate": duplicate_links})

    locations = sitemap_locations(root / "sitemap-special-needs.xml")
    expected_urls = {f"{BASE}/special-needs/"} | {f"{BASE}/special-needs/{slug}/" for slug in slugs}
    missing_urls = sorted(expected_urls - set(locations))
    if missing_urls:
        fail("Special-needs sitemap is missing hub or guide URLs", missing_urls)
    for url in expected_urls:
        if locations.count(url) != 1:
            fail("Special-needs sitemap URL must occur exactly once", url)

    robots = read(root / "robots.txt")
    child = f"Sitemap: {BASE}/sitemap-special-needs.xml"
    if robots.count(child) != 1:
        fail("robots.txt must register the special-needs sitemap exactly once")

    evidence = {
        "version": VERSION,
        "status": "passed",
        "deployment_commit": deployed_sha,
        "hub_release": report["hub_release"],
        "guide_count": len(slugs),
        "pathway_count": len(PATHWAY_ANCHORS),
        "faq_count": hub_report["faq_count"],
        "source_count": hub_report["source_count"],
        "jordan_source_count": hub_report["jordan_source_count"],
        "jordan_context_section": hub_report["jordan_context_section"],
        "guide_links": len(slugs),
        "sitemap_required_urls": len(expected_urls),
        "sitemap_total_urls": len(locations),
        "robots_child_sitemap_count": robots.count(child),
        "structured_data_types": list(SCHEMA_TYPES),
        "indexable": True,
        "javascript_required": False,
        "external_review_completed": report["external_review_completed"],
    }
    output = root / "api" / "special-needs-hub-live-v241.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-sha")
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.expected_sha), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
