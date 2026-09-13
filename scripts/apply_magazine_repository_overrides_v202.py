#!/usr/bin/env python3
"""Apply audited institutional-repository evidence to magazine verification.

Crossref and PubMed are not universal registries. University theses can have a
fully authoritative repository record while having no DOI, a non-Crossref DOI,
or a DOI resolver problem. This step applies only explicit records from
``data/magazine-source-overrides-v202.json`` and never marks arbitrary external
links as verified.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDES = ROOT / "data" / "magazine-source-overrides-v202.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return value


def load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    records = data.get("records")
    if not isinstance(records, list):
        raise SystemExit("Override registry must contain a records array")
    out: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise SystemExit("Every override record must be an object")
        page_path = str(record.get("path") or "").strip()
        source_url = str(record.get("source_url") or "").strip()
        status = str(record.get("verification_status") or "").strip()
        if not page_path or not source_url or status != "verified_repository":
            raise SystemExit(f"Invalid repository override: {record}")
        if not source_url.startswith("https://"):
            raise SystemExit(f"Repository override must use HTTPS: {source_url}")
        if page_path in out:
            raise SystemExit(f"Duplicate override for {page_path}")
        out[page_path] = record
    return out


def apply_overrides(report: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pages = report.get("pages")
    if not isinstance(pages, list):
        raise SystemExit("Verification report has no pages array")

    seen: set[str] = set()
    covered_unresolved_identifiers = 0
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_path = str(page.get("path") or "")
        override = overrides.get(page_path)
        if not override:
            continue
        seen.add(page_path)
        if any(
            isinstance(item, dict) and item.get("status") == "unverified"
            for item in page.get("doi_records") or []
        ):
            covered_unresolved_identifiers += 1
        page["bibliographic_verification"] = "verified_repository"
        page["primary_source"] = {
            "kind": "repository",
            "status": "verified",
            "source_type": override.get("source_type"),
            "institution": override.get("institution"),
            "title": override.get("verified_title"),
            "author": override.get("author"),
            "year": override.get("year"),
            "work_type": override.get("work_type"),
            "canonical_url": override.get("source_url"),
            "repository_identifier": override.get("repository_identifier"),
            "reported_doi": override.get("reported_doi"),
            "verification_note": override.get("verification_note"),
        }
        page["repository_override"] = True

    missing_from_report = sorted(set(overrides) - seen)
    if missing_from_report:
        raise SystemExit(f"Repository overrides point to undiscovered study pages: {missing_from_report}")

    counts: dict[str, int] = {}
    for page in pages:
        if isinstance(page, dict):
            key = str(page.get("bibliographic_verification") or "unknown")
            counts[key] = counts.get(key, 0) + 1

    summary = report.setdefault("summary", {})
    if not isinstance(summary, dict):
        raise SystemExit("Verification report summary is not an object")
    summary["page_status_counts"] = counts
    summary["repository_verified_pages"] = counts.get("verified_repository", 0)
    summary["verified_source_pages"] = counts.get("verified_identifier", 0) + counts.get("verified_repository", 0)
    summary["unresolved_identifier_pages_covered_by_repository"] = covered_unresolved_identifiers
    summary["source_pages_still_requiring_manual_review"] = sum(
        value
        for key, value in counts.items()
        if key not in {"verified_identifier", "verified_repository"}
    )
    report["repository_override_registry"] = {
        "applied": len(seen),
        "policy": "explicit-authoritative-institutional-records-only",
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    report = load_json(args.input)
    overrides = load_overrides(args.overrides)
    merged = apply_overrides(report, overrides)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(merged.get("summary", {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
