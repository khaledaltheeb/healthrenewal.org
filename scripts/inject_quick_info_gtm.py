#!/usr/bin/env python3
"""Restore the site's established Google Tag Manager contract on Quick Info only.

The canonical sitewide injector remains the single implementation of GTM
placement. This wrapper scopes it to the Quick Information hub and its 250
articles, then verifies both the head script and body noscript positions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import inject_google_tag_manager as gtm

ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "api" / "v1" / "quick-info.json"
REPORT_PATH = ROOT / "reports" / "quick-info-gtm.json"
EXPECTED_ARTICLES = 250
HEAD_RE = re.compile(r"<head\b[^>]*>", re.I)
BODY_RE = re.compile(r"<body\b[^>]*>", re.I)


def validate_page(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig", errors="strict")
    failures: list[str] = []
    head = HEAD_RE.search(text)
    body = BODY_RE.search(text)
    if not head:
        failures.append("missing <head>")
    elif gtm.GTM_ID not in text[head.end(): head.end() + 1400]:
        failures.append("GTM head script not directly after <head>")
    if not body:
        failures.append("missing <body>")
    elif f"ns.html?id={gtm.GTM_ID}" not in text[body.end(): body.end() + 1000]:
        failures.append("GTM noscript not directly after <body>")
    if text.count("googletagmanager.com/gtm.js") != 1:
        failures.append("GTM head script count is not exactly one")
    if text.count(f"googletagmanager.com/ns.html?id={gtm.GTM_ID}") != 1:
        failures.append("GTM noscript count is not exactly one")
    return failures


def main() -> None:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if payload.get("count") != EXPECTED_ARTICLES or len(items) != EXPECTED_ARTICLES:
        raise SystemExit(f"Expected {EXPECTED_ARTICLES} Quick Info articles, found {len(items)}")

    pages = [ROOT / "quick-info" / "index.html"] + [
        ROOT / "quick-info" / item["slug"] / "index.html" for item in items
    ]
    missing = [page.relative_to(ROOT).as_posix() for page in pages if not page.is_file()]
    if missing:
        raise SystemExit("Missing Quick Info HTML: " + ", ".join(missing[:20]))

    changed = 0
    warnings: list[dict[str, str]] = []
    for page in pages:
        page_changed, page_warnings = gtm.patch_html(page)
        changed += int(page_changed)
        warnings.extend(
            {"path": page.relative_to(ROOT).as_posix(), "warning": warning}
            for warning in page_warnings
        )

    failures: list[dict[str, object]] = []
    for page in pages:
        page_failures = validate_page(page)
        if page_failures:
            failures.append({
                "path": page.relative_to(ROOT).as_posix(),
                "failures": page_failures,
            })

    report = {
        "version": "1.0.0",
        "status": "passed" if not warnings and not failures else "failed",
        "gtmId": gtm.GTM_ID,
        "articles": EXPECTED_ARTICLES,
        "pagesExpected": EXPECTED_ARTICLES + 1,
        "pagesChecked": len(pages),
        "pagesChanged": changed,
        "warnings": warnings,
        "failures": failures,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit("Quick Info GTM validation failed")


if __name__ == "__main__":
    main()
