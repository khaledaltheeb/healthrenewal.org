from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

CATALOG_CONTRACT = 100
EXPECTED_TOOLS = 100
EXPECTED_CATEGORIES = 10
EXPECTED_PATHS = 10
EXPECTED_INDEXABLE_PAGES = 112
LEGACY_PATH_ALIASES: dict[str, str] = {
    "stress-basics-7-days": "stress-regulation-7-days",
    "family-listening-5-days": "family-parenting-7-days",
    "grief-support-7-days": "change-resilience-7-days",
    "caregiver-boundaries-7-days": "caregiver-wellbeing-7-days",
}
PROHIBITED = re.compile(
    r"fetch\(|XMLHttpRequest|navigator\.sendBeacon|تشخيصك|يعالج نهائيًا|بديل عن الطبيب",
    re.IGNORECASE,
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add_error(errors: list[dict[str, object]], check: str, **details: object) -> None:
    errors.append({"check": check, **details})


def verify(site: Path) -> dict[str, object]:
    errors: list[dict[str, object]] = []
    api_path = site / "api/daily-tools-v24.json"
    if not api_path.is_file():
        raise SystemExit(f"Missing daily-tools report: {api_path}")
    daily = json.loads(read(api_path))

    expected = {
        "catalog_contract": CATALOG_CONTRACT,
        "tools": EXPECTED_TOOLS,
        "categories": EXPECTED_CATEGORIES,
        "paths": EXPECTED_PATHS,
        "pages": EXPECTED_INDEXABLE_PAGES,
        "local_only": True,
        "search_and_filters": True,
        "per_tool_sources": True,
        "homepage_linked": True,
    }
    for key, value in expected.items():
        if daily.get(key) != value:
            add_error(errors, f"report.{key}", expected=value, actual=daily.get(key))

    tool_pages = list((site / "daily-tools").rglob("index.html"))
    if len(tool_pages) != EXPECTED_TOOLS + 1:
        add_error(errors, "daily_tool_html_pages", expected=EXPECTED_TOOLS + 1, actual=len(tool_pages))

    all_path_pages = list((site / "learning-paths").rglob("index.html"))
    alias_pages: list[Path] = []
    canonical_path_pages: list[Path] = []
    for page in all_path_pages:
        text = read(page)
        if 'data-legacy-path-alias="v100"' in text:
            alias_pages.append(page)
        else:
            canonical_path_pages.append(page)
    if len(canonical_path_pages) != EXPECTED_PATHS + 1:
        add_error(
            errors,
            "canonical_learning_path_html_pages",
            expected=EXPECTED_PATHS + 1,
            actual=len(canonical_path_pages),
        )
    if len(alias_pages) != len(LEGACY_PATH_ALIASES):
        add_error(
            errors,
            "legacy_learning_path_alias_pages",
            expected=len(LEGACY_PATH_ALIASES),
            actual=len(alias_pages),
        )

    found_aliases = {page.parent.name: page for page in alias_pages}
    for old_slug, new_slug in LEGACY_PATH_ALIASES.items():
        page = found_aliases.get(old_slug)
        if page is None:
            add_error(errors, "missing_legacy_path_alias", old_slug=old_slug, new_slug=new_slug)
            continue
        text = read(page)
        expected_path = f"/learning-paths/{new_slug}/"
        expected_canonical = f"https://healthrenewal.org/learning-paths/{new_slug}/"
        for marker in (
            '<meta name="robots" content="noindex,follow">',
            f'content="0;url={expected_path}"',
            f'<link rel="canonical" href="{expected_canonical}">',
            f'href="{expected_path}"',
        ):
            if marker not in text:
                add_error(
                    errors,
                    "invalid_legacy_path_alias",
                    old_slug=old_slug,
                    new_slug=new_slug,
                    missing=marker,
                )

    sitemap_path = site / "sitemap-tools-paths.xml"
    if not sitemap_path.is_file():
        add_error(errors, "missing_tool_path_sitemap", path=str(sitemap_path))
        sitemap_urls = 0
    else:
        sitemap_urls = len(list(ET.parse(sitemap_path).getroot()))
        if sitemap_urls != EXPECTED_INDEXABLE_PAGES:
            add_error(errors, "tool_path_sitemap_urls", expected=EXPECTED_INDEXABLE_PAGES, actual=sitemap_urls)

    master_path = site / "sitemap.xml"
    master_refs = read(master_path).count("sitemap-tools-paths.xml") if master_path.is_file() else 0
    if master_refs != 1:
        add_error(errors, "master_sitemap_reference", expected=1, actual=master_refs)

    index_path = site / "daily-tools/index.html"
    index = read(index_path) if index_path.is_file() else ""
    cards = index.count("<article data-tool-card ")
    if cards != EXPECTED_TOOLS:
        add_error(errors, "tool_cards", expected=EXPECTED_TOOLS, actual=cards)
    for marker in ("data-tool-search", "data-category-select", "100 أداة نفسية وتربوية يومية"):
        if marker not in index:
            add_error(errors, "daily_tools_index_marker", missing=marker)

    homepage_path = site / "index.html"
    homepage = read(homepage_path) if homepage_path.is_file() else ""
    if "100 أداة عربية عملية" not in homepage:
        add_error(errors, "homepage_count_copy", missing="100 أداة عربية عملية")
    homepage_cards = homepage.count("data-daily-tools-v219")
    if homepage_cards != 1:
        add_error(errors, "homepage_tool_card_uniqueness", expected=1, actual=homepage_cards)

    privacy_copy_pages = 0
    prohibited_matches: list[dict[str, str]] = []
    for directory in (site / "daily-tools", site / "learning-paths"):
        for page in directory.rglob("*.html"):
            text = read(page)
            if "لا تُرسل البيانات إلى خادم" in text:
                privacy_copy_pages += 1
            match = PROHIBITED.search(text)
            if match:
                prohibited_matches.append({
                    "page": str(page.relative_to(site)),
                    "match": match.group(0),
                })
    if privacy_copy_pages < EXPECTED_TOOLS:
        add_error(errors, "privacy_copy_coverage", minimum=EXPECTED_TOOLS, actual=privacy_copy_pages)
    if prohibited_matches:
        add_error(errors, "prohibited_network_or_claim_copy", matches=prohibited_matches[:25])

    sleep_path = site / "daily-tools/sleep-wind-down-plan/index.html"
    sleep_page = read(sleep_path) if sleep_path.is_file() else ""
    for marker in ("data-sleep-log", "sleep-log-v49.js", "غير تشخيص", "لا تُرسل البيانات إلى خادم"):
        if marker not in sleep_page:
            add_error(errors, "sleep_log_marker", missing=marker)

    report: dict[str, object] = {
        "status": "passed" if not errors else "failed",
        "contract": "daily-tools-pages-overlay-v100",
        "base_validated_run": os.environ.get("BASE_RUN_ID", ""),
        "base_source_commit": os.environ.get("BASE_SOURCE_COMMIT", ""),
        "overlay_commit": os.environ.get("GITHUB_SHA", ""),
        "tools": daily.get("tools"),
        "categories": daily.get("categories"),
        "paths": daily.get("paths"),
        "indexable_pages": daily.get("pages"),
        "tool_html_pages": len(tool_pages),
        "canonical_learning_path_pages": len(canonical_path_pages),
        "legacy_alias_pages": len(alias_pages),
        "physical_learning_path_pages": len(all_path_pages),
        "tool_cards": cards,
        "sitemap_urls": sitemap_urls,
        "master_sitemap_references": master_refs,
        "privacy_copy_pages": privacy_copy_pages,
        "prohibited_matches": prohibited_matches,
        "legacy_aliases": LEGACY_PATH_ALIASES,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    output = site / "api/daily-tools-overlay-v100.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    report = verify(site)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["errors"]:
        raise SystemExit(f"Daily-tools overlay validation failed with {len(report['errors'])} error(s)")


if __name__ == "__main__":
    main()
