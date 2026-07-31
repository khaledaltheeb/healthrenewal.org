#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

import publish_section_directory_v221 as legacy

VERSION = 322
COMPATIBILITY_ALIAS_ROUTES = {
    "editorial-methodology/",
    "evaluate-mental-health-information/",
}

ADDITIONS: OrderedDict[str, tuple[str, str, str]] = OrderedDict([
    (
        "outside-the-box/",
        (
            "خارج الصندوق",
            "مسارات متقدمة لمعيار الدليل والتفكير المنهجي وتحليل الادعاءات والممارسات.",
            "المصادر",
        ),
    ),
    (
        "specialists-partners/",
        (
            "فريقنا وشركاؤنا ذوو الاختصاص",
            "تعريف الفريق وسياسة التحقق المهني ومسار الانضمام والتعاون دون ادعاء شراكات غير موثقة.",
            "المؤسسات",
        ),
    ),
    (
        "platform/",
        (
            "دليل المنصة",
            "تعريف بنية المنصة وغرضها وسياسات النشر والتوسع والحوكمة.",
            "الحوكمة",
        ),
    ),
    (
        "copyright/",
        (
            "حقوق النشر والاستخدام",
            "سياسة حقوق المحتوى والاقتباس والإسناد والاستخدام المسموح والبلاغات.",
            "الحوكمة",
        ),
    ),
])

FEATURED = (
    "start-here/",
    "encyclopedia/",
    "special-needs/",
    "care-guides/",
    "comparisons/",
    "library/",
    "magazine/",
    "daily-tools/",
    "learning-paths/",
    "provider-assessment-demo/",
    "specialists-partners/",
    "outside-the-box/",
)

REQUIRED_DIRECTORY_ROUTES = {
    "start-here/",
    "encyclopedia/",
    "terms/",
    "hubs/",
    "comparisons/",
    "library/",
    "magazine/",
    "care-guides/",
    "tips/",
    "special-needs/",
    "sectors/",
    "guided-assessment/",
    "assessments/",
    "assessment-lab/",
    "cognitive-tests/",
    "cognitive-lab/",
    "daily-tools/",
    "learning-paths/",
    "provider-assessment-demo/",
    "specialists-partners/",
    "outside-the-box/",
    "trust/",
    "partners/",
    "developers/",
    "api/",
    "platform/",
    "copyright/",
    "en/",
    "es/",
}


def configure_legacy() -> None:
    definitions = OrderedDict(legacy.DEFINITIONS)
    rebuilt: OrderedDict[str, tuple[str, str, str]] = OrderedDict()

    for route, metadata in definitions.items():
        if route in COMPATIBILITY_ALIAS_ROUTES:
            continue
        rebuilt[route] = metadata
        if route == "magazine/":
            rebuilt["outside-the-box/"] = ADDITIONS["outside-the-box/"]
        if route == "provider-assessment-demo/":
            rebuilt["specialists-partners/"] = ADDITIONS["specialists-partners/"]
        if route == "partners/":
            rebuilt["platform/"] = ADDITIONS["platform/"]
            rebuilt["copyright/"] = ADDITIONS["copyright/"]

    for route, metadata in ADDITIONS.items():
        rebuilt.setdefault(route, metadata)

    legacy.DEFINITIONS = rebuilt
    legacy.FEATURED = FEATURED


def _read_directory(site: Path) -> dict[str, Any]:
    path = site / "api/v1/section-directory.json"
    if not path.is_file():
        raise legacy.SectionDirectoryError("section directory API was not generated")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise legacy.SectionDirectoryError("invalid section directory API payload")
    return payload


def _route_exists(site: Path, route: str) -> bool:
    return (site / route / "index.html").is_file()


def _refresh_home_metrics(site: Path, payload: dict[str, Any]) -> None:
    path = site / "index.html"
    source = path.read_text(encoding="utf-8")
    section_count = int(payload.get("section_count", 0))
    page_count = int(payload.get("html_page_count", 0))
    if section_count <= 0 or page_count <= 0:
        raise legacy.SectionDirectoryError("section directory counts are invalid")

    import re

    source, sections_changed = re.subn(
        r'(<strong\b[^>]*data-surface-section-count[^>]*>).*?(</strong>)',
        rf"\g<1>{section_count:,}\g<2>",
        source,
        count=1,
        flags=re.S,
    )
    source, pages_changed = re.subn(
        r'(<strong\b[^>]*data-surface-page-count[^>]*>).*?(</strong>)',
        rf"\g<1>{page_count:,}+\g<2>",
        source,
        count=1,
        flags=re.S,
    )
    if sections_changed != 1 or pages_changed != 1:
        raise legacy.SectionDirectoryError("homepage metric placeholders are missing")
    path.write_text(source, encoding="utf-8")


def publish(site: Path, root: Path) -> dict[str, Any]:
    site = site.resolve()
    configure_legacy()
    report = legacy.publish(site, root)
    payload = _read_directory(site)
    routes = {item.get("route") for item in payload["items"] if isinstance(item, dict)}

    # Compatibility aliases remain in the production artifact so historical
    # links resolve, but they canonicalize to /trust/, carry noindex, and are
    # not independent public sections.
    unexpected_aliases = sorted(COMPATIBILITY_ALIAS_ROUTES & routes)
    if unexpected_aliases:
        raise legacy.SectionDirectoryError(
            f"compatibility aliases must not be public directory items: {unexpected_aliases}"
        )

    # Build pipelines publish some top-level portals after the content catalog.
    # Enforce registration for every independent route already present now, and
    # let the final full-site audit enforce the complete publication surface.
    available_required = {
        route for route in REQUIRED_DIRECTORY_ROUTES if _route_exists(site, route)
    }
    missing_available = sorted(available_required - routes)
    if missing_available:
        raise legacy.SectionDirectoryError(
            f"available public routes missing from directory: {missing_available}"
        )
    deferred = sorted(REQUIRED_DIRECTORY_ROUTES - available_required)
    _refresh_home_metrics(site, payload)

    upgraded = {
        **report,
        "schema_version": VERSION,
        "legacy_schema_version": legacy.VERSION,
        "status": "passed",
        "critical_routes_declared": len(REQUIRED_DIRECTORY_ROUTES),
        "critical_routes_available": len(available_required),
        "critical_routes_registered": len(available_required & routes),
        "deferred_to_final_publication_gate": deferred,
        "featured_on_home": len(FEATURED),
        "specialists_partners_registered": "specialists-partners/" in routes,
        "outside_the_box_registered": "outside-the-box/" in routes,
        "compatibility_alias_routes": sorted(COMPATIBILITY_ALIAS_ROUTES),
        "compatibility_aliases_registered_as_sections": False,
        "homepage_metrics_refreshed": True,
    }
    legacy.write_json(site / "api/section-directory-v322.json", upgraded)
    return upgraded


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    print(json.dumps(publish(site, root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
