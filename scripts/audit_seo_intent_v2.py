#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "scripts" / "audit_seo_intent_v1.py"
FRAGMENT_ROOT = "content/quick-info-editorial/"


def is_editorial_fragment(path: str) -> bool:
    if not path.startswith(FRAGMENT_ROOT):
        return False
    source_path = ROOT / path
    if not source_path.is_file():
        return False
    source = source_path.read_text(encoding="utf-8", errors="replace").lower()
    # These files are intentionally inserted into a publication shell. Treat
    # them as fragments only when they genuinely lack a document shell.
    return not all(token in source for token in ("<html", "<head", "<body"))


def recompute(report: dict) -> dict:
    original = list(report.get("results") or [])
    excluded = [item for item in original if is_editorial_fragment(str(item.get("path") or ""))]
    kept = [item for item in original if item not in excluded]
    errors = sum(int(item.get("errors") or 0) for item in kept)
    warnings = sum(int(item.get("warnings") or 0) for item in kept)
    failed = sum(1 for item in kept if int(item.get("errors") or 0) > 0)
    summary = dict(report.get("summary") or {})
    summary.update({
        "pages": len(kept),
        "errors": errors,
        "warnings": warnings,
        "passed": len(kept) - failed,
        "failed": failed,
        "excluded_editorial_fragments": len(excluded),
    })
    report["contract"] = "sitewide-semantic-seo-search-intent-v2"
    report["summary"] = summary
    report["results"] = kept
    report["excluded"] = [
        {
            "path": item.get("path"),
            "reason": "editorial-fragment-without-document-shell",
            "original_errors": item.get("errors", 0),
            "original_warnings": item.get("warnings", 0),
        }
        for item in excluded
    ]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SEO intent v1 while excluding proven editorial fragments from page-level requirements.")
    parser.add_argument("--scope", choices=("priority", "all"), default="all")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "seo-v1.json"
        cmd = [sys.executable, str(V1), "--scope", args.scope, "--report", str(raw)]
        proc = subprocess.run(cmd, cwd=ROOT, text=True)
        if proc.returncode not in (0, 1):
            return proc.returncode
        report = json.loads(raw.read_text(encoding="utf-8"))

    report = recompute(report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.strict and int(report["summary"].get("failed") or 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
