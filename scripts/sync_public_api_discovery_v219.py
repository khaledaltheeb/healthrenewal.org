from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 219
REQUIRED_PATHS = {
    "/api/v1/content-index.json",
    "/api/v1/taxonomy.json",
}


class PublicApiDiscoverySyncError(ValueError):
    pass


def read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PublicApiDiscoverySyncError(f"invalid JSON: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise PublicApiDiscoverySyncError(f"expected object: {path}")
    return payload


def sync(root: Path, site: Path, stage: str) -> dict[str, Any]:
    if stage not in {"prepared", "published"}:
        raise PublicApiDiscoverySyncError(f"unsupported stage: {stage}")
    report_path = root / ".build" / "reports" / "public-api-v215.json"
    openapi_path = site / "api" / "v1" / "openapi.json"
    if not report_path.is_file():
        raise PublicApiDiscoverySyncError(
            "public-api-v215.json is missing; public API must run before discovery sync"
        )
    report = read_object(report_path)
    openapi = read_object(openapi_path)
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        raise PublicApiDiscoverySyncError("OpenAPI paths object is missing")
    missing = sorted(REQUIRED_PATHS - set(paths))
    if missing:
        raise PublicApiDiscoverySyncError(
            f"content discovery OpenAPI paths are missing: {missing}"
        )

    report["endpoints"] = len(paths)
    report["content_discovery"] = True
    report["content_discovery_schema_version"] = SCHEMA_VERSION
    report["content_discovery_stage"] = stage
    report["content_discovery_paths"] = sorted(REQUIRED_PATHS)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "endpoints": len(paths),
        "paths": sorted(REQUIRED_PATHS),
        "report": report_path.relative_to(root).as_posix(),
    }
