#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import materialize_sectors_v10_v1 as base

REVIEW_LEDGER = Path("data/content-reviews/sectors-v10-editorial-release-v2.json")
RELEASED_MANUAL_REVIEW_SOURCES = {
    "aac-home-school-guide.json",
    "inclusive-school-transition.json",
    "mental-health-foundations.json",
}

# Keep the user's prohibited wording out of public content while preserving
# exact legal/institutional names such as the UN Convention on the Rights of
# Persons with Disabilities. Rewriting official titles would reduce accuracy.
base.UNWANTED_TERMS = ("معاقين", "المعاقين")

_ORIGINAL_VALIDATE = base.validate_source
_ORIGINAL_RENDER = base.render_page
_ALLOWED_SCHEMA_TYPES = {
    "Article",
    "CollectionPage",
    "MedicalWebPage",
    "WebPage",
}


def _source_name(source: dict[str, Any]) -> str:
    explicit = str(source.get("name") or "").strip()
    if explicit:
        return explicit
    publisher = str(source.get("publisher") or "").strip()
    title = str(source.get("title") or source.get("label") or "").strip()
    if publisher and title and publisher.casefold() not in title.casefold():
        return f"{publisher} — {title}"
    return title or publisher or str(source.get("id") or "مصدر مرجعي").strip()


def _normalized_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for source in payload.get("sources") or []:
        if isinstance(source, str):
            normalized.append({"name": source, "url": source})
            continue
        if not isinstance(source, dict):
            normalized.append({"name": "", "url": ""})
            continue
        record = dict(source)
        record["name"] = _source_name(source)
        record["url"] = str(
            source.get("url") or source.get("href") or source.get("link") or ""
        ).strip()
        normalized.append(record)
    return normalized


def _stringify_item(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        if {"q", "a"} <= set(value):
            return f"{str(value['q']).strip()} — {str(value['a']).strip()}"
        if "axis" in value:
            label = str(value.get("axis") or "محور").strip()
            details = [
                f"{key}: {str(item).strip()}"
                for key, item in value.items()
                if key != "axis" and str(item).strip()
            ]
            return f"{label} — " + "؛ ".join(details)
        return "؛ ".join(
            f"{str(key).strip()}: {str(item).strip()}"
            for key, item in value.items()
            if str(item).strip()
        )
    return str(value).strip()


def _first_substantive_list(
    article: dict[str, Any], keys: tuple[str, ...]
) -> list[str]:
    for key in keys:
        values = article.get(key)
        if not isinstance(values, list):
            continue
        normalized = [_stringify_item(value) for value in values]
        normalized = [value for value in normalized if value]
        if len(normalized) >= 2:
            return normalized
    return []


def _normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(article)
    title = str(article.get("title") or "هذا المحور").strip()

    if not isinstance(normalized.get("signals"), list) or len(
        normalized.get("signals") or []
    ) < 3:
        signals = _first_substantive_list(
            article,
            (
                "warning_signs",
                "assessment_domains",
                "common_mistakes",
                "overlap_examples",
                "examples",
                "age_context",
                "practical_support",
                "comparison_axes",
                "faq",
            ),
        )
        if len(signals) >= 3:
            normalized["signals"] = signals

    if not isinstance(normalized.get("phrases"), list) or len(
        normalized.get("phrases") or []
    ) < 2:
        normalized["phrases"] = [
            f"لن نحسم «{title}» من علامة واحدة؛ سنراجع السياق والتاريخ والأثر الوظيفي.",
            "سنبدأ بالسلامة والاحتياج العملي، ثم نحدد إن كان التقييم المتخصص مطلوبًا.",
        ]

    return normalized


def normalize_payload(payload: dict[str, Any]) -> None:
    payload["sources"] = _normalized_sources(payload)
    articles = payload.get("articles")
    if isinstance(articles, list):
        payload["articles"] = [
            _normalize_article(article) if isinstance(article, dict) else article
            for article in articles
        ]


def _publication_canonical(payload: dict[str, Any]) -> str:
    key = str(payload.get("key") or "").strip()
    return f"{base.BASE_URL}/{base.OUTPUT_ROOT.as_posix()}/{key}/"


def validate_source(path: Path, payload: dict[str, Any]) -> None:
    normalize_payload(payload)
    _ORIGINAL_VALIDATE(path, payload)
    declared_canonical = str(payload.get("canonical") or "").strip()
    expected_canonical = _publication_canonical(payload)
    if declared_canonical and declared_canonical != expected_canonical:
        raise base.PublicationError(
            f"{path}: canonical mismatch: expected {expected_canonical}, "
            f"got {declared_canonical}"
        )


base.validate_source = validate_source


def _schema_types(payload: dict[str, Any]) -> list[str]:
    requested = payload.get("schema_types")
    if not isinstance(requested, list):
        return ["Article"]
    result: list[str] = []
    for value in requested:
        item = str(value).strip()
        if item in _ALLOWED_SCHEMA_TYPES and item not in result:
            result.append(item)
    return result or ["Article"]


def _review_value(value: Any) -> str:
    normalized = str(value or "").strip()
    labels = {
        "internally-reviewed": "مراجعة تحريرية داخلية",
        "recommended-not-completed": "مراجعة خارجية موصى بها ولم تكتمل",
        "sensitive": "محتوى حساس",
    }
    return labels.get(normalized, normalized)


def _list_html(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{base.esc(value)}</li>" for value in items) + "</ul>"


def _questions_section(payload: dict[str, Any]) -> str:
    blocks: list[str] = []
    for article in payload.get("articles") or []:
        if not isinstance(article, dict):
            continue
        questions = article.get("questions")
        questions_html = _list_html(questions)
        if not questions_html:
            continue
        title = str(article.get("title") or "أسئلة عملية").strip()
        blocks.append(
            f'<article class="panel"><h3>{base.esc(title)}</h3>{questions_html}</article>'
        )
    if not blocks:
        return ""
    return (
        '<section class="guide-section governance" id="practical-questions">'
        "<h2>أسئلة عملية قبل التقييم أو المتابعة</h2>"
        '<div class="guide-grid">'
        + "".join(blocks)
        + "</div></section>"
    )


def _source_governance_section(payload: dict[str, Any]) -> str:
    review_rows: list[str] = []
    review_fields = (
        ("حالة المراجعة", payload.get("review_status")),
        ("المراجعة الخارجية", payload.get("external_review")),
        ("مستوى الحساسية", payload.get("safety_level")),
        ("تاريخ التحقق", payload.get("verified_at")),
        ("موعد المراجعة التالية", payload.get("next_review_due")),
    )
    for label, value in review_fields:
        rendered = _review_value(value)
        if rendered:
            review_rows.append(
                f"<dt>{base.esc(label)}</dt><dd>{base.esc(rendered)}</dd>"
            )

    source_log = payload.get("source_log")
    method = ""
    limitations = ""
    claims_html = ""
    if isinstance(source_log, dict):
        method = str(source_log.get("method") or "").strip()
        limitations = str(source_log.get("limitations") or "").strip()
        claims_html = _list_html(source_log.get("claims_checked"))

    source_records: list[str] = []
    for source in payload.get("sources") or []:
        if not isinstance(source, dict):
            continue
        details = [
            str(source.get("publisher") or "").strip(),
            str(source.get("type") or "").strip(),
            str(source.get("verified_at") or "").strip(),
            str(source.get("use") or "").strip(),
        ]
        details = [detail for detail in details if detail]
        if not details:
            continue
        source_records.append(
            "<li><strong>"
            + base.esc(source.get("name") or "مصدر")
            + "</strong><br>"
            + base.esc(" · ".join(details))
            + "</li>"
        )

    if not (review_rows or method or limitations or claims_html or source_records):
        return ""

    parts = [
        '<section class="guide-section governance" id="governance">',
        "<h2>حالة المراجعة ومنهجية المصادر</h2>",
    ]
    if review_rows:
        parts.append("<dl>" + "".join(review_rows) + "</dl>")
    if method:
        parts.append(f"<h3>منهج الإعداد</h3><p>{base.esc(method)}</p>")
    if claims_html:
        parts.append("<h3>المحاور التي تم التحقق منها</h3>" + claims_html)
    if limitations:
        parts.append(f"<h3>الحدود والسياق</h3><p>{base.esc(limitations)}</p>")
    if source_records:
        parts.append(
            "<h3>سجل المصادر</h3><ul class=\"source-log\">"
            + "".join(source_records)
            + "</ul>"
        )
    parts.append("</section>")
    return "".join(parts)


def _internal_links_section(payload: dict[str, Any]) -> str:
    links = payload.get("internal_links")
    if not isinstance(links, list):
        return ""
    labels = {
        "/mental-health/": "بوابة الصحة النفسية",
        "/daily-tools/medical-visit-preparation/": "التحضير للزيارة الطبية",
        "/safety/": "السلامة وطلب المساعدة",
        "/encyclopedia/": "الموسوعة",
    }
    items: list[str] = []
    for value in links:
        url = str(value).strip()
        if not url.startswith("/") or url.startswith("//"):
            continue
        label = labels.get(url, url.strip("/").replace("-", " ") or "رابط داخلي")
        items.append(f'<li><a href="{base.esc(url)}">{base.esc(label)}</a></li>')
    if not items:
        return ""
    return (
        '<section class="guide-section related" id="related-links">'
        "<h2>مسارات مرتبطة داخل المنصة</h2><ul>"
        + "".join(items)
        + "</ul></section>"
    )


def _enhance_schema(document: str, payload: dict[str, Any]) -> str:
    match = re.search(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        document,
        flags=re.DOTALL,
    )
    if not match:
        return document
    try:
        schema = json.loads(match.group(2))
    except json.JSONDecodeError:
        return document

    description = str(payload.get("description") or payload.get("subtitle") or "").strip()
    graph = schema.get("@graph") if isinstance(schema, dict) else None
    if isinstance(graph, list) and graph and isinstance(graph[0], dict):
        graph[0]["@type"] = _schema_types(payload)
        if description:
            graph[0]["description"] = description[:300]
    encoded = json.dumps(
        schema, ensure_ascii=False, separators=(",", ":")
    ).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return document[: match.start(2)] + encoded + document[match.end(2) :]


def render_page(item: base.PublicationItem) -> str:
    payload = item.payload
    document = _ORIGINAL_RENDER(item)

    description = str(payload.get("description") or payload.get("subtitle") or "").strip()
    if description:
        escaped = base.esc(description[:300])
        document = re.sub(
            r'<meta name="description" content="[^"]*">',
            f'<meta name="description" content="{escaped}">',
            document,
            count=1,
        )
        document = re.sub(
            r'<meta property="og:description" content="[^"]*">',
            f'<meta property="og:description" content="{escaped}">',
            document,
            count=1,
        )
        document = re.sub(
            r'<meta name="twitter:description" content="[^"]*">',
            f'<meta name="twitter:description" content="{escaped}">',
            document,
            count=1,
        )

    document = _enhance_schema(document, payload)

    additions = (
        _questions_section(payload)
        + _source_governance_section(payload)
        + _internal_links_section(payload)
    )
    if additions:
        marker = '<section class="sources" id="sources">'
        document = document.replace(marker, additions + marker, 1)
        extra_css = (
            ".governance dl{display:grid;grid-template-columns:minmax(10rem,auto) 1fr;"
            "gap:.45rem 1rem}.governance dt{font-weight:700}.governance dd{margin:0}"
            ".source-log{padding-inline-start:1.2rem}"
            "@media(max-width:640px){.governance dl{grid-template-columns:1fr}}"
            "@media print{.governance,.related{break-inside:avoid}}"
        )
        document = document.replace("</style>", extra_css + "</style>", 1)

    return document


base.render_page = render_page


def validated_editorial_release(repo_root: Path) -> set[str]:
    ledger_path = repo_root / REVIEW_LEDGER
    if not ledger_path.is_file():
        raise base.PublicationError(f"Editorial release ledger not found: {ledger_path}")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(ledger, dict):
        raise base.PublicationError("Editorial release ledger must be a JSON object")
    if ledger.get("clinicalReviewClaimed") is not False:
        raise base.PublicationError(
            "Editorial release must explicitly state that clinical review is not claimed"
        )
    if ledger.get("reviewType") != "internal-editorial-and-source-structure-review":
        raise base.PublicationError("Unexpected editorial review type")

    released = ledger.get("releasedSources")
    if not isinstance(released, list):
        raise base.PublicationError("releasedSources must be a list")
    names = {
        Path(str(item.get("path") or "")).name
        for item in released
        if isinstance(item, dict) and item.get("decision") == "publish-educational-content"
    }
    if names != RELEASED_MANUAL_REVIEW_SOURCES:
        raise base.PublicationError(
            f"Editorial release mismatch: expected {sorted(RELEASED_MANUAL_REVIEW_SOURCES)}, got {sorted(names)}"
        )
    for name in names:
        source_path = repo_root / base.CONTENT_DIR / name
        if not source_path.is_file():
            raise base.PublicationError(f"Released source is missing: {source_path}")
    return names


def write_publication(repo_root: Path, *, check: bool = False) -> dict[str, Any]:
    released = validated_editorial_release(repo_root)
    original_manual_review_sources = set(base.MANUAL_REVIEW_SOURCES)
    base.MANUAL_REVIEW_SOURCES = original_manual_review_sources - released
    try:
        return base.write_publication(repo_root, check=check)
    finally:
        base.MANUAL_REVIEW_SOURCES = original_manual_review_sources


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize reviewed sectors-v10 sources with structured-reference "
            "compatibility and an explicit internal editorial release ledger."
        )
    )
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = write_publication(args.repo_root.resolve(), check=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
