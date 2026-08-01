#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import publish_autism_clinical_pathways_v324 as clinical324
import publish_special_needs_guides_v217_pipeline_core as pipeline
import publish_undercovered_content_v401 as expansion401
from publish_special_needs_guides_v217_pipeline_core import *  # noqa: F401,F403


def validate_clinical_pathways(report: dict[str, Any]) -> None:
    if report.get("version") != 324 or report.get("status") != "passed":
        raise SystemExit(f"Autism clinical pathways v324 contract failed: {report}")
    if report.get("guide_slugs") != list(clinical324.EXPECTED):
        raise SystemExit("Autism clinical pathway routes are incomplete")
    if report.get("guide_count") != 4 or report.get("section_count") != 28:
        raise SystemExit("v324 must publish four guides and twenty-eight sections")
    if report.get("source_count") != 26:
        raise SystemExit("v324 evidence-source count changed unexpectedly")
    if report.get("minimum_guide_words", 0) < 1250:
        raise SystemExit("v324 guide depth is below the production threshold")
    if report.get("action_step_count") != 24 or report.get("urgent_item_count") != 12:
        raise SystemExit("v324 action or urgent-depth contract failed")
    if report.get("parent_links_added") != 4 or report.get("sitemap_registered") is not True:
        raise SystemExit("v324 discovery or sitemap contract failed")
    if report.get("external_clinical_review_completed") is not False:
        raise SystemExit("v324 must not overstate external clinical review")


def validate_undercovered_expansion(report: dict[str, Any]) -> None:
    expected_distribution = {
        "special-needs": 60,
        "learning-paths": 15,
        "child": 10,
        "family": 8,
        "home": 7,
    }
    if report.get("version") != 401 or report.get("status") != "passed":
        raise SystemExit(f"Undercovered content v401 contract failed: {report}")
    if report.get("page_count") != 100 or report.get("unique_routes") != 100:
        raise SystemExit("v401 must publish exactly one hundred unique pages")
    if report.get("distribution") != expected_distribution:
        raise SystemExit(f"v401 distribution changed unexpectedly: {report.get('distribution')}")
    if report.get("minimum_words", 0) < 1200 or report.get("minimum_h2", 0) < 15:
        raise SystemExit("v401 depth or hierarchy is below the production threshold")
    if report.get("minimum_citations", 0) < 3 or report.get("source_count", 0) < 10:
        raise SystemExit("v401 source visibility is below the production threshold")
    if report.get("external_specialist_review_completed") is not False:
        raise SystemExit("v401 must not overstate external specialist review")
    required_gates = {
        "functional_icf_frame",
        "rights_based_frame",
        "professional_limits_visible",
        "urgent_escalation_visible",
        "measurement_and_decision_rules",
        "inclusive_language_gate",
        "external_review_not_overstated",
        "no_client_side_network_runtime",
    }
    gates = report.get("quality_gates", {})
    if not required_gates.issubset(gates) or not all(gates.get(key) is True for key in required_gates):
        raise SystemExit(f"v401 quality gates failed: {gates}")


def reset_clinical_outputs(site: Path) -> None:
    """Remove only generated v324 outputs so repeated central builds start equally."""
    for slug in clinical324.EXPECTED:
        shutil.rmtree(site / "special-needs" / slug, ignore_errors=True)
    (site / "api" / "autism-clinical-pathways-v324.json").unlink(missing_ok=True)

    parent = site / "special-needs" / "autism" / "index.html"
    if parent.is_file():
        source = parent.read_text(encoding="utf-8")
        pattern = rf'<section\b[^>]*{re.escape(clinical324.PARENT_MARKER)}[^>]*>.*?</section>'
        source, count = re.subn(pattern, "", source, count=1, flags=re.I | re.S)
        if count > 1 or source.count(clinical324.PARENT_MARKER):
            raise SystemExit("Unable to reset prior v324 autism parent block")
        parent.write_text(source, encoding="utf-8")

    sitemap = site / "sitemap-special-needs.xml"
    if sitemap.is_file():
        tree = ET.parse(sitemap)
        root = tree.getroot()
        targets = {
            f"{clinical324.BASE}/special-needs/{slug}/"
            for slug in clinical324.EXPECTED
        }
        for row in list(root.findall("{*}url")):
            loc = (row.findtext("{*}loc") or "").strip()
            if loc in targets:
                root.remove(row)
        ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
        ET.indent(tree, space="  ")
        tree.write(sitemap, encoding="utf-8", xml_declaration=True)
        clinical324.normalize_sitemap(sitemap)


def publish(site: Path) -> dict[str, Any]:
    reset_clinical_outputs(site)
    report = pipeline.publish(site)
    clinical_report = clinical324.publish(site)
    validate_clinical_pathways(clinical_report)
    expansion_report = expansion401.publish(site)
    validate_undercovered_expansion(expansion_report)

    report["autism_clinical_pathways_contract"] = 324
    report.setdefault("condition_hubs", {})["autism_clinical_pathways"] = pipeline.pick(
        clinical_report,
        "version",
        "status",
        "guide_count",
        "guide_slugs",
        "generated_pages",
        "minimum_guide_words",
        "total_guide_words",
        "section_count",
        "source_count",
        "action_step_count",
        "urgent_item_count",
        "parent_links_added",
        "sitemap_registered",
        "reviewed_at",
        "next_review_due",
        "external_clinical_review_completed",
        "content_source",
    )
    report["undercovered_content_contract"] = 401
    report["undercovered_content"] = pipeline.pick(
        expansion_report,
        "version",
        "status",
        "page_count",
        "distribution",
        "minimum_words",
        "total_words",
        "minimum_h2",
        "minimum_citations",
        "unique_routes",
        "source_count",
        "hub_counts",
        "sitemap_updates",
        "reviewed_at",
        "next_review_due",
        "external_specialist_review_completed",
        "quality_gates",
    )

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
