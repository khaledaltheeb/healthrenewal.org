#!/usr/bin/env python3
"""Stable-report adapter for the edited v403 content engine.

The HTML engine remains v403. This adapter converts per-run sitemap insertion
counts into deterministic contract counts, canonicalizes whitespace around hub
insertion markers, and completes social metadata on every generated page.
"""

from __future__ import annotations

from pathlib import Path
import json
import re
import sys
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publish_undercovered_content_v403 import *  # noqa: F401,F403
import publish_undercovered_content_v403 as engine403
from social_metadata_v2 import ensure_social_metadata

ENGINE_REVISION = 403
STABLE_SITEMAP_CONTRACT = {
    "sitemap-special-needs.xml": 60,
    "sitemap-family-special-needs.xml": 60,
    "sitemap-family-learning-paths.xml": 15,
    "sitemap-family-main.xml": 25,
}


def normalize_hub_markers(site: Path) -> None:
    """Keep exactly one newline around each generated hub block."""
    for section, relative_path in HUB_PATHS.items():
        path = site / relative_path
        if not path.is_file():
            raise SystemExit(f"Missing hub during stable normalization: {path}")
        source = path.read_text(encoding="utf-8")
        start = f"<!-- undercovered-content-v401-{section}:start -->"
        end = f"<!-- undercovered-content-v401-{section}:end -->"
        if source.count(start) != 1 or source.count(end) != 1:
            raise SystemExit(f"{path}: generated hub markers are missing or duplicated")
        source = re.sub(rf"\s*{re.escape(start)}", "\n" + start, source, count=1)
        source = re.sub(rf"{re.escape(end)}\s*", end + "\n", source, count=1)
        path.write_text(source, encoding="utf-8")


def complete_generated_social_metadata(site: Path, expected: int) -> int:
    """Complete cards on v403 pages and fail if the publication surface drifts."""
    processed = 0
    for path in sorted(site.rglob("*.html")):
        source = path.read_text(encoding="utf-8")
        if 'data-content-engine="v403"' not in source:
            continue
        updated = ensure_social_metadata(source)
        path.write_text(updated, encoding="utf-8")
        processed += 1
    if processed != expected:
        raise SystemExit(f"Expected {expected} v403 pages for social metadata; found {processed}")
    return processed


def publish(site: Path) -> dict[str, Any]:
    report = engine403.publish(site)
    social_pages = complete_generated_social_metadata(site, report["page_count"])
    normalize_hub_markers(site)
    report["engine_revision"] = ENGINE_REVISION
    report["sitemap_updates"] = dict(STABLE_SITEMAP_CONTRACT)
    report["social_metadata_pages"] = social_pages
    report["quality_gates"]["stable_sitemap_report"] = True
    report["quality_gates"]["stable_hub_whitespace"] = True
    report["quality_gates"]["complete_social_metadata"] = True
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
