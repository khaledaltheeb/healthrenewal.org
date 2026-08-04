#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def validate_source(path: Path, payload: dict[str, Any]) -> None:
    normalize_payload(payload)
    _ORIGINAL_VALIDATE(path, payload)


base.validate_source = validate_source


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
