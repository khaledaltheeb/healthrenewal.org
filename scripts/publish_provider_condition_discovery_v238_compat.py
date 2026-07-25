#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import publish_provider_condition_discovery_v238 as core


def sync_robots(site: Path) -> None:
    path = site / "robots.txt"
    child = f"Sitemap: {core.BASE}/{core.SITEMAP_NAME}"
    if path.is_file():
        lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
    else:
        lines = ["User-agent: *", "Allow: /"]
    lines = [line for line in lines if line != child]
    lines.append(child)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def validate(site: Path, records: list[dict[str, str]], urls: list[str]) -> dict[str, Any]:
    gateway = (site / "provider-assessment-demo" / "index.html").read_text(encoding="utf-8")
    directory = (site / "provider-assessment-demo" / "conditions" / "index.html").read_text(encoding="utf-8")
    training_path = site / "provider-assessment-demo" / "training" / "index.html"
    if not training_path.is_file():
        raise ValueError("Missing provider training page")
    training = training_path.read_text(encoding="utf-8")
    if f"{core.BASE}/provider-assessment-demo/training/" not in training or "noindex" in training.lower():
        raise ValueError("Provider training page indexability contract failed")
    if gateway.count(core.GATEWAY_START) != 1:
        raise ValueError("Provider gateway marker contract failed")
    if gateway.count('href="conditions/"') < 1:
        raise ValueError("Provider condition gateway link is missing")
    if gateway.count('href="training/"') != 1:
        raise ValueError("Provider training gateway link contract failed")
    if directory.count(core.DIRECTORY_START) != 1:
        raise ValueError("Provider condition directory marker contract failed")
    if directory.count(core.STYLE_MARKER) != 1 or directory.count(core.SCHEMA_MARKER) != 1:
        raise ValueError("Provider condition directory metadata contract failed")
    missing = [record["slug"] for record in records if directory.count(f'href="{record["slug"]}/"') != 1]
    if missing:
        raise ValueError(f"Provider condition links are missing or duplicated: {missing}")
    sitemap = ET.parse(site / core.SITEMAP_NAME).getroot()
    locations = [(node.text or "").strip() for node in sitemap.findall("{*}url/{*}loc") if node.text]
    if locations != urls or len(locations) != len(set(locations)):
        raise ValueError("Provider condition sitemap route contract failed")
    robots = (site / "robots.txt").read_text(encoding="utf-8")
    child = f"Sitemap: {core.BASE}/{core.SITEMAP_NAME}"
    if robots.count(child) != 1:
        raise ValueError("Robots provider sitemap contract failed")
    return {
        "version": core.VERSION,
        "status": "passed",
        "condition_count": len(records),
        "gateway_links": 1,
        "directory_links": len(records),
        "training_links": 1,
        "sitemap_routes": len(urls),
        "robots_sitemap_registered": True,
        "root_sitemap_unchanged": True,
        "static_html_discovery": True,
        "javascript_required_for_discovery": False,
    }


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ValueError(f"Missing site directory: {site}")
    root_sitemap = site / "sitemap.xml"
    before = root_sitemap.read_bytes() if root_sitemap.is_file() else None
    records = core.discover_conditions(site)
    core.inject_directory_page(site, records)
    core.inject_gateway_page(site)
    urls = core.write_provider_sitemap(site, records, core.UPDATED)
    sync_robots(site)
    if before is not None and root_sitemap.read_bytes() != before:
        raise ValueError("Provider discovery compatibility layer changed the root sitemap")
    report = validate(site, records, urls)
    output = site / "api" / "provider-condition-discovery-v238.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
