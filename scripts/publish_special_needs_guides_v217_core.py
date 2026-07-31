#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html as html_module
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

import publish_special_needs_guides_v209 as shared
import publish_special_needs_guides_v209_compat as batch209
import publish_special_needs_guides_v210 as batch210
import publish_special_needs_guides_v211 as batch211
import publish_special_needs_guides_v212 as batch212
import publish_special_needs_sleep_v336 as sleep336

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org/"
BATCHES: tuple[tuple[int, Callable[[Path], dict[str, Any]], Path], ...] = (
    (209, batch209.publish, ROOT / "content" / "v209" / "special-needs-guides-manifest-ar.json"),
    (210, batch210.publish, ROOT / "content" / "v210" / "special-needs-guides-manifest-ar.json"),
    (211, batch211.publish, ROOT / "content" / "v211" / "special-needs-guides-manifest-ar.json"),
    (212, batch212.publish, ROOT / "content" / "v212" / "special-needs-guides-manifest-ar.json"),
)
TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
FORBIDDEN_RUNTIME = ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "WebSocket(", "eval(", "new Function(")


def read_manifest(path: Path, version: int) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"Missing v{version} guide manifest: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != version:
        raise SystemExit(f"Manifest version mismatch: expected {version}, found {data.get('version')}")
    slugs = data.get("guide_slugs", [])
    if len(slugs) != 5 or len(slugs) != len(set(slugs)):
        raise SystemExit(f"v{version} must declare five unique guide slugs")
    if data.get("status") != "internally-reviewed":
        raise SystemExit(f"v{version} must retain internally-reviewed status")
    return data


def text_words(markup: str) -> int:
    visible = html_module.unescape(TAG_RE.sub(" ", markup))
    return len(WORD_RE.findall(visible))


def validate_page(site: Path, slug: str, expected_title: str) -> dict[str, Any]:
    path = site / "special-needs" / slug / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing generated guide page: {path}")
    source = path.read_text(encoding="utf-8")
    canonical = f"{BASE}/special-needs/{slug}/"
    required = (
        '<html lang="ar" dir="rtl">',
        '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">',
        f'<link rel="canonical" href="{canonical}">',
        '<script type="application/ld+json">',
        "حدود الاستخدام:",
        "مراجعة داخلية",
        "متى نطلب مساعدة متخصصة؟",
        "المصادر والمنهج",
        "المراجعة الخارجية المتخصصة موصى بها",
        "/special-needs/",
        "/trust/",
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise SystemExit(f"{slug}: missing production markers {missing}")
    if source.count("<h1") != 1:
        raise SystemExit(f"{slug}: expected exactly one H1")
    if len(re.findall(r"<h2\b", source)) < 9:
        raise SystemExit(f"{slug}: guide hierarchy is too shallow")
    if expected_title not in source:
        raise SystemExit(f"{slug}: manifest title is not rendered")
    if shared.BANNED.search(source):
        raise SystemExit(f"{slug}: prohibited person-label language remains")
    if any(token in source for token in FORBIDDEN_RUNTIME):
        raise SystemExit(f"{slug}: network or unsafe runtime API detected")
    if source.count('rel="noopener noreferrer"') < 2:
        raise SystemExit(f"{slug}: fewer than two visible source citations")
    words = text_words(source)
    if words < 700:
        raise SystemExit(f"{slug}: rendered page is too thin ({words} words)")
    return {
        "slug": slug,
        "path": path.relative_to(site).as_posix(),
        "canonical": canonical,
        "words": words,
        "h2": len(re.findall(r"<h2\b", source)),
        "citations": source.count('rel="noopener noreferrer"'),
    }


def sitemap_locations(path: Path, child: str) -> tuple[str, list[str]]:
    if not path.is_file():
        raise SystemExit(f"Missing sitemap: {path}")
    root = ET.parse(path).getroot()
    mode = root.tag.rsplit("}", 1)[-1]
    if mode == "urlset":
        nodes = root.findall("{*}url/{*}loc")
    elif mode == "sitemapindex":
        nodes = root.findall("{*}sitemap/{*}loc")
    else:
        raise SystemExit(f"Unsupported sitemap root in {path}: {mode}")
    values = [(node.text or "").strip() for node in nodes if node.text and node.text.strip()]
    if len(values) != len(set(values)):
        raise SystemExit(f"Duplicate {child} entries in {path}")
    return mode, values


def validate_discovery(site: Path, slugs: list[str]) -> dict[str, Any]:
    expected_urls = {f"{BASE}/special-needs/{slug}/" for slug in slugs}
    special_mode, special_urls = sitemap_locations(site / "sitemap-special-needs.xml", "URL")
    if special_mode != "urlset":
        raise SystemExit("sitemap-special-needs.xml must remain a URL set")
    missing_special = sorted(expected_urls - set(special_urls))
    if missing_special:
        raise SystemExit(f"Special-needs sitemap is missing guide URLs: {missing_special}")

    main_mode, main_values = sitemap_locations(site / "sitemap.xml", "discovery")
    if main_mode == "sitemapindex":
        child = f"{BASE}/sitemap-special-needs.xml"
        if main_values.count(child) != 1:
            raise SystemExit("Main sitemap index must reference sitemap-special-needs.xml exactly once")
    elif not expected_urls.issubset(set(main_values)):
        raise SystemExit("Main URL sitemap is missing one or more guide URLs")

    hub_path = site / "special-needs" / "index.html"
    if not hub_path.is_file():
        raise SystemExit("Missing special-needs hub")
    hub = hub_path.read_text(encoding="utf-8")
    for version in (209, 210, 211, 212):
        if f"<!-- special-needs-guides-v{version}:start -->" not in hub:
            raise SystemExit(f"Special-needs hub is missing v{version} guide block")
    missing_links = [slug for slug in slugs if f"/special-needs/{slug}/" not in hub]
    if missing_links:
        raise SystemExit(f"Special-needs hub is missing guide links: {missing_links}")

    return {
        "special_sitemap_mode": special_mode,
        "special_sitemap_urls": len(special_urls),
        "main_sitemap_mode": main_mode,
        "hub_linked_guides": len(slugs),
    }


def publish(site: Path) -> dict[str, Any]:
    manifests: dict[int, dict[str, Any]] = {}
    all_slugs: list[str] = []
    titles: dict[str, str] = {}
    batch_reports: list[dict[str, Any]] = []

    for version, publisher, manifest_path in BATCHES:
        manifest = read_manifest(manifest_path, version)
        manifests[version] = manifest
        for slug in manifest["guide_slugs"]:
            guide_path = manifest_path.parent / "special-needs-guides" / f"{slug}.json"
            guide = json.loads(guide_path.read_text(encoding="utf-8"))
            titles[slug] = guide["title"]
            all_slugs.append(slug)
        report = publisher(site)
        if report.get("guide_count") != 5 or report.get("generated_page_count") != 5:
            raise SystemExit(f"v{version} publisher did not generate five guides: {report}")
        if report.get("review_status") != "internally-reviewed":
            raise SystemExit(f"v{version} publisher changed the honest review status")
        report["status"] = "production-integrated"
        report["production_contract"] = 217
        report_path = site / "api" / f"special-needs-guides-v{version}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        batch_reports.append(report)

    if len(all_slugs) != 20 or len(all_slugs) != len(set(all_slugs)):
        raise SystemExit("The four batches must produce twenty unique guide routes")

    pages = [validate_page(site, slug, titles[slug]) for slug in all_slugs]
    discovery = validate_discovery(site, all_slugs)
    sleep_report = sleep336.publish(site)
    if sleep_report.get("version") != 336 or sleep_report.get("status") != "passed":
        raise SystemExit(f"Sleep support production integration failed: {sleep_report}")
    if not all(
        sleep_report.get(key) is True
        for key in (
            "medication_boundary_visible",
            "sleep_apnoea_escalation_visible",
            "two_week_sleep_log_visible",
            "hub_linked",
            "sitemap_registered",
        )
    ):
        raise SystemExit("Sleep support safety or discovery contract failed")

    report = {
        "version": 217,
        "status": "passed",
        "production_status": "integrated",
        "batches": [version for version, _, _ in BATCHES],
        "batch_count": len(BATCHES),
        "guide_count": len(all_slugs),
        "guide_slugs": all_slugs,
        "generated_pages": [page["path"] for page in pages],
        "minimum_rendered_words": min(page["words"] for page in pages),
        "minimum_h2": min(page["h2"] for page in pages),
        "minimum_citations": min(page["citations"] for page in pages),
        "review_status": "internally-reviewed",
        "external_review_completed": False,
        "professional_limits_visible": True,
        "source_citations_visible": True,
        "inclusive_language_gate": True,
        "unsafe_runtime_detected": False,
        "sleep_support": sleep_report,
        **discovery,
        "batch_reports": [
            {
                "version": item["version"],
                "status": item["status"],
                "guide_count": item["guide_count"],
                "minimum_source_words": item["minimum_source_words"],
                "source_count": item["source_count"],
            }
            for item in batch_reports
        ],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-guides-v217.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
