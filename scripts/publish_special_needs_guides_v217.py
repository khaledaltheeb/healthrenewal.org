#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import publish_special_needs_condition_hubs_v302 as condition302
import publish_special_needs_guides_v214 as batch214
import publish_special_needs_guides_v217_core as core
import publish_special_needs_hub_v235_compat as hub235

ROOT = Path(__file__).resolve().parents[1]
V214_MANIFEST = ROOT / "content" / "v214" / "special-needs-guides-manifest-ar.json"
PRODUCTION_MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"
VERSIONS = (209, 210, 211, 212, 214)


def summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": report["version"],
        "status": report["status"],
        "guide_count": report["guide_count"],
        "minimum_source_words": report["minimum_source_words"],
        "source_count": report["source_count"],
    }


def load_production_manifest() -> dict[str, Any]:
    data = json.loads(PRODUCTION_MANIFEST.read_text(encoding="utf-8"))
    paths = data.get("source_files", [])
    if data.get("version") != 221 or data.get("status") != "production-integrated":
        raise SystemExit("Special-needs production manifest contract is invalid")
    if data.get("review_status") != "internally-reviewed" or data.get("external_review") != "recommended-not-completed":
        raise SystemExit("Special-needs production manifest review state is dishonest")
    if len(paths) != 25 or len(paths) != len(set(paths)):
        raise SystemExit("Special-needs production manifest must list twenty-five unique source files")
    missing = [path for path in paths if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"Special-needs production manifest references missing files: {missing}")
    return data


def publish(site: Path) -> dict[str, Any]:
    for slug in ("autism", "down-syndrome"):
        shutil.rmtree(site / "special-needs" / slug, ignore_errors=True)
    production_manifest = load_production_manifest()
    hub_report = hub235.publish(site)
    if hub_report.get("version") != 235 or hub_report.get("guide_count") != 25:
        raise SystemExit(f"Institutional special-needs hub contract failed: {hub_report}")
    if hub_report.get("source_count") != 10 or hub_report.get("jordan_source_count") != 3:
        raise SystemExit(f"Institutional special-needs source contract failed: {hub_report}")
    if hub_report.get("jordan_context_section") is not True:
        raise SystemExit("Institutional Jordan context contract failed")
    if hub_report.get("asha_aac_source_updated") is not True:
        raise SystemExit("Institutional AAC source contract failed")

    base = core.publish(site)
    manifest = core.read_manifest(V214_MANIFEST, 214)
    titles: dict[str, str] = {}
    for slug in manifest["guide_slugs"]:
        guide_path = V214_MANIFEST.parent / "special-needs-guides" / f"{slug}.json"
        guide = json.loads(guide_path.read_text(encoding="utf-8"))
        titles[slug] = guide["title"]

    report214 = batch214.publish(site)
    if report214.get("guide_count") != 5 or report214.get("generated_page_count") != 5:
        raise SystemExit(f"v214 publisher did not generate five guides: {report214}")
    if report214.get("review_status") != "internally-reviewed":
        raise SystemExit("v214 changed the honest review status")
    report214["status"] = "production-integrated"
    report214["production_contract"] = 221
    (site / "api" / "special-needs-guides-v214.json").write_text(
        json.dumps(report214, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    all_slugs = list(base["guide_slugs"]) + list(manifest["guide_slugs"])
    if len(all_slugs) != 25 or len(all_slugs) != len(set(all_slugs)):
        raise SystemExit("The five batches must produce twenty-five unique guide routes")

    pages = list(base["generated_pages"])
    validated214 = [core.validate_page(site, slug, titles[slug]) for slug in manifest["guide_slugs"]]
    pages.extend(page["path"] for page in validated214)
    discovery = core.validate_discovery(site, all_slugs)

    condition_report = condition302.publish(site)
    if condition_report.get("version") != 302 or condition_report.get("condition_count") != 2:
        raise SystemExit(f"Special-needs condition hub contract failed: {condition_report}")
    if condition_report.get("condition_slugs") != ["autism", "down-syndrome"]:
        raise SystemExit("Autism and Down syndrome routes are required")
    if condition_report.get("generated_page_count") != 2 or condition_report.get("source_count", 0) < 15:
        raise SystemExit("Scientific condition page depth contract failed")

    report = {
        **base,
        "version": 221,
        "legacy_contract": 217,
        "guide_contract": 221,
        "hub_contract": 235,
        "hub_release": 241,
        "condition_hubs_contract": 302,
        "status": "passed",
        "production_status": "integrated",
        "batches": list(VERSIONS),
        "batch_count": 5,
        "guide_count": 25,
        "guide_slugs": all_slugs,
        "generated_pages": pages,
        "minimum_rendered_words": min(base["minimum_rendered_words"], *(page["words"] for page in validated214)),
        "minimum_h2": min(base["minimum_h2"], *(page["h2"] for page in validated214)),
        "minimum_citations": min(base["minimum_citations"], *(page["citations"] for page in validated214)),
        "review_status": "internally-reviewed",
        "external_review_completed": False,
        "external_review": "recommended-not-completed",
        "production_source_manifest": PRODUCTION_MANIFEST.relative_to(ROOT).as_posix(),
        "production_source_file_count": len(production_manifest["source_files"]),
        "hub": {
            "status": hub_report["status"],
            "pathway_count": hub_report["pathway_count"],
            "faq_count": hub_report["faq_count"],
            "source_count": hub_report["source_count"],
            "jordan_source_count": hub_report["jordan_source_count"],
            "jordan_context_section": hub_report["jordan_context_section"],
            "asha_aac_source_updated": hub_report["asha_aac_source_updated"],
            "seo": hub_report["seo"],
            "accessibility": hub_report["accessibility"],
        },
        "condition_hubs": {
            "status": condition_report["status"],
            "version": condition_report["version"],
            "condition_count": condition_report["condition_count"],
            "condition_slugs": condition_report["condition_slugs"],
            "generated_pages": condition_report["generated_pages"],
            "source_count": condition_report["source_count"],
            "provider_source": condition_report["provider_source"],
            "published_provider_count": condition_report["published_provider_count"],
            "sitemap_registered": condition_report["sitemap_registered"],
        },
        **discovery,
        "batch_reports": [*base["batch_reports"], summary(report214)],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    (api / "special-needs-guides-v217.json").write_text(payload, encoding="utf-8")
    (api / "special-needs-guides-v221.json").write_text(payload, encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
