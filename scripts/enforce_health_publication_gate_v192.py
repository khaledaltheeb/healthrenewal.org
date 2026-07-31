from __future__ import annotations

"""بوابة النشر الصحي الأصلية مع إنهاء الهيدر والأبعاد والبنية الدلالية."""

import json

try:
    from scripts import enforce_health_publication_gate_v192_base as _base
    from scripts.finalize_sector_image_dimensions_v236 import finalize as _finalize_image_dimensions
    from scripts.finalize_semantic_structure_v237 import finalize as _finalize_semantic_structure
    from scripts.publish_institutional_header_v233 import publish as _publish_header
except ModuleNotFoundError:
    import enforce_health_publication_gate_v192_base as _base
    from finalize_sector_image_dimensions_v236 import finalize as _finalize_image_dimensions
    from finalize_semantic_structure_v237 import finalize as _finalize_semantic_structure
    from publish_institutional_header_v233 import publish as _publish_header


for _name in dir(_base):
    if not _name.startswith("_") and _name not in {"enforce", "main"}:
        globals()[_name] = getattr(_base, _name)

SITE = _base.SITE
CARE_GUIDE_ABSOLUTE_LINK = '<a href="/care-guides/">أدلة التعامل</a>'
CARE_GUIDE_RELATIVE_LINK = '<a href="care-guides/">أدلة التعامل</a>'


def ensure_care_guide_link_compatibility(homepage) -> bool:
    """حافظ على عقد ربط الأدلة القديم دون إضافة رابط مرئي جديد."""
    text = homepage.read_text(encoding="utf-8")
    absolute_count = text.count(CARE_GUIDE_ABSOLUTE_LINK)
    relative_count = text.count(CARE_GUIDE_RELATIVE_LINK)
    if absolute_count == 1 and relative_count == 0:
        homepage.write_text(
            text.replace(CARE_GUIDE_ABSOLUTE_LINK, CARE_GUIDE_RELATIVE_LINK, 1),
            encoding="utf-8",
        )
        return True
    if absolute_count == 0 and relative_count == 1:
        return False
    raise SystemExit(
        "Institutional header care-guide link is missing or duplicated: "
        f"absolute={absolute_count}, relative={relative_count}"
    )


def enforce() -> dict:
    _base.SITE = SITE
    report = _base.enforce()
    homepage = SITE / "index.html"
    if not homepage.is_file():
        return report

    header_report = _publish_header(SITE)
    if header_report.get("status") != "passed":
        raise SystemExit(f"Institutional header v233 failed after health gate: {header_report}")
    care_guide_link_normalized = ensure_care_guide_link_compatibility(homepage)

    image_report = _finalize_image_dimensions(SITE)
    if image_report.get("status") != "passed":
        raise SystemExit(f"Sector image dimensions v236 failed after health gate: {image_report}")

    semantic_report = _finalize_semantic_structure(SITE)
    if semantic_report.get("status") != "passed":
        raise SystemExit(f"Semantic structure v237 failed after health gate: {semantic_report}")

    report = dict(report)
    report["institutional_header_version"] = 233
    report["institutional_header_status"] = "passed"
    report["institutional_header_section_links"] = header_report["section_links"]
    report["institutional_header_language_links"] = header_report["language_links"]
    report["institutional_header_care_guide_link"] = "care-guides/"
    report["institutional_header_care_guide_link_compatible"] = True
    report["institutional_header_care_guide_link_normalized"] = care_guide_link_normalized
    report["sector_image_dimensions_version"] = 236
    report["sector_image_dimensions_status"] = "passed"
    report["sector_image_dimensions_target_images"] = image_report["target_images"]
    report["sector_image_dimensions_images_updated"] = image_report["images_updated"]
    report["sector_image_dimensions_remaining"] = image_report["remaining_missing_dimensions"]
    report["semantic_structure_version"] = 237
    report["semantic_structure_status"] = "passed"
    report["semantic_structure_heading_pages_updated"] = semantic_report["heading_pages_updated"]
    report["semantic_structure_heading_tags_updated"] = semantic_report["heading_tags_updated"]
    report["semantic_structure_remaining_heading_jumps"] = semantic_report["remaining_heading_jumps"]
    report["semantic_structure_error_page_jsonld_present"] = semantic_report["error_page_jsonld_present"]
    report_path = SITE / "api" / "health-publication-gate-v192.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    print(json.dumps(enforce(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
