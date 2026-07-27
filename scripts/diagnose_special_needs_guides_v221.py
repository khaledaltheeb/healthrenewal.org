from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for candidate in (str(ROOT), str(SCRIPTS)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import publish_new_special_needs_conditions_v323 as conditions323
import publish_special_needs_guides_v217 as guides
import publish_special_needs_guides_v217_core as core

CONTRACT = 221
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
REPORT = SITE / "api" / "special-needs-guides-progress-v221.json"
STATE: dict[str, Any] = {
    "status": "starting",
    "stage": "initialization",
    "last_batch_started": None,
    "last_batch_completed": None,
    "last_page_started": None,
    "last_page_completed": None,
}


def stamp(**updates: Any) -> None:
    STATE.update(updates)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        **STATE,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wrap_batch(version: int, publisher: Callable[[Path], dict[str, Any]]) -> Callable[[Path], dict[str, Any]]:
    def wrapped(site: Path) -> dict[str, Any]:
        stamp(status="running", stage="batch-publication", last_batch_started=version)
        try:
            result = publisher(site)
        except Exception as exc:
            stamp(
                status="failed",
                stage="batch-publication",
                last_batch_started=version,
                error_type=type(exc).__name__,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise
        stamp(status="running", stage="batch-publication", last_batch_completed=version)
        return result

    return wrapped


ORIGINAL_VALIDATE_PAGE = core.validate_page
ORIGINAL_VALIDATE_DISCOVERY = core.validate_discovery


def traced_validate_page(site: Path, slug: str, expected_title: str) -> dict[str, Any]:
    stamp(status="running", stage="page-validation", last_page_started=slug)
    try:
        result = ORIGINAL_VALIDATE_PAGE(site, slug, expected_title)
    except Exception as exc:
        stamp(
            status="failed",
            stage="page-validation",
            last_page_started=slug,
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise
    stamp(status="running", stage="page-validation", last_page_completed=slug)
    return result


def traced_validate_discovery(site: Path, slugs: list[str]) -> dict[str, Any]:
    stamp(status="running", stage="discovery-validation")
    try:
        result = ORIGINAL_VALIDATE_DISCOVERY(site, slugs)
    except Exception as exc:
        stamp(
            status="failed",
            stage="discovery-validation",
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise
    stamp(status="running", stage="discovery-validation-completed")
    return result


def integrate_new_conditions(report: dict[str, Any], conditions_report: dict[str, Any]) -> dict[str, Any]:
    if conditions_report.get("version") != 323 or conditions_report.get("status") != "passed":
        raise SystemExit(f"New special-needs condition contract failed: {conditions_report}")
    if conditions_report.get("condition_slugs") != [
        "rett-syndrome",
        "fragile-x-syndrome",
        "angelman-syndrome",
    ]:
        raise SystemExit("New special-needs condition routes are incomplete")
    if conditions_report.get("condition_count") != 3 or conditions_report.get("section_count") != 21:
        raise SystemExit("New special-needs condition depth contract failed")
    if conditions_report.get("minimum_condition_words", 0) < 1350:
        raise SystemExit("New special-needs condition pages are too shallow")
    if conditions_report.get("external_clinical_review_completed") is not False:
        raise SystemExit("New special-needs condition pages overstate external review")
    if not conditions_report.get("hub_link_added") or not conditions_report.get("sitemap_registered"):
        raise SystemExit("New special-needs condition discovery contract failed")

    condition_hubs = report.setdefault("condition_hubs", {})
    condition_hubs["new_genetic_developmental_conditions"] = {
        key: conditions_report[key]
        for key in (
            "version",
            "status",
            "cluster_slug",
            "condition_count",
            "condition_slugs",
            "generated_pages",
            "source_count",
            "section_count",
            "faq_count",
            "minimum_condition_words",
            "hub_link_added",
            "sitemap_registered",
            "reviewed_at",
            "next_review_due",
            "external_clinical_review_completed",
            "content_source",
        )
    }
    report["new_condition_guides_contract"] = 323
    report["additional_condition_page_count"] = conditions_report["condition_count"]
    api = SITE / "api"
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    (api / "special-needs-guides-v217.json").write_text(payload, encoding="utf-8")
    (api / "special-needs-guides-v221.json").write_text(payload, encoding="utf-8")
    return report


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site directory: {SITE}")

    core.BATCHES = tuple(
        (version, wrap_batch(version, publisher), manifest_path)
        for version, publisher, manifest_path in core.BATCHES
    )
    core.validate_page = traced_validate_page
    core.validate_discovery = traced_validate_discovery

    original_batch214 = guides.batch214.publish
    guides.batch214.publish = wrap_batch(214, original_batch214)

    stamp(status="running", stage="publisher-start")
    try:
        report = guides.publish(SITE)
        stamp(status="running", stage="new-condition-publication", last_batch_started=323)
        conditions_report = conditions323.publish(SITE)
        report = integrate_new_conditions(report, conditions_report)
        stamp(status="running", stage="new-condition-publication-completed", last_batch_completed=323)
    except BaseException as exc:
        if STATE.get("status") != "failed":
            stamp(
                status="failed",
                error_type=type(exc).__name__,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
        raise
    finally:
        guides.batch214.publish = original_batch214

    stamp(
        status="passed",
        stage="completed",
        guide_count=report.get("guide_count"),
        batch_count=report.get("batch_count"),
        production_source_file_count=report.get("production_source_file_count"),
        additional_condition_page_count=report.get("additional_condition_page_count"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
