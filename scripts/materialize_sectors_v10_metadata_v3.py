#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import materialize_sectors_v10_compat_v2 as compat

base = compat.base
_ORIGINAL_RENDER_PAGE = base.render_page


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _internal_href(value: Any) -> str | None:
    href = str(value or "").strip()
    if not href.startswith("/") or href.startswith("//"):
        return None
    return href


def _schema_types(payload: dict[str, Any]) -> str | list[str]:
    values = payload.get("schema_types")
    if not isinstance(values, list):
        return "Article"
    allowed = [
        str(value).strip()
        for value in values
        if str(value).strip() in {"Article", "MedicalWebPage", "CollectionPage", "WebPage"}
    ]
    return allowed or "Article"


def normalize_governance(payload: dict[str, Any]) -> None:
    compat.normalize_payload(payload)
    boundary = str(payload.get("professional_boundary") or "").strip()
    if boundary and not str(payload.get("disclaimer") or "").strip():
        payload["disclaimer"] = boundary


def _replace_description(page: str, description: str) -> str:
    if not description:
        return page
    escaped = _esc(description[:300])
    page = page.replace(
        page[page.index('<meta name="description"'):page.index('>', page.index('<meta name="description"')) + 1],
        f'<meta name="description" content="{escaped}">',
        1,
    )
    for prop in ("og:description", "twitter:description"):
        marker = f'<meta property="{prop}"' if prop.startswith("og:") else f'<meta name="{prop}"'
        if marker in page:
            start = page.index(marker)
            end = page.index('>', start) + 1
            page = page[:start] + (
                f'<meta property="{prop}" content="{escaped}">' if prop.startswith("og:")
                else f'<meta name="{prop}" content="{escaped}">'
            ) + page[end:]
    return page


def _replace_schema(page: str, item: base.PublicationItem) -> str:
    payload = item.payload
    canonical = f"{base.BASE_URL}/{item.route}"
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": _schema_types(payload),
                "@id": canonical + "#content",
                "url": canonical,
                "headline": str(payload["title"]),
                "name": str(payload["title"]),
                "description": str(payload.get("description") or payload["subtitle"])[:300],
                "inLanguage": "ar",
                "dateModified": str(payload.get("reviewed_at") or "2026-08-04"),
                "datePublished": str(payload.get("published_at") or payload.get("reviewed_at") or "2026-08-04"),
                "isAccessibleForFree": True,
                "author": {"@type": "Organization", "name": "منصة روافد"},
                "publisher": {"@type": "Organization", "name": "منصة روافد", "url": base.BASE_URL + "/"},
                "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": base.BASE_URL + "/"},
                    {"@type": "ListItem", "position": 2, "name": "الأدلة المبنية على المصادر", "item": base.BASE_URL + "/evidence-guides/"},
                    {"@type": "ListItem", "position": 3, "name": str(payload["title"]), "item": canonical},
                ],
            },
        ],
    }
    encoded = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    start_marker = '<script type="application/ld+json">'
    start = page.index(start_marker)
    end = page.index("</script>", start) + len("</script>")
    return page[:start] + start_marker + encoded + "</script>" + page[end:]


def _inject_questions(page: str, payload: dict[str, Any]) -> str:
    cursor = 0
    marker = '</article>\n<aside class="avoid">'
    for article in payload.get("articles") or []:
        questions = article.get("questions") if isinstance(article, dict) else None
        if not isinstance(questions, list) or not questions:
            continue
        position = page.find(marker, cursor)
        if position < 0:
            break
        block = (
            '</article>\n<article class="panel questions"><h3>أسئلة عملية للتحضير والمتابعة</h3>'
            + base._list_items(questions)
            + '</article>\n<aside class="avoid">'
        )
        page = page[:position] + block + page[position + len(marker):]
        cursor = position + len(block)
    return page


def _governance_section(payload: dict[str, Any]) -> str:
    log = payload.get("source_log")
    if not isinstance(log, dict):
        return ""
    method = str(log.get("method") or "").strip()
    limitations = str(log.get("limitations") or "").strip()
    claims = log.get("claims_checked")
    claims_html = base._list_items(claims) if isinstance(claims, list) and claims else ""
    return (
        '<section class="sources" id="source-log"><h2>سجل المنهج والتحقق</h2>'
        + (f'<p><strong>المنهج:</strong> {_esc(method)}</p>' if method else "")
        + (f'<h3>الادعاءات التي جرى فحصها</h3>{claims_html}' if claims_html else "")
        + (f'<p><strong>القيود:</strong> {_esc(limitations)}</p>' if limitations else "")
        + '</section>'
    )


def _internal_links_section(payload: dict[str, Any]) -> str:
    links = [_internal_href(value) for value in payload.get("internal_links") or []]
    links = [value for value in links if value]
    if not links:
        return ""
    items = "".join(f'<li><a href="{_esc(href)}">{_esc(href)}</a></li>' for href in links)
    return f'<section class="sources" id="related"><h2>روابط داخلية ذات صلة</h2><ul>{items}</ul></section>'


def render_page(item: base.PublicationItem) -> str:
    normalize_governance(item.payload)
    page = _ORIGINAL_RENDER_PAGE(item)
    page = _replace_description(page, str(item.payload.get("description") or ""))
    page = _replace_schema(page, item)
    page = _inject_questions(page, item.payload)
    additions = _governance_section(item.payload) + _internal_links_section(item.payload)
    if additions:
        page = page.replace('<section class="sources" id="sources">', additions + '<section class="sources" id="sources">', 1)
    verified_at = str(item.payload.get("verified_at") or "").strip()
    review_status = str(item.payload.get("review_status") or "").strip()
    if verified_at or review_status:
        details = " · ".join(value for value in (f"التحقق: {verified_at}" if verified_at else "", f"حالة المراجعة: {review_status}" if review_status else "") if value)
        page = page.replace("</section>\n<aside class=\"safety\">", f'<p class="meta">{_esc(details)}</p></section>\n<aside class="safety">', 1)
    return page


base.render_page = render_page


def write_publication(repo_root: Path, *, check: bool = False) -> dict[str, Any]:
    return compat.write_publication(repo_root, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize sectors-v10 with governed metadata and practical sections.")
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = write_publication(args.repo_root.resolve(), check=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
