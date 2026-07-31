#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import publish_provider_condition_discovery_v238 as core

BASE = "https://healthrenewal.org"
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

    # Remove all legacy discovery directives before registering only live,
    # custom-domain maps. The central generator preserves these directives.
    lines = [
        line
        for line in lines
        if not (
            line.strip().lower().startswith("sitemap:")
            and any(line.strip().endswith(f"/{filename}") for filename in DISCOVERY_SITEMAPS)
        )
    ]

    registered: list[str] = []
    for filename in DISCOVERY_SITEMAPS:
        sitemap = site / filename
        if not sitemap.is_file():
            continue
        lines.append(f"Sitemap: {BASE}/{filename}")
        registered.append(filename)

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    normalized = path.read_text(encoding="utf-8")
    if "khaledaltheeb.github.io/" in normalized:
        raise ValueError("robots.txt contains a legacy discovery sitemap URL")
    for filename in DISCOVERY_SITEMAPS:
        directive = f"Sitemap: {BASE}/{filename}"
        expected = 1 if filename in registered else 0
        actual = normalized.count(directive)
        if actual != expected:
            raise ValueError(
                f"robots.txt sitemap registry failed: {filename}; expected={expected}; actual={actual}"
            )
    return registered


def finalize_sitemap_coverage(site: Path) -> dict[str, Any]:
    """Rebuild exact routes after discovery changes; metadata was enforced before the deployment stamp."""
    generator = Path(__file__).with_name("generate_sitemap_index_v304.py")
    auditor = Path(__file__).with_name("audit_indexing_coverage_v303.py")
    subprocess.run([sys.executable, str(generator), str(site)], check=True)
    subprocess.run([sys.executable, str(auditor), str(site), "--routes-only"], check=True)
    report_path = site / "api" / "indexing-coverage-audit-v303.json"
    if not report_path.is_file():
        raise ValueError(f"Missing indexing coverage evidence: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("version") != 305 or report.get("status") != "passed":
        raise ValueError(f"Final indexing route coverage failed: {report}")
    if report.get("mode") != "routes-only" or report.get("local_route_contract") != "passed":
        raise ValueError(f"Post-discovery route contract was not enforced: {report}")
    if int(report.get("sitemap_urls", -1)) != int(report.get("expected_indexable_pages", 0)):
        raise ValueError(f"Sitemap URL count differs from expected pages: {report}")
    if float(report.get("sitemap_coverage_ratio", 0)) != 1.0:
        raise ValueError(f"Sitemap coverage is incomplete: {report}")
    return report


def publish(site: Path) -> dict[str, Any]:
    """Compatibility entrypoint retained for the production discovery workflow."""
    site = site.resolve()
    report = core.publish(site)
    registered = sync_discovery_sitemaps(site)
    indexing = finalize_sitemap_coverage(site)

    # The generator rewrites sitemap.xml as the complete canonical urlset and
    # preserves the custom-domain discovery sitemap directives in robots.txt.
    final_robots = (site / "robots.txt").read_text(encoding="utf-8")
    for filename in registered:
        directive = f"Sitemap: {BASE}/{filename}"
        if final_robots.count(directive) != 1:
            raise ValueError(f"Final robots registry lost discovery sitemap: {filename}")

    report["robots_registered_sitemaps"] = registered
    report["provider_assessment_sitemap_registered"] = "sitemap-provider-assessment.xml" in registered
    report["special_needs_sitemap_registered"] = "sitemap-special-needs.xml" in registered
    report["sitemap_index_version"] = indexing["version"]
    report["sitemap_index_status"] = indexing["status"]
    report["sitemap_index_mode"] = indexing["mode"]
    report["sitemap_index_pages"] = indexing["expected_indexable_pages"]
    report["sitemap_index_urls"] = indexing["sitemap_urls"]
    report["sitemap_index_coverage_ratio"] = indexing["sitemap_coverage_ratio"]
    report["primary_sitemap_complete"] = (
        int(indexing["sitemap_urls"]) == int(indexing["expected_indexable_pages"])
        and float(indexing["sitemap_coverage_ratio"]) == 1.0
    )
    report["custom_domain"] = BASE
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
