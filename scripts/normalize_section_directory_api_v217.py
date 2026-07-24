#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
SECTIONS_ENDPOINT = BASE_URL + "api/v1/sections.json"


def main() -> None:
    platform_path = SITE / "api" / "v1" / "platform.json"
    sections_path = SITE / "api" / "v1" / "sections.json"
    openapi_path = SITE / "api" / "v1" / "openapi.json"
    if not platform_path.is_file() or not sections_path.is_file() or not openapi_path.is_file():
        raise SystemExit("Section directory API inputs are missing")

    sections = json.loads(sections_path.read_text(encoding="utf-8"))
    if sections.get("release") != 217 or int(sections.get("section_count", 0)) <= 0:
        raise SystemExit(f"Invalid sections endpoint: {sections}")

    platform = json.loads(platform_path.read_text(encoding="utf-8"))
    resources = platform.setdefault("resources", [])
    if not isinstance(resources, list):
        raise SystemExit("platform resources must be a list")
    normalized = {
        "id": "sections",
        "type": "collection",
        "title": "دليل أقسام المنصة",
        "url": SECTIONS_ENDPOINT,
        "tags": ["الأقسام", "التصفح", "واجهة API"],
    }
    matched = False
    cleaned: list[object] = []
    for item in resources:
        item_url = item.get("url") if isinstance(item, dict) else item
        item_id = item.get("id") if isinstance(item, dict) else None
        if item_url == SECTIONS_ENDPOINT or item_id == "sections":
            if not matched:
                cleaned.append(normalized)
                matched = True
            continue
        cleaned.append(item)
    if not matched:
        cleaned.append(normalized)
    platform["resources"] = cleaned
    endpoints = platform.setdefault("endpoints", {})
    if not isinstance(endpoints, dict):
        raise SystemExit("platform endpoints must be an object")
    endpoints["sections"] = SECTIONS_ENDPOINT
    platform_path.write_text(
        json.dumps(platform, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
    paths = openapi.get("paths", {})
    if not isinstance(paths, dict) or not any(
        str(path).endswith("/api/v1/sections.json") for path in paths
    ):
        raise SystemExit("OpenAPI sections endpoint is missing")

    report_path = SITE / "api" / "section-directory-v217.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["platform_resource_normalized"] = True
    report["platform_endpoint_registered"] = True
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "passed",
        "sections": sections["section_count"],
        "platform_resource": "normalized",
        "endpoint": SECTIONS_ENDPOINT,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
