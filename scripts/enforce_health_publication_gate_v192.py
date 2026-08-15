from __future__ import annotations

"""بوابة النشر الصحي الأصلية مع إنهاء الهيدر والأبعاد والبنية الدلالية."""

import json
import xml.etree.ElementTree as ET

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
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def reconcile_care_guide_sitemap() -> dict[str, object]:
    """Make the care-guide sitemap exactly match materialized index routes.

    Earlier publication stages can preserve a URL for a guide that a later
    gated publication stage removes. The health gate must validate the final
    publication surface, so reconcile the generated sitemap from the actual
    care-guide index pages before the strict parity check runs.
    """
    care_root = SITE / "care-guides"
    sitemap_path = SITE / "sitemap-care-guides.xml"
    if not care_root.is_dir() or not sitemap_path.is_file():
        return {
            "status": "skipped",
            "reason": "missing-care-root-or-sitemap",
            "removed_urls": [],
            "added_urls": [],
        }

    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    if root.tag.rsplit("}", 1)[-1] != "urlset":
        raise SystemExit(f"Care-guide sitemap must be a urlset: {sitemap_path.name}")

    actual_urls: list[str] = []
    for page in sorted(care_root.rglob("index.html")):
        relative = page.parent.relative_to(SITE).as_posix().strip("/")
        actual_urls.append(_base.BASE + relative + "/")
    actual_urls = sorted(set(actual_urls))
    actual_set = set(actual_urls)

    present_urls: set[str] = set()
    removed_urls: list[str] = []
    for node in list(root.findall("{*}url")):
        loc = node.find("{*}loc")
        url = (loc.text or "").strip() if loc is not None else ""
        if not url or url not in actual_set or url in present_urls:
            if url:
                removed_urls.append(url)
            root.remove(node)
            continue
        present_urls.add(url)

    added_urls = [url for url in actual_urls if url not in present_urls]
    for url in added_urls:
        node = ET.SubElement(root, f"{{{SITEMAP_NAMESPACE}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NAMESPACE}}}loc").text = url

    if removed_urls or added_urls:
        ET.register_namespace("", SITEMAP_NAMESPACE)
        tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)

    final_urls = [
        (node.find("{*}loc").text or "").strip()
        for node in root.findall("{*}url")
        if node.find("{*}loc") is not None and node.find("{*}loc").text
    ]
    if len(final_urls) != len(actual_urls) or set(final_urls) != actual_set:
        raise SystemExit(
            "Care-guide sitemap reconciliation failed: "
            f"pages={len(actual_urls)}, sitemap_urls={len(final_urls)}"
        )

    return {
        "status": "passed",
        "pages": len(actual_urls),
        "sitemap_urls": len(final_urls),
        "removed_urls": removed_urls,
        "added_urls": added_urls,
    }


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
    sitemap_reconciliation = reconcile_care_guide_sitemap()
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
    report["care_guide_sitemap_reconciliation"] = sitemap_reconciliation
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
