from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import enforce_health_publication_gate_v192_core as _core
from scripts.enforce_health_publication_gate_v192_core import *  # noqa: F401,F403
from scripts.publish_verified_public_api_v220 import publish_verified

PUBLIC_API_CONTRACT = 220
SITE = _core.SITE


def enforce() -> dict:
    _core.SITE = SITE
    return _core.enforce()


def main() -> None:
    report = enforce()
    api_report = publish_verified(SITE)
    report.update(
        {
            "public_api_contract": PUBLIC_API_CONTRACT,
            "public_api_published": True,
            "public_api_routes_verified": api_report["all_routes_verified"],
            "public_api_sections": api_report["sections"],
            "authorized_course_sources": api_report["approved_sources"],
            "authorized_courses": api_report["courses"],
            "course_import_policy": api_report["permission_policy"],
        }
    )
    report_path = SITE / "api" / "health-publication-gate-v192.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
