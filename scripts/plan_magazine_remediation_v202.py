#!/usr/bin/env python3
"""Turn magazine audit + verification reports into a deterministic repair queue.

The planner never edits content. It prioritizes source problems, indexability
problems, truly thin pages, core scientific gaps and then gold-standard gaps.
This gives editors a title-by-title queue instead of bulk-filling pages with
repetitive boilerplate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VERIFIED_STATUSES = {"verified_identifier", "verified_repository"}

WEIGHTS = {
    "source_unverified": 100,
    "noindex": 95,
    "thin_under_500": 70,
    "core_section": 20,
    "gold_section": 7,
    "below_gold_depth": 5,
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return value


def verification_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pages = report.get("pages")
    if not isinstance(pages, list):
        raise SystemExit("Verification report has no pages array")
    return {
        str(page.get("path")): page
        for page in pages
        if isinstance(page, dict) and page.get("path")
    }


def classify_sector(path: str) -> str:
    if "/pediatric-oncology/theses/" in path:
        return "pediatric-oncology-theses"
    if "/pediatric-oncology/studies/" in path:
        return "pediatric-oncology-studies"
    if "/pediatric-oncology/" in path:
        return "pediatric-oncology"
    if path.startswith("magazine/thesis-"):
        return "theses-general"
    return "magazine-general"


def page_priority(page: dict[str, Any], verification: dict[str, Any] | None) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    status = str((verification or {}).get("bibliographic_verification") or "unverified")
    if status not in VERIFIED_STATUSES:
        score += WEIGHTS["source_unverified"]
        reasons.append(f"source:{status}")
    if page.get("noindex"):
        score += WEIGHTS["noindex"]
        reasons.append("published_page_noindex")
    word_count = int(page.get("word_count") or 0)
    if word_count < 500:
        score += WEIGHTS["thin_under_500"]
        reasons.append(f"thin:{word_count}_words")
    elif word_count < 700:
        score += WEIGHTS["below_gold_depth"]
        reasons.append(f"below_gold_depth:{word_count}_words")

    core_missing = [str(x) for x in page.get("missing_core_sections") or []]
    gold_missing = [str(x) for x in page.get("missing_gold_sections") or []]
    score += len(core_missing) * WEIGHTS["core_section"]
    score += len([x for x in gold_missing if x not in core_missing]) * WEIGHTS["gold_section"]
    reasons.extend(f"core:{name}" for name in core_missing)
    reasons.extend(f"gold:{name}" for name in gold_missing if name not in core_missing)
    return score, reasons


def build_plan(audit: dict[str, Any], verification: dict[str, Any], batch_size: int) -> dict[str, Any]:
    audit_pages = audit.get("pages")
    if not isinstance(audit_pages, list):
        raise SystemExit("Audit report has no pages array")
    verified = verification_map(verification)

    queue: list[dict[str, Any]] = []
    for page in audit_pages:
        if not isinstance(page, dict):
            continue
        path = str(page.get("path") or "")
        v = verified.get(path)
        score, reasons = page_priority(page, v)
        if score <= 0:
            continue
        primary_source = (v or {}).get("primary_source")
        queue.append(
            {
                "path": path,
                "url": page.get("url"),
                "title": page.get("title"),
                "sector": classify_sector(path),
                "priority_score": score,
                "word_count": page.get("word_count"),
                "source_status": (v or {}).get("bibliographic_verification"),
                "primary_source": primary_source,
                "missing_core_sections": page.get("missing_core_sections") or [],
                "missing_gold_sections": page.get("missing_gold_sections") or [],
                "reasons": reasons,
                "editorial_action": (
                    "verify source before content work"
                    if any(reason.startswith("source:") for reason in reasons)
                    else "complete only evidence-supported missing sections; preserve existing content"
                ),
            }
        )

    queue.sort(key=lambda item: (-int(item["priority_score"]), str(item["path"])))
    batches = [queue[i : i + batch_size] for i in range(0, len(queue), batch_size)]
    by_sector: dict[str, int] = {}
    for item in queue:
        sector = str(item["sector"])
        by_sector[sector] = by_sector.get(sector, 0) + 1

    audit_summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    verification_summary = verification.get("summary") if isinstance(verification.get("summary"), dict) else {}
    return {
        "schema_version": 1,
        "policy": {
            "source_first": True,
            "non_destructive": True,
            "no_bulk_boilerplate": True,
            "page_complete_only_when_gold_contract_and_source_verification_pass": True,
        },
        "summary": {
            "study_pages": audit_summary.get("study_pages"),
            "core_complete_with_source": audit_summary.get("core_complete_with_source"),
            "gold_complete_before_bibliographic_verification": audit_summary.get("gold_complete_before_bibliographic_verification"),
            "verified_source_pages": verification_summary.get("verified_source_pages"),
            "pages_requiring_editorial_work": len(queue),
            "batches": len(batches),
            "batch_size": batch_size,
            "by_sector": by_sector,
        },
        "batches": [
            {"batch": index + 1, "pages": pages}
            for index, pages in enumerate(batches)
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--verification", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--batch-size", type=int, default=25)
    args = ap.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    plan = build_plan(load_json(args.audit), load_json(args.verification), args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
