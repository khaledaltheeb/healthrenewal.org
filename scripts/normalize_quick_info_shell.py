#!/usr/bin/env python3
"""Normalize only the Quick Information hub and its 250 articles.

Uses the repository's canonical platform-shell implementation while keeping the
operation scoped to Quick Information so unrelated site surfaces are never
rewritten by this workflow.
"""

from __future__ import annotations

import json
from pathlib import Path

import normalize_platform_shell as platform

ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "api" / "v1" / "quick-info.json"
REPORT_PATH = ROOT / "reports" / "quick-info-platform-shell.json"
EXPECTED_COUNT = 250


def main() -> None:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if payload.get("count") != EXPECTED_COUNT or len(items) != EXPECTED_COUNT:
        raise SystemExit(f"Expected {EXPECTED_COUNT} Quick Information items, found {len(items)}")

    pages = [ROOT / "quick-info" / "index.html"] + [
        ROOT / "quick-info" / item["slug"] / "index.html" for item in items
    ]
    missing = [page.relative_to(ROOT).as_posix() for page in pages if not page.is_file()]
    if missing:
        raise SystemExit("Missing Quick Information pages: " + ", ".join(missing[:20]))

    results = [platform.normalize_file(page, ROOT, check_only=False) for page in pages]
    failures = [
        {"path": result.path, "status": result.status, "detail": result.detail}
        for result in results
        if result.status in {"error", "skipped"}
    ]

    postcheck = [platform.normalize_file(page, ROOT, check_only=True) for page in pages]
    drift = [
        {"path": result.path, "status": result.status, "detail": result.detail}
        for result in postcheck
        if result.status != "current"
    ]

    report = {
        "version": "1.0.0",
        "status": "passed" if not failures and not drift else "failed",
        "shellVersion": platform.SHELL_VERSION,
        "pagesExpected": EXPECTED_COUNT + 1,
        "pagesProcessed": len(results),
        "updated": sum(result.status == "updated" for result in results),
        "alreadyCurrent": sum(result.status == "current" for result in results),
        "failures": failures,
        "postcheckDrift": drift,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit("Quick Information platform shell normalization failed")


if __name__ == "__main__":
    main()
