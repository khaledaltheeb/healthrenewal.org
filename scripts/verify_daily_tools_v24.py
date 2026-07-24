from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import verify_daily_tools_v24_core as _core
from scripts.verify_daily_tools_v24_core import *  # noqa: F401,F403
from scripts.publish_verified_public_api_v220 import verify_and_expand_sections

API_SECTION_CONTRACT = 220
SITE = _core.SITE


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def synchronize_reports(site: Path, section_report: dict) -> None:
    build_report = ROOT / ".build" / "reports" / "verified-public-api-v220.json"
    if build_report.is_file():
        payload = json.loads(build_report.read_text(encoding="utf-8"))
        payload.update(
            {
                "sections": section_report["sections"],
                "verified_routes": section_report["verified_routes"],
                "all_routes_verified": section_report["all_routes_verified"],
                "final_section_refresh_after_daily_tools": True,
            }
        )
        write_json(build_report, payload)

    health_report = site / "api" / "health-publication-gate-v192.json"
    if health_report.is_file():
        payload = json.loads(health_report.read_text(encoding="utf-8"))
        payload.update(
            {
                "public_api_contract": API_SECTION_CONTRACT,
                "public_api_sections": section_report["sections"],
                "public_api_routes_verified": section_report["all_routes_verified"],
                "public_api_refreshed_after_daily_tools": True,
            }
        )
        write_json(health_report, payload)


def main() -> None:
    _core.SITE = SITE
    _core.main()
    site = SITE
    sections_path = site / "api" / "v1" / "sections.json" if site else None
    if not site or not sections_path or not sections_path.is_file():
        print(
            json.dumps(
                {
                    "api_section_contract": API_SECTION_CONTRACT,
                    "api_sections_refreshed": False,
                    "reason": "API fixture is not present in this validation path",
                },
                ensure_ascii=False,
            )
        )
        return
    report = verify_and_expand_sections(site)
    synchronize_reports(site, report)
    print(
        json.dumps(
            {
                "api_section_contract": API_SECTION_CONTRACT,
                "api_sections_refreshed": True,
                "sections": report["sections"],
                "optional_sections_added": report["optional_sections_added"],
                "all_routes_verified": report["all_routes_verified"],
                "reports_synchronized": True,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
