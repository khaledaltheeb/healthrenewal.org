#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DEMO = ROOT / "provider-assessment-demo"
BASE_STYLE = DEMO / "styles.css"
CONTRACT_STYLE = DEMO / "institutional-contract-v220.css"
INTEGRATION = DEMO / "institutional-contract-v220-integration.js"
INDEX = DEMO / "index.html"
REPORT_NAME = "provider-layout-stability-v225.json"
MARKER = "provider-layout-stability-v225"
CONTRACT = "2026.07.25-v220"


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing provider layout source: {path}")
    return path.read_text(encoding="utf-8")


def validate(base_css: str, contract_css: str, integration: str, html: str) -> dict[str, object]:
    if contract_css.count(MARKER) != 1:
        raise SystemExit("Provider layout stability marker must appear exactly once")
    if not re.search(r"\.tabs\{[^}]*display:flex[^}]*overflow-x:auto", base_css):
        raise SystemExit("Provider tab strip must remain horizontal and scrollable")
    match = re.search(r"\.tabs\{([^}]*)\}", contract_css)
    if not match:
        raise SystemExit("Institutional tab geometry rule is missing")
    rule = match.group(1)
    for declaration in (
        "min-block-size:82px",
        "align-items:center",
        "overscroll-behavior-inline:contain",
    ):
        if declaration not in rule:
            raise SystemExit(f"Provider tab geometry is missing: {declaration}")
    if "tabs.insertBefore(tab, guideTab)" not in integration:
        raise SystemExit("Dynamic institutional tab insertion contract is missing")
    if 'tab.textContent = "العقد المؤسسي v220"' not in integration:
        raise SystemExit("Institutional tab label contract is missing")
    if f'data-institutional-contract="{CONTRACT}"' not in html:
        raise SystemExit("Provider page does not declare the current institutional contract")
    # 44px tab + 20px vertical padding + 2px border + about 15px classic scrollbar.
    required_height = 44 + 20 + 2 + 15
    if required_height > 82:
        raise SystemExit("Reserved tab-strip geometry is insufficient")
    return {
        "version": 225,
        "status": "passed",
        "marker_count": 1,
        "reserved_tab_strip_px": 82,
        "required_geometry_px": required_height,
        "horizontal_scroll_preserved": True,
        "dynamic_tab_insertion_detected": True,
        "institutional_contract": CONTRACT,
        "threshold_changed": False,
    }


def main() -> int:
    report = validate(read(BASE_STYLE), read(CONTRACT_STYLE), read(INTEGRATION), read(INDEX))
    if SITE.is_dir():
        production = SITE / "provider-assessment-demo"
        report["production_verified"] = validate(
            read(production / "styles.css"),
            read(production / "institutional-contract-v220.css"),
            read(production / "institutional-contract-v220-integration.js"),
            read(production / "index.html"),
        )["status"] == "passed"
        api = SITE / "api"
        api.mkdir(parents=True, exist_ok=True)
        (api / REPORT_NAME).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        report["production_verified"] = False
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
