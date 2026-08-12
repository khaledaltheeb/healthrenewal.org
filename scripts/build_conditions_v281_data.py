#!/usr/bin/env python3
"""Build the deterministic v281 payload from reviewable JSON sources."""
from __future__ import annotations

import argparse
import base64
import json
import zlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "content" / "v281" / "metadata-ar.json"
CONDITIONS_DIR = ROOT / "content" / "v281" / "conditions"
OVERRIDES = ROOT / "content" / "v281" / "evidence-overrides-wave1-ar.json"
DEFAULT_OUTPUT = ROOT / "content" / "v281" / "conditions-50-ar.json.zlib.b64"
REQUIRED_FIELDS = {
    "rank", "slug", "title_ar", "title_en", "category", "cause", "pattern",
    "medical_focus", "diagnosis", "care", "safety", "opportunity",
    "source_title", "source_url",
}
APPENDABLE_FIELDS = {"cause", "pattern", "medical_focus", "diagnosis", "care", "safety", "opportunity"}
OVERRIDE_KEYS = {"source_title", "source_url"} | {f"{field}_append" for field in APPENDABLE_FIELDS}


def apply_evidence_overrides(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not OVERRIDES.exists():
        return {"applied": 0, "slugs": []}
    payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    overrides = payload.get("conditions")
    if not isinstance(overrides, dict):
        raise ValueError("evidence overrides must contain a conditions object")
    by_slug = {item["slug"]: item for item in items}
    unknown = sorted(set(overrides) - set(by_slug))
    if unknown:
        raise ValueError(f"evidence overrides reference unknown slugs: {unknown}")
    for slug, patch in overrides.items():
        if not isinstance(patch, dict):
            raise ValueError(f"{slug}: evidence override must be an object")
        invalid = sorted(set(patch) - OVERRIDE_KEYS)
        if invalid:
            raise ValueError(f"{slug}: unsupported evidence override keys: {invalid}")
        item = by_slug[slug]
        for field in ("source_title", "source_url"):
            if field in patch:
                value = patch[field]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{slug}: {field} must be a non-empty string")
                item[field] = value.strip()
        for field in APPENDABLE_FIELDS:
            key = f"{field}_append"
            if key in patch:
                addition = patch[key]
                if not isinstance(addition, str) or len(addition.strip()) < 70:
                    raise ValueError(f"{slug}: {key} is too short")
                item[field] = f"{item[field].rstrip()} {addition.strip()}"
    return {"applied": len(overrides), "slugs": sorted(overrides), "updated_at": payload.get("updated_at")}


def load_sources() -> dict[str, Any]:
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    for path in sorted(CONDITIONS_DIR.glob("*.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
            if set(item) != REQUIRED_FIELDS:
                raise ValueError(f"{path}:{number}: invalid fields {sorted(set(item) ^ REQUIRED_FIELDS)}")
            items.append(item)
    items.sort(key=lambda item: item["rank"])
    if len(items) != 50:
        raise ValueError(f"expected 50 conditions, found {len(items)}")
    if [item["rank"] for item in items] != list(range(101, 151)):
        raise ValueError("ranks must be exactly 101..150")
    slugs = [item["slug"] for item in items]
    if len(set(slugs)) != 50:
        raise ValueError("condition slugs must be unique")

    evidence = apply_evidence_overrides(items)

    source_urls = [item["source_url"] for item in items]
    if len(set(source_urls)) != 50:
        raise ValueError("each condition must have a distinct source entry URL")
    categories = metadata.get("categories", {})
    for item in items:
        if item["category"] not in categories:
            raise ValueError(f"unknown category: {item['category']}")
        for field in APPENDABLE_FIELDS:
            if len(item[field]) < 70:
                raise ValueError(f"{item['slug']}: {field} is too short")
        if not item["source_url"].startswith("https://"):
            raise ValueError(f"{item['slug']}: source_url must use https")

    payload = dict(metadata)
    payload["conditions"] = items
    payload["evidence_overrides"] = evidence
    return payload


def build(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    payload = load_sources()
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded + "\n", encoding="ascii")
    report = {
        "version": payload["version"],
        "conditions": len(payload["conditions"]),
        "categories": len(payload["categories"]),
        "evidence_overrides": payload["evidence_overrides"]["applied"],
        "raw_bytes": len(raw),
        "encoded_bytes": len(encoded),
        "output": str(output),
    }
    print(json.dumps(report, ensure_ascii=False))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output)


if __name__ == "__main__":
    main()
