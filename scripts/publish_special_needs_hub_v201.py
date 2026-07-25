#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import publish_special_needs_guides_v217 as institutional


EXPECTED_GUIDES = 25
EXPECTED_SOURCES = 10
EXPECTED_JORDAN_SOURCES = 3


def validate_report(report: dict[str, Any]) -> None:
    required = {
        "version": 221,
        "status": "passed",
        "production_status": "integrated",
        "guide_count": EXPECTED_GUIDES,
        "batch_count": 5,
        "hub_contract": 235,
        "hub_release": 241,
        "external_review_completed": False,
    }
    for key, expected in required.items():
        if report.get(key) != expected:
            raise SystemExit(
                f"Institutional special-needs production bridge failed: {key}={report.get(key)!r}, expected={expected!r}"
            )

    hub = report.get("hub")
    if not isinstance(hub, dict):
        raise SystemExit("Institutional special-needs hub report is missing")
    for key, expected in {
        "status": "production-integrated",
        "pathway_count": 8,
        "faq_count": 8,
        "source_count": EXPECTED_SOURCES,
        "jordan_source_count": EXPECTED_JORDAN_SOURCES,
        "jordan_context_section": True,
        "asha_aac_source_updated": True,
    }.items():
        if hub.get(key) != expected:
            raise SystemExit(
                f"Institutional special-needs hub bridge failed: {key}={hub.get(key)!r}, expected={expected!r}"
            )


def publish(site: Path) -> Path:
    site = site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")

    report = institutional.publish(site)
    validate_report(report)

    output = site / "special-needs" / "index.html"
    if not output.is_file():
        raise SystemExit("Institutional special-needs publisher did not create the hub")
    source = output.read_text(encoding="utf-8")
    for marker in (
        "pathway-communication",
        "data-special-needs-jordan-context-v241",
        "مصفوفة قرار سريعة",
        "معايير جودة الخطة أو الخدمة",
        "prefers-reduced-motion",
        "@media print",
    ):
        if marker not in source:
            raise SystemExit(f"Institutional special-needs hub is missing production marker: {marker}")

    compatibility = {
        "version": 201,
        "status": "production-integrated",
        "superseded_by": 243,
        "hub_contract": 235,
        "hub_release": 241,
        "pathways": report["hub"]["pathway_count"],
        "existing_resources": report["guide_count"],
        "review_status": report["review_status"],
        "external_review": report["external_review"],
        "source_count": report["hub"]["source_count"],
        "jordan_source_count": report["hub"]["jordan_source_count"],
        "guide_count": report["guide_count"],
        "output": "special-needs/index.html",
        "institutional_report": "api/special-needs-guides-v221.json",
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-hub-v201.json").write_text(
        json.dumps(compatibility, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    output = publish(args.site)
    print(
        json.dumps(
            {
                "status": "production-integrated",
                "superseded_by": 243,
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
