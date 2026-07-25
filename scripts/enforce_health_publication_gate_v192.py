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


def enforce() -> dict:
    _base.SITE = SITE
    report = _base.enforce()
    homepage = SITE / "index.html"
    if not homepage.is_file():
        return report

    header_report = _publish_header(SITE)
    if header_report.get("status") != "passed":
        raise SystemExit(f"Institutional header v233 failed after health gate: {header_report}")

    report = dict(report)
    report["institutional_header_version"] = 233
    report["institutional_header_status"] = "passed"
    report["institutional_header_section_links"] = header_report["section_links"]
    report["institutional_header_language_links"] = header_report["language_links"]
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
