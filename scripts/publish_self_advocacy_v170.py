#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import publish_self_advocacy_v171 as previous

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "learning-paths" / "self-advocacy"
CONTINUITY_FILE = "service-transition-and-continuity-plan.json"
CONTINUITY_TITLE = "خطة انتقال الخدمة واستمراريتها في المناصرة الذاتية"
VERSION = 172

PUBLIC_PACKAGES = previous.PUBLIC_PACKAGES + ((CONTINUITY_FILE, CONTINUITY_TITLE),)
GOVERNANCE_FILE = previous.GOVERNANCE_FILE
HISTORICAL_GOVERNANCE_FILE = previous.HISTORICAL_GOVERNANCE_FILE
TARGET_RELATIVE = previous.TARGET_RELATIVE
CANONICAL_ROUTE = previous.CANONICAL_ROUTE
CANONICAL_URL = previous.CANONICAL_URL
START = previous.START
END = previous.END


def publish(site: Path) -> dict[str, Any]:
    source_path = SOURCE_DIR / CONTINUITY_FILE
    if not source_path.is_file():
        raise SystemExit(f"Missing continuity source package: {source_path}")
    data = previous.base.load_json(source_path)
    previous.base.validate_package(source_path, data)

    report = previous.publish(site)
    target = site / TARGET_RELATIVE
    page = target.read_text(encoding="utf-8", errors="replace")
    marker = f'data-source-package="{CONTINUITY_FILE}"'
    if marker not in page:
        section = previous.base.render_package(CONTINUITY_FILE, CONTINUITY_TITLE, data)
        if END not in page:
            raise SystemExit("Self-advocacy integration end marker is missing")
        page = page.replace(END, section + "\n" + END, 1)
        target.write_text(page, encoding="utf-8")

    accessibility = previous.validate_accessibility_contract(site, page)
    if page.count(marker) != 1:
        raise SystemExit("Continuity package was not integrated exactly once")
    if page.count(f'<link rel="canonical" href="{CANONICAL_URL}">') != 1:
        raise SystemExit("Self-advocacy canonical changed during continuity integration")

    report.update({
        "version": VERSION,
        "sourcePackageCount": len(PUBLIC_PACKAGES) + 1,
        "totalEvidenceFiles": len(PUBLIC_PACKAGES) + 2,
        "publicContentPackageCount": len(PUBLIC_PACKAGES),
        "sectionsRendered": len(PUBLIC_PACKAGES) + 2,
        "continuityPackage": CONTINUITY_FILE,
        "continuityPackageStatus": "merged-into-existing-page",
        "standalonePagesCreated": 0,
        "accessibilityStatus": "passed",
        "accessibilityChecks": accessibility,
        "outputBytes": len(page.encode("utf-8")),
    })
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    for filename in ("self-advocacy-v170.json", "self-advocacy-v171.json", "self-advocacy-v172.json"):
        (api / filename).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
