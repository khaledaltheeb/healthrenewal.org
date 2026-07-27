from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for candidate in (str(ROOT), str(SCRIPTS)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import publish_mowat_wilson_kleefstra_v326 as conditions326
import publish_new_special_needs_conditions_v323 as conditions323
import publish_phelan_mcdermid_satb2_v327 as conditions327
import publish_smith_magenis_pitt_hopkins_v325 as conditions325
import publish_special_needs_guides_v217 as guides
import publish_special_needs_guides_v217_core as core
import publish_williams_prader_willi_v324 as conditions324

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


def write_central_reports(report: dict[str, Any]) -> None:
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    (api / "special-needs-guides-v217.json").write_text(payload, encoding="utf-8")
    (api / "special-needs-guides-v221.json").write_text(payload, encoding="utf-8")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _copy_fields(payload: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    missing = [key for key in keys if key not in payload]
    _require(not missing, f"Condition report is missing required fields: {missing}")
    return {key: payload[key] for key in keys}


def _require_discovery(payload: dict[str, Any], *keys: str) -> None:
    _require(all(payload.get(key) for key in keys), "Condition discovery contract failed")


def _require_honest_review(payload: dict[str, Any], label: str) -> None:
    _require(
        payload.get("external_clinical_review_completed") is False,
        f"{label} pages overstate external review",
    )


def _expansion_fields() -> tuple[str, ...]:
    return (
        "version",
        "status",
        "cluster_slug",
        "previous_condition_count",
        "added_condition_count",
        "total_condition_count",
        "added_condition_slugs",
        "all_condition_slugs",
        "generated_pages",
        "source_count",
        "section_count",
        "faq_count",
        "minimum_condition_words",
        "cluster_expanded",
        "hub_link_updated",
        "sitemap_registered",
        "reviewed_at",
        "next_review_due",
        "external_clinical_review_completed",
        "content_source",
    )


def integrate_new_conditions(report: dict[str, Any], conditions_report: dict[str, Any]) -> dict[str, Any]:
    expected = ["rett-syndrome", "fragile-x-syndrome", "angelman-syndrome"]
    _require(
        conditions_report.get("version") == 323 and conditions_report.get("status") == "passed",
        f"New special-needs condition contract failed: {conditions_report}",
    )
    _require(conditions_report.get("condition_slugs") == expected, "New special-needs condition routes are incomplete")
    _require(
        conditions_report.get("condition_count") == 3 and conditions_report.get("section_count") == 21,
        "New special-needs condition depth contract failed",
    )
    _require(conditions_report.get("minimum_condition_words", 0) >= 1350, "New special-needs condition pages are too shallow")
    _require_honest_review(conditions_report, "New special-needs condition")
    _require_discovery(conditions_report, "hub_link_added", "sitemap_registered")

    fields = (
        "version", "status", "cluster_slug", "condition_count", "condition_slugs",
        "generated_pages", "source_count", "section_count", "faq_count",
        "minimum_condition_words", "hub_link_added", "sitemap_registered",
        "reviewed_at", "next_review_due", "external_clinical_review_completed",
        "content_source",
    )
    report.setdefault("condition_hubs", {})["new_genetic_developmental_conditions"] = _copy_fields(
        conditions_report, fields
    )
    report["new_condition_guides_contract"] = 323
    report["additional_condition_page_count"] = 3
    report["total_new_condition_page_count"] = 3
    write_central_reports(report)
    return report


def integrate_extended_conditions(report: dict[str, Any], conditions_report: dict[str, Any]) -> dict[str, Any]:
    expected = ["williams-syndrome", "prader-willi-syndrome"]
    _require(
        conditions_report.get("version") == 324 and conditions_report.get("status") == "passed",
        f"Williams and Prader-Willi contract failed: {conditions_report}",
    )
    _require(conditions_report.get("added_condition_slugs") == expected, "Williams and Prader-Willi routes are incomplete")
    _require(
        conditions_report.get("base_condition_count") == 3
        and conditions_report.get("added_condition_count") == 2
        and conditions_report.get("total_condition_count") == 5
        and conditions_report.get("section_count") == 14,
        "Williams and Prader-Willi depth or count contract failed",
    )
    _require(conditions_report.get("minimum_condition_words", 0) >= 1400, "Williams or Prader-Willi page is too shallow")
    _require_honest_review(conditions_report, "Williams or Prader-Willi")
    _require_discovery(conditions_report, "cluster_expanded", "hub_link_updated", "sitemap_registered")

    fields = (
        "version", "status", "cluster_slug", "base_condition_count",
        "added_condition_count", "total_condition_count", "added_condition_slugs",
        "all_condition_slugs", "generated_pages", "source_count", "section_count",
        "faq_count", "minimum_condition_words", "cluster_expanded",
        "hub_link_updated", "sitemap_registered", "reviewed_at", "next_review_due",
        "external_clinical_review_completed", "content_source",
    )
    report.setdefault("condition_hubs", {})["williams_prader_willi_expansion"] = _copy_fields(
        conditions_report, fields
    )
    report["expanded_condition_guides_contract"] = 324
    report["second_condition_batch_page_count"] = 2
    report["total_new_condition_page_count"] = 5
    write_central_reports(report)
    return report


def integrate_third_conditions(report: dict[str, Any], conditions_report: dict[str, Any]) -> dict[str, Any]:
    expected = ["smith-magenis-syndrome", "pitt-hopkins-syndrome"]
    _require(
        conditions_report.get("version") == 325 and conditions_report.get("status") == "passed",
        f"Smith-Magenis and Pitt-Hopkins contract failed: {conditions_report}",
    )
    _require(conditions_report.get("added_condition_slugs") == expected, "Smith-Magenis and Pitt-Hopkins routes are incomplete")
    _require(
        conditions_report.get("previous_condition_count") == 5
        and conditions_report.get("added_condition_count") == 2
        and conditions_report.get("total_condition_count") == 7
        and conditions_report.get("section_count") == 14
        and conditions_report.get("source_count") == 14,
        "Smith-Magenis and Pitt-Hopkins depth or count contract failed",
    )
    _require(conditions_report.get("minimum_condition_words", 0) >= 1550, "Smith-Magenis or Pitt-Hopkins page is too shallow")
    _require_honest_review(conditions_report, "Smith-Magenis or Pitt-Hopkins")
    _require_discovery(conditions_report, "cluster_expanded", "hub_link_updated", "sitemap_registered")

    report.setdefault("condition_hubs", {})["smith_magenis_pitt_hopkins_expansion"] = _copy_fields(
        conditions_report, _expansion_fields()
    )
    report["third_condition_guides_contract"] = 325
    report["third_condition_batch_page_count"] = 2
    report["total_new_condition_page_count"] = 7
    write_central_reports(report)
    return report


def integrate_fourth_conditions(report: dict[str, Any], conditions_report: dict[str, Any]) -> dict[str, Any]:
    expected = ["mowat-wilson-syndrome", "kleefstra-syndrome"]
    _require(
        conditions_report.get("version") == 326 and conditions_report.get("status") == "passed",
        f"Mowat-Wilson and Kleefstra contract failed: {conditions_report}",
    )
    _require(conditions_report.get("added_condition_slugs") == expected, "Mowat-Wilson and Kleefstra routes are incomplete")
    _require(
        conditions_report.get("previous_condition_count") == 7
        and conditions_report.get("added_condition_count") == 2
        and conditions_report.get("total_condition_count") == 9
        and conditions_report.get("section_count") == 14
        and conditions_report.get("source_count") == 14,
        "Mowat-Wilson and Kleefstra depth or count contract failed",
    )
    _require(conditions_report.get("minimum_condition_words", 0) >= 1650, "Mowat-Wilson or Kleefstra page is too shallow")
    _require_honest_review(conditions_report, "Mowat-Wilson or Kleefstra")
    _require_discovery(conditions_report, "cluster_expanded", "hub_link_updated", "sitemap_registered")

    report.setdefault("condition_hubs", {})["mowat_wilson_kleefstra_expansion"] = _copy_fields(
        conditions_report, _expansion_fields()
    )
    report["fourth_condition_guides_contract"] = 326
    report["fourth_condition_batch_page_count"] = 2
    report["total_new_condition_page_count"] = 9
    write_central_reports(report)
    return report


def integrate_fifth_conditions(report: dict[str, Any], conditions_report: dict[str, Any]) -> dict[str, Any]:
    expected = ["phelan-mcdermid-syndrome", "satb2-associated-syndrome"]
    _require(
        conditions_report.get("version") == 327 and conditions_report.get("status") == "passed",
        f"Phelan-McDermid and SATB2-associated contract failed: {conditions_report}",
    )
    _require(
        conditions_report.get("added_condition_slugs") == expected,
        "Phelan-McDermid and SATB2-associated routes are incomplete",
    )
    _require(
        conditions_report.get("previous_condition_count") == 9
        and conditions_report.get("added_condition_count") == 2
        and conditions_report.get("total_condition_count") == 11
        and conditions_report.get("section_count") == 14
        and conditions_report.get("source_count") == 14,
        "Phelan-McDermid and SATB2-associated depth or count contract failed",
    )
    _require(
        conditions_report.get("minimum_condition_words", 0) >= 1750,
        "Phelan-McDermid or SATB2-associated page is too shallow",
    )
    _require_honest_review(conditions_report, "Phelan-McDermid or SATB2-associated")
    _require_discovery(conditions_report, "cluster_expanded", "hub_link_updated", "sitemap_registered")

    report.setdefault("condition_hubs", {})["phelan_mcdermid_satb2_expansion"] = _copy_fields(
        conditions_report, _expansion_fields()
    )
    report["fifth_condition_guides_contract"] = 327
    report["fifth_condition_batch_page_count"] = 2
    report["total_new_condition_page_count"] = 11
    write_central_reports(report)
    return report


def _publish_layer(
    report: dict[str, Any],
    version: int,
    stage: str,
    publisher: Callable[[Path], dict[str, Any]],
    integrator: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    stamp(status="running", stage=stage, last_batch_started=version)
    layer_report = publisher(SITE)
    report = integrator(report, layer_report)
    stamp(status="running", stage=f"{stage}-completed", last_batch_completed=version)
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
        report = _publish_layer(report, 323, "new-condition-publication", conditions323.publish, integrate_new_conditions)
        report = _publish_layer(report, 324, "condition-expansion-publication", conditions324.publish, integrate_extended_conditions)
        report = _publish_layer(report, 325, "third-condition-expansion", conditions325.publish, integrate_third_conditions)
        report = _publish_layer(report, 326, "fourth-condition-expansion", conditions326.publish, integrate_fourth_conditions)
        report = _publish_layer(report, 327, "fifth-condition-expansion", conditions327.publish, integrate_fifth_conditions)
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
        second_condition_batch_page_count=report.get("second_condition_batch_page_count"),
        third_condition_batch_page_count=report.get("third_condition_batch_page_count"),
        fourth_condition_batch_page_count=report.get("fourth_condition_batch_page_count"),
        fifth_condition_batch_page_count=report.get("fifth_condition_batch_page_count"),
        total_new_condition_page_count=report.get("total_new_condition_page_count"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
