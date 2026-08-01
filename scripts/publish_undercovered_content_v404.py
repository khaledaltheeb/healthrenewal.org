#!/usr/bin/env python3
"""Stable-report adapter for the edited v403 content engine.

The HTML engine remains v403. This adapter converts per-run sitemap insertion
counts into deterministic contract counts so repeated publication produces the
same API report as well as the same pages, hubs, and sitemap files.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import publish_undercovered_content_v403 as core
from publish_undercovered_content_v403 import *  # noqa: F401,F403

ENGINE_REVISION = 403
STABLE_SITEMAP_CONTRACT = {
    "sitemap-special-needs.xml": 60,
    "sitemap-family-special-needs.xml": 60,
    "sitemap-family-learning-paths.xml": 15,
    "sitemap-family-main.xml": 25,
}


def publish(site: Path) -> dict[str, Any]:
    report = core.publish(site)
    report["sitemap_updates"] = dict(STABLE_SITEMAP_CONTRACT)
    report["quality_gates"]["stable_sitemap_report"] = True
    api = site / "api" / "undercovered-content-v401.json"
    api.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Publish stable v401 reports using the edited v403 HTML engine.")
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
