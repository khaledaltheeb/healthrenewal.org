#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

LABEL_OLD = '<label class="field"><span>البحث داخل المركز</span>'
LABEL_NEW = '<label class="field" for="hub-search"><span>البحث داخل المركز</span>'
INPUT_OLD = '<input id="hub-search" type="search" placeholder='
INPUT_NEW = '<input id="hub-search" type="search" aria-label="البحث داخل مركز ذوي الاحتياجات الخاصة" placeholder='


def run_batch(site: Path, version: int, script_name: str) -> dict[str, object]:
    publisher = Path(__file__).with_name(script_name)
    subprocess.run([sys.executable, str(publisher), str(site)], check=True)
    report_path = site / "api" / f"special-needs-guides-v{version}.json"
    if not report_path.is_file():
        raise SystemExit(f"v{version} publisher completed without an evidence report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("guide_count") != 5 or not report.get("hub_linked"):
        raise SystemExit(f"Invalid v{version} guide report: {report}")
    return report


def finalize(site: Path) -> dict[str, object]:
    page = site / "special-needs" / "index.html"
    if not page.is_file():
        raise SystemExit(f"Missing generated special-needs hub: {page}")

    text = page.read_text(encoding="utf-8")
    if text.count('id="hub-search"') != 1:
        raise SystemExit("Expected exactly one special-needs hub search input")

    label_changed = False
    input_changed = False
    if 'for="hub-search"' not in text:
        if LABEL_OLD not in text:
            raise SystemExit("Special-needs search label marker changed; refusing unsafe accessibility patch")
        text = text.replace(LABEL_OLD, LABEL_NEW, 1)
        label_changed = True

    if 'aria-label="البحث داخل مركز ذوي الاحتياجات الخاصة"' not in text:
        if INPUT_OLD not in text:
            raise SystemExit("Special-needs search input marker changed; refusing unsafe accessibility patch")
        text = text.replace(INPUT_OLD, INPUT_NEW, 1)
        input_changed = True

    if text.count('for="hub-search"') != 1:
        raise SystemExit("Search input must have exactly one explicit label association")
    if text.count('aria-label="البحث داخل مركز ذوي الاحتياجات الخاصة"') != 1:
        raise SystemExit("Search input must have exactly one accessible name")

    page.write_text(text, encoding="utf-8")

    report_path = site / "api" / "special-needs-hub-v201.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report = {"version": 201, "output": "special-needs/index.html"}
    report["search_accessibility"] = {
        "explicit_label_for": True,
        "accessible_name": True,
        "input_id": "hub-search",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    batches = [
        run_batch(site, 209, "publish_special_needs_guides_v209_compat.py"),
        run_batch(site, 210, "publish_special_needs_guides_v210.py"),
        run_batch(site, 211, "publish_special_needs_guides_v211.py"),
    ]
    total_guides = sum(int(batch["guide_count"]) for batch in batches)

    result = {
        "version": 201,
        "page": "special-needs/index.html",
        "label_changed": label_changed,
        "input_changed": input_changed,
        "explicit_label_for": True,
        "accessible_name": True,
        "special_needs_guides_versions": [209, 210, 211],
        "special_needs_guides": total_guides,
        "special_needs_batches": len(batches),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not target.is_dir():
        raise SystemExit(f"Missing site directory: {target}")
    finalize(target)
