#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
SOURCE_CSS = ROOT / "provider-assessment-demo" / "enhancements.css"
SOURCE_HTML = ROOT / "provider-assessment-demo" / "index.html"
SOURCE_JS = ROOT / "provider-assessment-demo" / "app.js"
REPORT_NAME = "provider-layout-stability-v223.json"
MARKER = "provider-layout-stability-v223"


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing provider layout source: {path}")
    return path.read_text(encoding="utf-8")


def validate(css: str, html: str, runtime: str) -> dict[str, object]:
    if css.count(MARKER) != 1:
        raise SystemExit("Provider layout stability marker must appear exactly once")
    if not re.search(r"\.stats-grid>\.stat-card\{[^}]*min-block-size:128px", css):
        raise SystemExit("Provider statistic cards do not reserve hydration height")
    if not re.search(r"#current-uid\{[^}]*font-size:clamp\([^}]*line-height:1\.35", css):
        raise SystemExit("Provider UID does not have stable wrapping metrics")
    if html.count('id="current-uid"') != 1:
        raise SystemExit("Provider page must expose exactly one current UID field")
    if 'el.uid.textContent=identity.uid' not in runtime:
        raise SystemExit("Provider runtime UID hydration contract is missing")
    if 'UID-VIS' not in runtime or '.slice(0,16)' not in runtime:
        raise SystemExit("Provider UID length contract changed without layout review")
    return {
        "version": 223,
        "status": "passed",
        "marker_count": 1,
        "reserved_stat_card_px": 128,
        "uid_wrap_metrics_reserved": True,
        "uid_hydration_detected": True,
        "uid_length_contract_detected": True,
        "threshold_changed": False,
    }


def main() -> int:
    report = validate(read(SOURCE_CSS), read(SOURCE_HTML), read(SOURCE_JS))
    if SITE.is_dir():
        production_css = SITE / "provider-assessment-demo" / "enhancements.css"
        production_html = SITE / "provider-assessment-demo" / "index.html"
        if not production_css.is_file() or not production_html.is_file():
            raise SystemExit("Generated provider platform is missing before layout verification")
        production = validate(read(production_css), read(production_html), read(SOURCE_JS))
        report["production_verified"] = production["status"] == "passed"
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
