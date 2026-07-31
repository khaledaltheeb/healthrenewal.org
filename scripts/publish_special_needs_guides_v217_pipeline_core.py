#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import audit_special_needs_condition_sources_v310 as source310
import publish_autism_lived_experience_guides_v322 as autism322
import publish_special_needs_condition_age_guides_v314 as age314
import publish_special_needs_condition_hubs_v302 as condition302
import publish_special_needs_condition_postlaunch_v305 as postlaunch305
import publish_special_needs_condition_trust_v307 as trust307
import publish_special_needs_diagnostic_decision_guides_v316 as decision316
import publish_special_needs_guides_v214 as batch214
import publish_special_needs_guides_v217_core as core
import publish_special_needs_hub_v235_compat as hub235
import publish_special_needs_regression_coexisting_v320 as regression320
import publish_special_needs_support_interventions_v318 as support318
import validate_special_needs_provider_directory_v308 as provider308

ROOT = Path(__file__).resolve().parents[1]
V214_MANIFEST = ROOT / "content" / "v214" / "special-needs-guides-manifest-ar.json"
PRODUCTION_MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"
VERSIONS = (209, 210, 211, 212, 214)
CONDITION_SLUGS = (
    "autism",
    "down-syndrome",
    "autism-signs-by-age",
    "down-syndrome-health-by-age",
    "autism-screening-vs-diagnosis",
    "down-syndrome-prenatal-screening-vs-diagnosis",
    "autism-evidence-based-support-plan",
    "down-syndrome-development-communication-independence",
    "autism-coexisting-conditions-sudden-change",
    "down-syndrome-regression-dementia-urgent-changes",
    "autism-sensory-profile-overload",
    "autism-communication-stimming-neurodiversity",
)
CONDITION_URLS = {f"{condition302.BASE}/special-needs/{slug}/" for slug in CONDITION_SLUGS}
CONDITION_API_FILES = (
    "special-needs-condition-hubs-v302.json",
    "special-needs-condition-postlaunch-v305.json",
    "special-needs-condition-trust-v307.json",
    "special-needs-provider-governance-v308.json",
    "special-needs-condition-source-maintenance-v310.json",
    "special-needs-condition-age-guides-v314.json",
    "special-needs-diagnostic-decision-guides-v316.json",
    "special-needs-support-interventions-v318.json",
    "special-needs-regression-coexisting-v320.json",
    "autism-lived-experience-guides-v322.json",
)


def summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": report["version"],
        "status": report["status"],
        "guide_count": report["guide_count"],
        "minimum_source_words": report["minimum_source_words"],
        "source_count": report["source_count"],
    }


def pick(report: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: report[key] for key in keys}


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
    for slug in CONDITION_SLUGS:
        shutil.rmtree(site / "special-needs" / slug, ignore_errors=True)
    for name in CONDITION_API_FILES:
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


def validate_condition_layers(
    source_report: dict[str, Any],
    provider_report: dict[str, Any],
    condition_report: dict[str, Any],
    age_report: dict[str, Any],
    decision_report: dict[str, Any],
    support_report: dict[str, Any],
    regression_report: dict[str, Any],
    autism_report: dict[str, Any],
    postlaunch_report: dict[str, Any],
    trust_report: dict[str, Any],
) -> None:
    if source_report.get("version") != 310 or source_report.get("status") != "passed":
        raise SystemExit(f"Condition source maintenance contract failed: {source_report}")
    if source_report.get("condition_slugs") != ["autism", "down-syndrome"]:
        raise SystemExit("Source maintenance must cover both condition pages")
    if source_report.get("source_count") != 17 or source_report.get("condition_count") != 2:
        raise SystemExit("Source maintenance must cover all seventeen condition references")

    if provider_report.get("version") != 308 or provider_report.get("status") != "passed":
        raise SystemExit(f"Provider directory governance contract failed: {provider_report}")
    if provider_report.get("sponsored_publication_enabled") is not False:
        raise SystemExit("Sponsored provider publishing must remain disabled until visible disclosure rendering exists")

    if condition_report.get("version") != 302 or condition_report.get("condition_count") != 2:
        raise SystemExit(f"Special-needs condition hub contract failed: {condition_report}")
    if condition_report.get("condition_slugs") != ["autism", "down-syndrome"]:
        raise SystemExit("Autism and Down syndrome routes are required")
    if condition_report.get("generated_page_count") != 2 or condition_report.get("source_count", 0) < 15:
        raise SystemExit("Scientific condition page depth contract failed")
    if condition_report.get("source_count") != source_report.get("source_count"):
        raise SystemExit("Rendered condition source count must match the maintenance audit")
    rendered_total = sum(condition_report.get("provider_counts", {}).values())
    published_records = provider_report.get("published_count", 0)
    if rendered_total != condition_report.get("published_provider_count"):
        raise SystemExit("Rendered provider counts are internally inconsistent")
    if not (published_records <= rendered_total <= published_records * 2):
        raise SystemExit(
            "Published provider records do not match one-or-two condition page appearances: "
            f"records={published_records}, appearances={rendered_total}"
        )

    if age_report.get("version") != 314 or age_report.get("status") != "passed":
        raise SystemExit(f"Condition age-guide contract failed: {age_report}")
    if age_report.get("guide_slugs") != ["autism-signs-by-age", "down-syndrome-health-by-age"]:
        raise SystemExit("Condition age-guide routes are incomplete")
    if age_report.get("guide_count") != 2 or age_report.get("stage_count") != 8:
        raise SystemExit("Condition age guides must publish two pages and eight age stages")
    if age_report.get("source_count") != 7 or age_report.get("parent_links_added") != 2:
        raise SystemExit("Condition age-guide evidence or parent-link contract failed")

    if decision_report.get("version") != 316 or decision_report.get("status") != "passed":
        raise SystemExit(f"Diagnostic decision-guide contract failed: {decision_report}")
    if decision_report.get("guide_slugs") != [
        "autism-screening-vs-diagnosis",
        "down-syndrome-prenatal-screening-vs-diagnosis",
    ]:
        raise SystemExit("Diagnostic decision-guide routes are incomplete")
    if decision_report.get("guide_count") != 2 or decision_report.get("section_count") != 10:
        raise SystemExit("Diagnostic decision guides must publish two pages and ten decision sections")
    if decision_report.get("source_count") != 8 or decision_report.get("parent_links_added") != 2:
        raise SystemExit("Diagnostic decision-guide evidence or parent-link contract failed")

    if support_report.get("version") != 318 or support_report.get("status") != "passed":
        raise SystemExit(f"Support intervention-guide contract failed: {support_report}")
    if support_report.get("guide_slugs") != [
        "autism-evidence-based-support-plan",
        "down-syndrome-development-communication-independence",
    ]:
        raise SystemExit("Support intervention-guide routes are incomplete")
    if support_report.get("guide_count") != 2 or support_report.get("section_count") != 10:
        raise SystemExit("Support intervention guides must publish two pages and ten support sections")
    if support_report.get("source_count") != 9 or support_report.get("parent_links_added") != 2:
        raise SystemExit("Support intervention-guide evidence or parent-link contract failed")
    if support_report.get("plan_step_count") != 10 or support_report.get("urgent_item_count") != 6:
        raise SystemExit("Support intervention plan or safety depth failed")

    if regression_report.get("version") != 320 or regression_report.get("status") != "passed":
        raise SystemExit(f"Regression/coexisting guide contract failed: {regression_report}")
    if regression_report.get("guide_slugs") != [
        "autism-coexisting-conditions-sudden-change",
        "down-syndrome-regression-dementia-urgent-changes",
    ]:
        raise SystemExit("Regression/coexisting routes are incomplete")
    if regression_report.get("guide_count") != 2 or regression_report.get("section_count") != 10:
        raise SystemExit("Regression/coexisting guides must publish two pages and ten sections")
    if regression_report.get("source_count") != 11 or regression_report.get("parent_links_added") != 2:
        raise SystemExit("Regression/coexisting evidence or parent-link contract failed")
    if regression_report.get("action_step_count") != 10 or regression_report.get("urgent_item_count") != 6:
        raise SystemExit("Regression/coexisting action or urgent-depth contract failed")
    if not all(
        regression_report.get(key) is True
        for key in ("dsrd_consensus_limit_visible", "dementia_baseline_limit_visible", "diagnostic_overshadowing_guard")
    ):
        raise SystemExit("Regression/coexisting clinical-boundary controls are incomplete")

    if autism_report.get("version") != 322 or autism_report.get("status") != "passed":
        raise SystemExit(f"Autism lived-experience guide contract failed: {autism_report}")
    if autism_report.get("guide_slugs") != [
        "autism-sensory-profile-overload",
        "autism-communication-stimming-neurodiversity",
    ]:
        raise SystemExit("Autism lived-experience routes are incomplete")
    if autism_report.get("guide_count") != 2 or autism_report.get("section_count") != 10:
        raise SystemExit("Autism lived-experience guides must publish two pages and ten sections")
    if autism_report.get("source_count") != 11 or autism_report.get("practical_resource_count") != 4:
        raise SystemExit("Autism lived-experience evidence or practical-resource depth failed")
    if autism_report.get("action_step_count") != 10 or autism_report.get("urgent_item_count") != 6:
        raise SystemExit("Autism lived-experience action or urgent-depth contract failed")
    if autism_report.get("parent_links_added") != 2:
        raise SystemExit("Autism lived-experience parent-link contract failed")
    if not all(
        autism_report.get(key) is True
        for key in ("national_autistic_society_resource_used", "content_rewritten_not_copied")
    ):
        raise SystemExit("Autism source attribution or rewrite contract failed")

    for report, label in (
        (age_report, "age guides"),
        (decision_report, "diagnostic decision guides"),
        (support_report, "support intervention guides"),
        (regression_report, "regression/coexisting guides"),
        (autism_report, "autism lived-experience guides"),
    ):
        if report.get("external_clinical_review_completed") is not False:
            raise SystemExit(f"{label} must not overstate external clinical review")
        if report.get("sitemap_registered") is not True:
            raise SystemExit(f"{label} routes must be registered in the special-needs sitemap")

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

    if trust_report.get("version") != 307 or trust_report.get("status") != "passed":
        raise SystemExit(f"Condition trust and FAQ contract failed: {trust_report}")
    if trust_report.get("condition_slugs") != ["autism", "down-syndrome"] or trust_report.get("faq_count") != 8:
        raise SystemExit("Trust layer must publish four referenced FAQs for each condition")
    if trust_report.get("faq_schema_visible_match") is not True:
        raise SystemExit("Visible FAQ content and FAQPage structured data must match")
    if trust_report.get("external_clinical_review_completed") is not False:
        raise SystemExit("Trust layer must not overstate external clinical review")


def publish(site: Path) -> dict[str, Any]:
    reset_condition_outputs(site)
    production_manifest = load_production_manifest()

    hub_report = hub235.publish(site)
    if hub_report.get("version") != 235 or hub_report.get("guide_count") != 25:
        raise SystemExit(f"Institutional special-needs hub contract failed: {hub_report}")
    if hub_report.get("source_count") != 10 or hub_report.get("jordan_source_count") != 3:
        raise SystemExit(f"Institutional special-needs source contract failed: {hub_report}")
    if hub_report.get("jordan_context_section") is not True or hub_report.get("asha_aac_source_updated") is not True:
        raise SystemExit("Institutional Jordan or AAC source contract failed")

    base = core.publish(site)
    manifest = core.read_manifest(V214_MANIFEST, 214)
    titles: dict[str, str] = {}
    for slug in manifest["guide_slugs"]:
        guide_path = V214_MANIFEST.parent / "special-needs-guides" / f"{slug}.json"
        titles[slug] = json.loads(guide_path.read_text(encoding="utf-8"))["title"]

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

    source_report = source310.publish(site)
    provider_report = provider308.publish(site)
    condition_report = condition302.publish(site)
    age_report = age314.publish(site)
    decision_report = decision316.publish(site)
    support_report = support318.publish(site)
    regression_report = regression320.publish(site)
    autism_report = autism322.publish(site)
    postlaunch_report = postlaunch305.publish(site)
    trust_report = trust307.publish(site)

    validate_condition_layers(
        source_report,
        provider_report,
        condition_report,
        age_report,
        decision_report,
        support_report,
        regression_report,
        autism_report,
        postlaunch_report,
        trust_report,
    )

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
        "condition_source_maintenance_contract": 310,
        "condition_age_guides_contract": 314,
        "diagnostic_decision_guides_contract": 316,
        "support_intervention_guides_contract": 318,
        "regression_coexisting_guides_contract": 320,
        "autism_lived_experience_guides_contract": 322,
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
            **pick(
                hub_report,
                "status",
                "pathway_count",
                "faq_count",
                "source_count",
                "jordan_source_count",
                "jordan_context_section",
                "asha_aac_source_updated",
                "seo",
                "accessibility",
            )
        },
        "condition_hubs": {
            **pick(
                condition_report,
                "status",
                "version",
                "condition_count",
                "condition_slugs",
                "generated_pages",
                "source_count",
                "provider_source",
                "published_provider_count",
                "sitemap_registered",
            ),
            "age_guides": pick(
                age_report,
                "version",
                "status",
                "guide_count",
                "guide_slugs",
                "generated_pages",
                "stage_count",
                "source_count",
                "urgent_item_count",
                "parent_links_added",
                "sitemap_registered",
                "reviewed_at",
                "next_review_due",
                "external_clinical_review_completed",
                "content_source",
            ),
            "diagnostic_decision_guides": pick(
                decision_report,
                "version",
                "status",
                "guide_count",
                "guide_slugs",
                "generated_pages",
                "section_count",
                "source_count",
                "decision_step_count",
                "urgent_item_count",
                "parent_links_added",
                "sitemap_registered",
                "reviewed_at",
                "next_review_due",
                "external_clinical_review_completed",
                "content_source",
            ),
            "support_interventions": pick(
                support_report,
                "version",
                "status",
                "guide_count",
                "guide_slugs",
                "generated_pages",
                "section_count",
                "source_count",
                "plan_step_count",
                "urgent_item_count",
                "parent_links_added",
                "sitemap_registered",
                "reviewed_at",
                "next_review_due",
                "external_clinical_review_completed",
                "content_source",
            ),
            "regression_coexisting": pick(
                regression_report,
                "version",
                "status",
                "guide_count",
                "guide_slugs",
                "generated_pages",
                "section_count",
                "source_count",
                "action_step_count",
                "urgent_item_count",
                "parent_links_added",
                "sitemap_registered",
                "dsrd_consensus_limit_visible",
                "dementia_baseline_limit_visible",
                "diagnostic_overshadowing_guard",
                "reviewed_at",
                "next_review_due",
                "external_clinical_review_completed",
                "content_source",
            ),
            "autism_lived_experience": pick(
                autism_report,
                "version",
                "status",
                "guide_count",
                "guide_slugs",
                "generated_pages",
                "section_count",
                "source_count",
                "practical_resource_count",
                "action_step_count",
                "urgent_item_count",
                "parent_links_added",
                "sitemap_registered",
                "national_autistic_society_resource_used",
                "content_rewritten_not_copied",
                "reviewed_at",
                "next_review_due",
                "external_clinical_review_completed",
                "content_source",
            ),
            "source_maintenance": pick(
                source_report,
                "version",
                "checked_at",
                "review_interval_days",
                "maximum_allowed_review_age_days",
                "source_count",
                "distinct_host_count",
                "overdue_source_count",
                "due_within_30_days_count",
            ),
            "provider_governance": pick(
                provider_report,
                "version",
                "checked_at",
                "record_count",
                "published_count",
                "sponsored_count",
                "sponsored_publication_enabled",
                "expiring_within_30_days",
                "status_counts",
                "provider_source",
            ),
            "postlaunch": pick(
                postlaunch_report,
                "version",
                "reviewed_at",
                "minimum_words",
                "minimum_h2",
                "related_link_count",
                "visible_breadcrumbs",
                "meta_enhanced",
                "provider_policy_visible",
                "focus_visibility_guard",
                "config_source",
            ),
            "trust": pick(
                trust_report,
                "version",
                "reviewed_at",
                "next_review_due",
                "faq_count",
                "minimum_source_count",
                "faq_schema_visible_match",
                "external_clinical_review_completed",
                "config_source",
            ),
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
