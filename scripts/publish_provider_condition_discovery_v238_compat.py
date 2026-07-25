#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import publish_provider_condition_discovery_v238 as core

BASE = "https://khaledaltheeb.github.io/pterminology-site"
DISCOVERY_SITEMAPS = (
    "sitemap-provider-assessment.xml",
    "sitemap-special-needs.xml",
)


def sync_discovery_sitemaps(site: Path) -> list[str]:
    path = site / "robots.txt"
    if path.is_file():
        lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
    else:
        lines = ["User-agent: *", "Allow: /"]

    registered: list[str] = []
    for filename in DISCOVERY_SITEMAPS:
        directive = f"Sitemap: {BASE}/{filename}"
        # Remove stale and duplicate directives first. Re-add exactly once only
        # when the corresponding sitemap exists in the production artifact.
        lines = [line for line in lines if line != directive]
        sitemap = site / filename
        if not sitemap.is_file():
            continue
        lines.append(directive)
        registered.append(filename)

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    normalized = path.read_text(encoding="utf-8")
    for filename in DISCOVERY_SITEMAPS:
        directive = f"Sitemap: {BASE}/{filename}"
        expected = 1 if filename in registered else 0
        actual = normalized.count(directive)
        if actual != expected:
            raise ValueError(
                f"robots.txt sitemap registry failed: {filename}; expected={expected}; actual={actual}"
            )
    return registered


def publish(site: Path) -> dict[str, Any]:
    """Compatibility entrypoint retained for the production discovery workflow."""
    site = site.resolve()
    report = core.publish(site)
    registered = sync_discovery_sitemaps(site)
    report["robots_registered_sitemaps"] = registered
    report["provider_assessment_sitemap_registered"] = "sitemap-provider-assessment.xml" in registered
    report["special_needs_sitemap_registered"] = "sitemap-special-needs.xml" in registered
    report_path = site / "api" / "provider-condition-discovery-v238.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
