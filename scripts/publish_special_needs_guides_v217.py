#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import publish_special_needs_condition_hubs_v302 as condition302
import publish_special_needs_condition_postlaunch_v305 as postlaunch305
import publish_special_needs_condition_trust_v307 as trust307
import publish_special_needs_guides_v214 as batch214
import publish_special_needs_guides_v217_core as core
import publish_special_needs_hub_v235_compat as hub235
import validate_special_needs_provider_directory_v308 as provider308

ROOT = Path(__file__).resolve().parents[1]
V214_MANIFEST = ROOT / "content" / "v214" / "special-needs-guides-manifest-ar.json"
PRODUCTION_MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"
VERSIONS = (209, 210, 211, 212, 214)
CONDITION_URLS = {
    f"{condition302.BASE}/special-needs/autism/",
    f"{condition302.BASE}/special-needs/down-syndrome/",
}


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


def reset_condition_outputs(site: Path) -> None:
    for slug in ("autism", "down-syndrome"):
        shutil.rmtree(site / "special-needs" / slug, ignore_errors=True)
    for name in (
        "special-needs-condition-hubs-v302.json",
        "special-needs-condition-postlaunch-v305.json",
        "special-needs-condition-trust-v307.json",
        "special-needs-provider-governance-v308.json",
    ):
        (site / "api" / name).unlink(missing_ok=True)

    sitemap_path = site / "sitemap-special-needs.xml"
    if not sitemap_path.is_file():
        return
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    removed = False
    for row in list(root.findall("{*}url")):
        loc = (row.findtext("{*}loc") or "").strip()
        if loc in CONDITION_URLS:
            root.remove(row)
            removed = True
    if removed:
        tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict[str, Any]:
    reset_condition_outputs(site)

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

    provider_report = provider308.publish(site)
    if provider_report.get("version") != 308 or provider_report.get("status") != "passed":
        raise SystemExit(f"Provider directory governance contract failed: {provider_report}")
    if provider_report.get("sponsored_publication_enabled") is not False:
        raise SystemExit("Sponsored provider publishing must remain disabled until visible disclosure rendering exists")

    condition_report = condition302.publish(site)
    if condition_report.get("version") != 302 or condition_report.get("condition_count") != 2:
        raise SystemExit(f"Special-needs condition hub contract failed: {condition_report}")
    if condition_report.get("condition_slugs") != ["autism", "down-syndrome"]:
        raise SystemExit("Autism and Down syndrome routes are required")
    if condition_report.get("generated_page_count") != 2 or condition_report.get("source_count", 0) < 15:
        raise SystemExit("Scientific condition page depth contract failed")
    if condition_report.get("published_provider_count") != provider_report.get("published_count") * 2:
        # A provider covering both conditions appears once on each condition page.
        expected = sum(condition_report.get("provider_counts", {}).values())
        if expected != condition_report.get("published_provider_count"):
            raise SystemExit("Rendered provider counts are internally inconsistent")

    postlaunch_report = postlaunch305.publish(site)
    if postlaunch_report.get("version") != 305 or postlaunch_report.get("status") != "passed":
        raise SystemExit(f"Condition post-launch audit contract failed: {postlaunch_report}")
    if postlaunch_report.get("condition_slugs") != ["autism", "down-syndrome"]:
        raise SystemExit("Post-launch audit must cover both condition routes")
    if postlaunch_report.get("related_link_count") != 16:
        raise SystemExit("Post-launch internal-link graph must contain sixteen contextual links")
    if not all(
        postlaunch_report.get(key) is True
        for key in ("visible_breadcrumbs", "meta_enhanced", "provider_policy_visible", "focus_visibility_guard")
    ):
        raise SystemExit("Post-launch accessibility and transparency controls are incomplete")

    trust_report = trust307.publish(site)
    if trust_report.get("version") != 307 or trust_report.get("status") != "passed":
        raise SystemExit(f"Condition trust and FAQ contract failed: {trust_report}")
    if trust_report.get("condition_slugs") != ["autism", "down-syndrome"] or trust_report.get("faq_count") != 8:
        raise SystemExit("Trust layer must publish four referenced FAQs for each condition")
    if trust_report.get("faq_schema_visible_match") is not True:
        raise SystemExit("Visible FAQ content and FAQPage structured data must match")
    if trust_report.get("external_clinical_review_completed") is not False:
        raise SystemExit("Trust layer must not overstate external clinical review")

    report = {
        **base,
        "version": 221,
        "legacy_contract": 217,
        "guide_contract": 221,
        "hub_contract": 235,
        "hub_release": 241,
        "condition_hubs_contract": 302,
        "condition_postlaunch_contract": 305,
        "condition_trust_contract": 307,
        "provider_governance_contract": 308,
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
            "provider_governance": {
                "version": provider_report["version"],
                "checked_at": provider_report["checked_at"],
                "record_count": provider_report["record_count"],
                "published_count": provider_report["published_count"],
                "sponsored_count": provider_report["sponsored_count"],
                "sponsored_publication_enabled": provider_report["sponsored_publication_enabled"],
                "expiring_within_30_days": provider_report["expiring_within_30_days"],
                "status_counts": provider_report["status_counts"],
                "provider_source": provider_report["provider_source"],
            },
            "postlaunch": {
                "version": postlaunch_report["version"],
                "reviewed_at": postlaunch_report["reviewed_at"],
                "minimum_words": postlaunch_report["minimum_words"],
                "minimum_h2": postlaunch_report["minimum_h2"],
                "related_link_count": postlaunch_report["related_link_count"],
                "visible_breadcrumbs": postlaunch_report["visible_breadcrumbs"],
                "meta_enhanced": postlaunch_report["meta_enhanced"],
                "provider_policy_visible": postlaunch_report["provider_policy_visible"],
                "focus_visibility_guard": postlaunch_report["focus_visibility_guard"],
                "config_source": postlaunch_report["config_source"],
            },
            "trust": {
                "version": trust_report["version"],
                "reviewed_at": trust_report["reviewed_at"],
                "next_review_due": trust_report["next_review_due"],
                "faq_count": trust_report["faq_count"],
                "minimum_source_count": trust_report["minimum_source_count"],
                "faq_schema_visible_match": trust_report["faq_schema_visible_match"],
                "external_clinical_review_completed": trust_report["external_clinical_review_completed"],
                "config_source": trust_report["config_source"],
            },
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
