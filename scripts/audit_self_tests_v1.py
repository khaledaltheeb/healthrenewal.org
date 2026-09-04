#!/usr/bin/env python3
"""Static quality gate for Rawafid interactive self-tests.

Run from repository root:
    python scripts/audit_self_tests_v1.py

This intentionally uses only the Python standard library.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / ".self-tests" / "catalog.json"
ENGINE = ROOT / "assets" / "self-tests" / "self-tests.js"

FORBIDDEN_ENGINE_TOKENS = {
    "localStorage": "persistent browser storage",
    "sessionStorage": "browser session storage",
    "indexedDB": "IndexedDB persistence",
    "document.cookie": "cookie persistence",
    "XMLHttpRequest": "network transmission",
    "fetch(": "network transmission",
    "sendBeacon": "analytics/network transmission",
    "dataLayer.push": "analytics payload transmission",
}

REQUIRED_PAGE_MARKERS = [
    "ليست مقياسًا تشخيصيًا",
    "الخصوصية",
    "data-self-test-root",
    "قسم المختصين",
    "لا يرسل",
    "مراسلتنا باختياري",
]

AMBIGUITY_PATTERNS = [
    (re.compile(r"\bليس\b.*\bلا\b"), "possible double negation"),
    (re.compile(r"\bلا\b.*\bليس\b"), "possible double negation"),
]


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def extract_config(html: str) -> str | None:
    marker = "window.RAWAFID_SELF_TEST="
    start = html.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = html.find(";</script>", start)
    return html[start:end] if end >= 0 else None


def extract_items(config: str) -> list[tuple[str, str]]:
    # The test configs deliberately use a constrained object-literal form.
    return re.findall(r"\{dimension:'([^']+)',text:'([^']+)'\}", config)


def extract_dimensions(config: str) -> set[str]:
    head = config.split("bands:", 1)[0]
    return set(re.findall(r"\{id:'([^']+)',label:'[^']+'\}", head))


def audit_engine(errors: list[str]) -> None:
    if not ENGINE.exists():
        fail(errors, f"missing engine: {ENGINE.relative_to(ROOT)}")
        return
    text = ENGINE.read_text(encoding="utf-8")
    for token, reason in FORBIDDEN_ENGINE_TOKENS.items():
        if token in text:
            fail(errors, f"engine contains forbidden {reason}: {token}")
    if "new Array(cfg.items.length).fill(null)" not in text:
        fail(errors, "engine missing explicit unanswered-state initialization")
    if "missing" not in text and "findIndex(v=>v===null)" not in text:
        fail(errors, "engine may not block scoring with unanswered items")


def audit_item_wording(errors: list[str], warnings: list[str], route: str, items: list[tuple[str, str]]) -> None:
    texts = [text for _, text in items]
    duplicate = [t for t, n in Counter(texts).items() if n > 1]
    for text in duplicate:
        fail(errors, f"{route}: duplicate item: {text}")
    for idx, (_, text) in enumerate(items, 1):
        if len(text) > 125:
            warnings.append(f"{route} item {idx}: long wording ({len(text)} chars)")
        if "؟" in text and text.count("؟") > 1:
            warnings.append(f"{route} item {idx}: may ask more than one question")
        for pattern, reason in AMBIGUITY_PATTERNS:
            if pattern.search(text):
                warnings.append(f"{route} item {idx}: {reason}: {text}")


def audit_page(entry: dict, errors: list[str], warnings: list[str]) -> None:
    route = entry["route"]
    rel = route.strip("/")
    path = ROOT / rel / "index.html"
    if not path.exists():
        fail(errors, f"catalog route missing page: {route}")
        return
    html = path.read_text(encoding="utf-8")
    for marker in REQUIRED_PAGE_MARKERS:
        if marker not in html:
            fail(errors, f"{route}: missing required marker: {marker}")
    for token in ("localStorage", "sessionStorage", "indexedDB", "document.cookie", "dataLayer.push"):
        if token in html:
            fail(errors, f"{route}: forbidden privacy-sensitive token: {token}")
    config = extract_config(html)
    if not config:
        fail(errors, f"{route}: missing RAWAFID_SELF_TEST config")
        return
    items = extract_items(config)
    expected = int(entry["item_count"])
    if len(items) != expected:
        fail(errors, f"{route}: item count {len(items)} != catalog {expected}")
    dimensions = extract_dimensions(config)
    declared = set(entry["dimensions"])
    if dimensions != declared:
        fail(errors, f"{route}: config dimensions {sorted(dimensions)} != catalog {sorted(declared)}")
    counts = Counter(dim for dim, _ in items)
    unknown = set(counts) - dimensions
    if unknown:
        fail(errors, f"{route}: items reference unknown dimensions {sorted(unknown)}")
    empty = dimensions - set(counts)
    if empty:
        fail(errors, f"{route}: dimensions without items {sorted(empty)}")
    if entry.get("diagnostic") is not False:
        fail(errors, f"{route}: public self-test catalog must explicitly declare diagnostic=false")
    if entry.get("data_persistence") != "none":
        fail(errors, f"{route}: data_persistence must be none")
    audit_item_wording(errors, warnings, route, items)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if not CATALOG.exists():
        print("FAIL: missing .self-tests/catalog.json")
        return 1
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: invalid catalog JSON: {exc}")
        return 1
    audit_engine(errors)
    ids = [x.get("id") for x in catalog.get("items", [])]
    routes = [x.get("route") for x in catalog.get("items", [])]
    if len(ids) != len(set(ids)):
        fail(errors, "duplicate catalog ids")
    if len(routes) != len(set(routes)):
        fail(errors, "duplicate catalog routes")
    for entry in catalog.get("items", []):
        audit_page(entry, errors, warnings)
    for msg in warnings:
        print(f"WARN: {msg}")
    for msg in errors:
        print(f"FAIL: {msg}")
    if errors:
        print(f"\nSelf-tests audit failed: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"PASS: {len(catalog.get('items', []))} self-test(s) audited; {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
