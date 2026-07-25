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


def institutional_report(site: Path) -> dict[str, object] | None:
    path = site / "api" / "special-needs-guides-v221.json"
    if not path.is_file():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("version") == 221 and report.get("hub_release") == 241:
        return report
    return None


def finalize_institutional(site: Path, report: dict[str, object]) -> dict[str, object]:
    page = site / "special-needs" / "index.html"
    if not page.is_file():
        raise SystemExit(f"Missing institutional special-needs hub: {page}")
    source = page.read_text(encoding="utf-8")
    required = (
        '<a class="skip" href="#main">',
        'pathway-communication',
        'data-special-needs-jordan-context-v241',
        'prefers-reduced-motion',
        'prefers-contrast:more',
        '@media print',
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise SystemExit(f"Institutional special-needs accessibility contract failed: {missing}")
    if any(token in source for token in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "eval(", "new Function(")):
        raise SystemExit("Institutional special-needs hub contains unsafe network or dynamic runtime")
    if report.get("guide_count") != 25 or report.get("batch_count") != 5:
        raise SystemExit(f"Institutional guide integration contract failed: {report}")

    compatibility_path = site / "api" / "special-needs-hub-v201.json"
    compatibility = (
        json.loads(compatibility_path.read_text(encoding="utf-8"))
        if compatibility_path.is_file()
        else {"version": 201, "output": "special-needs/index.html"}
    )
    compatibility["search_accessibility"] = {
        "mode": "static-semantic-navigation",
        "search_input_required": False,
        "skip_link": True,
        "keyboard_focus": True,
        "javascript_required": False,
    }
    compatibility["legacy_accessibility_finalizer"] = "institutional-v243-no-op"
    compatibility_path.parent.mkdir(parents=True, exist_ok=True)
    compatibility_path.write_text(
        json.dumps(compatibility, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = {
        "version": 201,
        "page": "special-needs/index.html",
        "mode": "institutional-v243",
        "legacy_search_patch_applied": False,
        "search_input_required": False,
        "skip_link": True,
        "keyboard_focus": True,
        "javascript_required": False,
        "special_needs_guides_versions": [209, 210, 211, 212, 214],
        "special_needs_guides": 25,
        "special_needs_batches": 5,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def finalize_legacy(site: Path) -> dict[str, object]:
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
    report = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.is_file()
        else {"version": 201, "output": "special-needs/index.html"}
    )
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
        run_batch(site, 212, "publish_special_needs_guides_v212.py"),
        run_batch(site, 214, "publish_special_needs_guides_v214.py"),
    ]
    total_guides = sum(int(batch["guide_count"]) for batch in batches)

    result = {
        "version": 201,
        "page": "special-needs/index.html",
        "mode": "legacy-v201",
        "label_changed": label_changed,
        "input_changed": input_changed,
        "explicit_label_for": True,
        "accessible_name": True,
        "special_needs_guides_versions": [209, 210, 211, 212, 214],
        "special_needs_guides": total_guides,
        "special_needs_batches": len(batches),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def finalize(site: Path) -> dict[str, object]:
    report = institutional_report(site)
    if report is not None:
        return finalize_institutional(site, report)
    return finalize_legacy(site)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not target.is_dir():
        raise SystemExit(f"Missing site directory: {target}")
    finalize(target)
