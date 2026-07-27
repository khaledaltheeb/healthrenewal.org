#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import publish_autism_clinical_pathways_v324 as clinical324
import publish_special_needs_guides_v217_pipeline_core as pipeline
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


def publish(site: Path) -> dict[str, Any]:
    report = pipeline.publish(site)
    clinical_report = clinical324.publish(site)
    validate_clinical_pathways(clinical_report)

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
