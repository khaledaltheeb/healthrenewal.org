#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

VERSION = 236
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
BATCHES = (209, 210, 211, 212, 214)
V214_SLUGS = (
    "assessment-homework-accommodations-plan",
    "visual-schedules-transitions-home-school-plan",
    "inclusive-play-peer-friendship-plan",
    "siblings-family-balance-support-plan",
    "accessible-family-emergency-preparedness-plan",
)


def fail(message: str, detail: Any | None = None) -> None:
    if detail is None:
        raise AssertionError(message)
    raise AssertionError(f"{message}: {detail}")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail("Missing JSON file", path.as_posix())
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("JSON root must be an object", path.as_posix())
    return data


def sitemap_locations(path: Path) -> list[str]:
    if not path.is_file():
        fail("Missing special-needs sitemap", path.as_posix())
    root = ET.parse(path).getroot()
    mode = root.tag.rsplit("}", 1)[-1]
    if mode != "urlset":
        fail("Special-needs sitemap must be a urlset", mode)
    values = [
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if node.text and node.text.strip()
    ]
    if len(values) != len(set(values)):
        fail("Duplicate URLs remain in special-needs sitemap")
    return values


def validate_page(path: Path, slug: str) -> None:
    if not path.is_file():
        fail("Missing guide page", path.as_posix())
    source = path.read_text(encoding="utf-8")
    canonical = f"{BASE}/special-needs/{slug}/"
    if len(re.findall(r"<h1\b", source, flags=re.I)) != 1:
        fail("Guide page must contain exactly one H1", slug)
    if canonical not in source:
        fail("Guide canonical URL is missing", slug)
    if "noindex" in source.lower():
        fail("Published guide page must not be noindex", slug)
    if not re.search(r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*index', source, flags=re.I | re.S):
        fail("Guide robots index contract is missing", slug)


def verify(site: Path, mode: str, expected_sha: str | None = None) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        fail("Site directory does not exist", site.as_posix())

    deployment = read_json(site / "deployment.json")
    if deployment.get("schema_version") not in {29, 30}:
        fail("Unexpected deployment schema", deployment)
    live_sha = deployment.get("commit")
    if not isinstance(live_sha, str) or len(live_sha) != 40:
        fail("Deployment commit must be a full SHA", live_sha)
    if expected_sha and live_sha != expected_sha:
        fail("Deployment SHA does not match expected SHA", {"live": live_sha, "expected": expected_sha})

    report = read_json(site / "api" / "special-needs-guides-v221.json")
    required_report = {
        "version": 221,
        "status": "passed",
        "production_status": "integrated",
        "batch_count": 5,
        "guide_count": 25,
        "production_source_file_count": 25,
        "review_status": "internally-reviewed",
        "external_review_completed": False,
        "external_review": "recommended-not-completed",
    }
    for key, expected in required_report.items():
        if report.get(key) != expected:
            fail("Special-needs report contract mismatch", {"key": key, "found": report.get(key), "expected": expected})
    if report.get("batches") != list(BATCHES):
        fail("Five guide batches are not declared in order", report.get("batches"))

    slugs = report.get("guide_slugs")
    if not isinstance(slugs, list) or len(slugs) != 25 or len(slugs) != len(set(slugs)):
        fail("Report must contain twenty-five unique guide slugs", slugs)
    if not set(V214_SLUGS).issubset(slugs):
        fail("One or more v214 guide slugs are absent", sorted(set(V214_SLUGS) - set(slugs)))

    hub_path = site / "special-needs" / "index.html"
    if not hub_path.is_file():
        fail("Missing special-needs hub", hub_path.as_posix())
    hub = hub_path.read_text(encoding="utf-8")
    if "noindex" in hub.lower() or len(re.findall(r"<h1\b", hub, flags=re.I)) != 1:
        fail("Special-needs hub indexability or H1 contract failed")
    for version in BATCHES:
        for edge in ("start", "end"):
            marker = f"special-needs-guides-v{version}:{edge}"
            if hub.count(marker) != 1:
                fail("Guide batch marker must appear exactly once", marker)

    missing_links: list[str] = []
    duplicate_links: list[str] = []
    for slug in slugs:
        route = f"{BASE_PATH}special-needs/{slug}/"
        count = hub.count(route)
        if count == 0:
            missing_links.append(slug)
        elif count != 1:
            duplicate_links.append(slug)
    if missing_links:
        fail("Hub is missing guide links", missing_links)
    if duplicate_links:
        fail("Hub contains duplicate guide links", duplicate_links)

    locations = sitemap_locations(site / "sitemap-special-needs.xml")
    expected_urls = {f"{BASE}/special-needs/{slug}/" for slug in slugs}
    missing_urls = sorted(expected_urls - set(locations))
    if missing_urls:
        fail("Special-needs sitemap is missing guide URLs", missing_urls)
    for url in expected_urls:
        if locations.count(url) != 1:
            fail("Guide URL must appear exactly once in sitemap", url)

    page_slugs = slugs if mode == "artifact" else list(V214_SLUGS)
    for slug in page_slugs:
        validate_page(site / "special-needs" / slug / "index.html", slug)

    result = {
        "version": VERSION,
        "status": "passed",
        "mode": mode,
        "deployment_commit": live_sha,
        "guide_count": len(slugs),
        "batch_count": len(BATCHES),
        "hub_links": len(slugs),
        "sitemap_guide_urls": len(expected_urls),
        "sitemap_total_urls": len(locations),
        "v214_pages_verified": len(V214_SLUGS),
        "all_guide_pages_verified": len(page_slugs) if mode == "artifact" else None,
        "review_status": report["review_status"],
        "external_review_completed": report["external_review_completed"],
        "blocked_review_files_published": False,
    }
    evidence = site / "api" / "special-needs-deployment-v236.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("--mode", choices=("artifact", "live"), default="artifact")
    parser.add_argument("--expected-sha")
    args = parser.parse_args()
    print(json.dumps(verify(args.site, args.mode, args.expected_sha), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
