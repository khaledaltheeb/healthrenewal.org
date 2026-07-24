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
    print(
        json.dumps(
            {
                "api_section_contract": API_SECTION_CONTRACT,
                "api_sections_refreshed": True,
                "sections": report["sections"],
                "optional_sections_added": report["optional_sections_added"],
                "all_routes_verified": report["all_routes_verified"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
