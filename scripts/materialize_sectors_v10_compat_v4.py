#!/usr/bin/env python3
from __future__ import annotations

"""Canonical v4 entrypoint for rich governed sectors-v10 sources.

This adapter preserves the richer source schema while delegating validation,
rendering, editorial-release handling, and publication to the established
v3/v2 stack. It does not create a second publisher.
"""

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import materialize_sectors_v10_metadata_v3 as metadata

compat = metadata.compat
base = metadata.base
PublicationItem = metadata.PublicationItem
PublicationError = metadata.PublicationError

# Historical generated sources used /family/ before the institutional family
# sector was standardized. Keep source payloads intact on disk, while publishing
# the current canonical route and preserving any supplied human-readable label.
LEGACY_ROUTE_MAP = {
    "/family/": "/sectors/family/",
}

# A page headline may be intentionally descriptive while the search-result title
# needs a tighter character budget. Keep explicit, reviewed overrides close to
# the canonical publisher so regeneration cannot restore known title warnings.
SEO_TITLE_OVERRIDES = {
    "clinical-anxiety": "القلق والهلع والوسواس: الفروق وطلب المساعدة",
}


def _canonical_internal_route(value: Any) -> str:
    route = str(value or "").strip()
    return LEGACY_ROUTE_MAP.get(route, route)


def normalize_payload(payload: dict[str, Any]) -> None:
    """Add compatibility fields without deleting richer source fields."""
    articles = payload.get("articles")
    if isinstance(articles, list):
        for article in articles:
            if not isinstance(article, dict):
                continue
            assessment = article.get("assessment_questions")
            if (
                "questions" not in article
                and isinstance(assessment, list)
                and assessment
            ):
                article["questions"] = list(assessment)

    links = payload.get("internal_links")
    if isinstance(links, list):
        normalized_links: list[str] = []
        labels: dict[str, str] = {}
        for entry in links:
            if isinstance(entry, str):
                url = _canonical_internal_route(entry)
                if url:
                    normalized_links.append(url)
                continue
            if not isinstance(entry, dict):
                continue
            url = _canonical_internal_route(entry.get("url"))
            if not url:
                continue
            normalized_links.append(url)
            label = str(entry.get("label") or "").strip()
            if label:
                labels[url] = label
        payload["internal_links"] = normalized_links
        if labels:
            payload["_internal_link_labels"] = labels

    source_log = payload.get("source_log")
    if isinstance(source_log, dict):
        limitations = source_log.get("limitations")
        if isinstance(limitations, list):
            source_log["limitations"] = " ".join(
                str(item).strip()
                for item in limitations
                if str(item).strip()
            )

    metadata.normalize_payload(payload)


def validate_source(path: Path, payload: dict[str, Any]) -> None:
    normalize_payload(payload)
    metadata.validate_source(path, payload)


def _internal_links_section(payload: dict[str, Any]) -> str:
    links = payload.get("internal_links")
    if not isinstance(links, list):
        return ""
    labels = {
        "/mental-health/": "بوابة الصحة النفسية",
        "/daily-tools/medical-visit-preparation/": "التحضير للزيارة الطبية",
        "/assessment-lab/": "مختبر التقييمات النفسية الآمنة",
        "/safety/": "السلامة وطلب المساعدة",
        "/services/": "دليل الخدمات والمسارات",
        "/sectors/family/": "قطاع الأسرة",
        "/encyclopedia/": "الموسوعة",
    }
    custom = payload.get("_internal_link_labels")
    if isinstance(custom, dict):
        labels.update(
            {
                str(url): str(label)
                for url, label in custom.items()
                if str(url).strip() and str(label).strip()
            }
        )

    items: list[str] = []
    seen: set[str] = set()
    for value in links:
        url = _canonical_internal_route(value)
        if (
            not url.startswith("/")
            or url.startswith("//")
            or url in seen
        ):
            continue
        seen.add(url)
        label = labels.get(url, url.strip("/").replace("-", " ") or "رابط داخلي")
        items.append(
            f'<li><a href="{base.esc(url)}">{base.esc(label)}</a></li>'
        )
    if not items:
        return ""
    return (
        '<section class="guide-section related" id="related-links">'
        "<h2>مسارات مرتبطة داخل المنصة</h2><ul>"
        + "".join(items)
        + "</ul></section>"
    )


def _apply_seo_title_override(page: str, payload: dict[str, Any]) -> str:
    key = str(payload.get("key") or "").strip()
    seo_title = SEO_TITLE_OVERRIDES.get(key)
    if not seo_title:
        return page
    rendered_title = f"{seo_title} | منصة روافد"
    start = page.find("<title>")
    end = page.find("</title>", start + len("<title>"))
    if start < 0 or end < 0:
        raise PublicationError(
            f"Rendered governed page for {key or 'unknown source'} is missing <title>."
        )
    return (
        page[: start + len("<title>")]
        + base.esc(rendered_title)
        + page[end:]
    )


def render_page(item: PublicationItem) -> str:
    normalize_payload(item.payload)
    original = compat._internal_links_section
    compat._internal_links_section = _internal_links_section
    try:
        page = metadata.render_page(item)
    finally:
        compat._internal_links_section = original

    page = _apply_seo_title_override(page, item.payload)

    boundary = str(item.payload.get("professional_boundary") or "").strip()
    disclaimer = str(item.payload.get("disclaimer") or "").strip()
    if boundary and boundary != disclaimer and boundary not in page:
        marker = '<aside class="safety"><h2>حدود الاستخدام والسلامة</h2>'
        if marker not in page:
            raise PublicationError(
                "Rendered governed page is missing the safety section required for professional boundaries."
            )
        page = page.replace(
            marker,
            marker + f"<p>{base.esc(boundary)}</p>",
            1,
        )
    return page


@contextmanager
def _patched_base_contract() -> Iterator[None]:
    original_validate = base.validate_source
    original_render = base.render_page
    base.validate_source = validate_source
    base.render_page = render_page
    try:
        yield
    finally:
        base.validate_source = original_validate
        base.render_page = original_render


def write_publication(repo_root: Path, *, check: bool = False) -> dict[str, Any]:
    with _patched_base_contract():
        return metadata.write_publication(repo_root, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize rich governed sectors-v10 sources through the canonical v4 adapter."
    )
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = write_publication(args.repo_root.resolve(), check=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
