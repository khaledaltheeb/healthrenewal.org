#!/usr/bin/env python3
"""Build the Rawafid magazine through one evidence-first v202 production path."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
MAGAZINE = ROOT / "magazine"
FEED_LIMIT = 20


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_repairs_and_enrichments(api: Path) -> None:
    repairs = load_module("magazine_repairs_v202", SCRIPTS / "repair_magazine_citation_integrity_v202.py")
    repair_report = repairs.apply_repairs(MAGAZINE, strict=True)
    write_json(api / "magazine-citation-repairs-v202.json", repair_report)

    enrich = load_module("magazine_enrich_v202", SCRIPTS / "apply_magazine_enrichments_v202.py")
    for registry_path in sorted(DATA.glob("magazine-enrichments-v202-*.json")):
        registry = enrich.load_registry(registry_path)
        report = enrich.apply_registry(MAGAZINE, registry, strict=True)
        write_json(api / f"{registry_path.stem}-report.json", report)


def build_verification(api: Path) -> Path:
    audit = load_module("magazine_audit_bundle_v202", SCRIPTS / "audit_magazine_sources_v202.py")
    manifest = audit.build_manifest()
    write_json(api / "magazine-source-manifest-v202.json", manifest)
    pages = manifest.get("pages") or []
    study_pages = len(pages)
    if study_pages < 1:
        raise SystemExit("Magazine v202 audit discovered zero study pages")

    verification_path = api / "magazine-bibliography-verification-v202.json"
    if verification_path.is_file():
        existing = json.loads(verification_path.read_text(encoding="utf-8"))
        summary = existing.get("summary") or {}
        if (
            int(summary.get("study_pages") or 0) == study_pages
            and int(summary.get("verified_source_pages") or 0) == study_pages
            and int(summary.get("source_pages_still_requiring_manual_review") or 0) == 0
        ):
            return verification_path

    verifier = load_module("magazine_verify_bundle_v202", SCRIPTS / "verify_magazine_bibliography_v202.py")
    dois = list(dict.fromkeys(str(d).lower() for page in pages for d in (page.get("doi") or [])))
    pmids = list(dict.fromkeys(str(p) for page in pages for p in (page.get("pmid") or [])))
    doi_records, pmid_records = verifier.verify_all(dois, pmids, workers=6)
    verified_pages = [verifier.page_verification(page, doi_records, pmid_records) for page in pages]
    counts: dict[str, int] = {}
    for page in verified_pages:
        key = str(page["bibliographic_verification"])
        counts[key] = counts.get(key, 0) + 1
    report = {
        "schema_version": 2,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "authority": {"doi": ["Crossref", "DataCite", "doi.org resolver fallback"], "pmid": ["NCBI PubMed ESummary"]},
        "summary": {
            "study_pages": study_pages,
            "unique_dois": len(dois),
            "unique_pmids": len(pmids),
            "doi_verified": sum(record.status == "verified" for record in doi_records.values()),
            "doi_resolvable_only": sum(record.status == "resolvable_only" for record in doi_records.values()),
            "doi_unverified": sum(record.status == "unverified" for record in doi_records.values()),
            "pmid_verified": sum(record.status == "verified" for record in pmid_records.values()),
            "pmid_unverified": sum(record.status == "unverified" for record in pmid_records.values()),
            "page_status_counts": counts,
        },
        "pages": verified_pages,
    }

    overrides = load_module("magazine_overrides_bundle_v202", SCRIPTS / "apply_magazine_repository_overrides_v202.py")
    merged = overrides.apply_overrides(report, overrides.load_overrides(DATA / "magazine-source-overrides-v202.json"))
    summary = merged.get("summary") or {}
    if int(summary.get("verified_source_pages") or 0) != study_pages:
        raise SystemExit(f"Not every magazine page has a verified source: {summary}")
    if int(summary.get("source_pages_still_requiring_manual_review") or 0) != 0:
        raise SystemExit(f"Magazine source verification still has manual-review gaps: {summary}")
    write_json(verification_path, merged)
    return verification_path


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    apply_repairs_and_enrichments(api)
    verification_path = build_verification(api)
    publisher = load_module("magazine_publisher_bundle_v202", SCRIPTS / "publish_magazine_v202.py")
    report = publisher.publish(site, verification_path)
    if int(report.get("missing_source_pages") or 0) != 0:
        raise SystemExit("Magazine v202 reports pages without sources")
    if int(report.get("unwired_research_pages") or 0) != 0:
        raise SystemExit("Magazine v202 reports unwired study pages")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps({
        "version": 202,
        "published_study_pages": report["published_study_pages"],
        "wired_study_pages": report["wired_study_pages"],
        "missing_source_pages": report["missing_source_pages"],
        "verified_and_complete": report["bibliographically_verified_and_complete"],
        "rss_items": report["rss_items"],
        "sitemap_urls": (report.get("sitemap") or {}).get("child_urls"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
