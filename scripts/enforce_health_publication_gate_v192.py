from __future__ import annotations

"""بوابة النشر الصحي الأصلية مع إنهاء الهيدر المؤسسي v233."""

import json

try:
    from scripts import enforce_health_publication_gate_v192_base as _base
    from scripts.publish_institutional_header_v233 import publish as _publish_header
except ModuleNotFoundError:
    import enforce_health_publication_gate_v192_base as _base
    from publish_institutional_header_v233 import publish as _publish_header


for _name in dir(_base):
    if not _name.startswith("_") and _name not in {"enforce", "main"}:
        globals()[_name] = getattr(_base, _name)

SITE = _base.SITE
CARE_GUIDE_ABSOLUTE_LINK = '<a href="/pterminology-site/care-guides/">أدلة التعامل</a>'
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

    report = dict(report)
    report["institutional_header_version"] = 233
    report["institutional_header_status"] = "passed"
    report["institutional_header_section_links"] = header_report["section_links"]
    report["institutional_header_language_links"] = header_report["language_links"]
    report["institutional_header_care_guide_link"] = "care-guides/"
    report["institutional_header_care_guide_link_compatible"] = True
    report["institutional_header_care_guide_link_normalized"] = care_guide_link_normalized
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
