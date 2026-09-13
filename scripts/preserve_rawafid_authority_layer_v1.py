#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

CANONICAL_FILES = (
    "llms.txt",
    "api/v1/institutional-profile.json",
    "api/v1/platform-facts.json",
    "api/v1/ai-discovery.json",
    "api/v1/ai-discovery.openapi.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _copy_json_with_fresh_timestamp(source: Path, destination: Path, generated_at: str) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "generatedAt" in payload:
        payload["generatedAt"] = generated_at
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _merge_llms_full(site: Path, repo_root: Path, generated_at: str) -> dict[str, object]:
    destination = site / "llms-full.txt"
    source = repo_root / "llms-full.txt"
    if not source.is_file():
        raise FileNotFoundError(source)

    canonical = source.read_text(encoding="utf-8").rstrip()
    generated = destination.read_text(encoding="utf-8") if destination.is_file() else ""

    marker = "## Canonical pages"
    generated_catalogue = ""
    if marker in generated:
        generated_catalogue = generated.split(marker, 1)[1].strip()

    lines = [canonical, "", "## Exhaustive generated page catalogue", ""]
    lines.append(
        "This catalogue is generated from the final production artifact after publication and exists to prevent homepage-only or sample-only evaluation from understating Rawafid's actual public scope."
    )
    lines.append("")
    lines.append(f"Generated from final artifact: {generated_at}")
    lines.append("")
    if generated_catalogue:
        lines.append(generated_catalogue)
    else:
        lines.append("Use the canonical sitemap and content index for exhaustive enumeration.")

    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "merged": True,
        "generated_catalogue_present": bool(generated_catalogue),
        "destination": "llms-full.txt",
    }


def apply(site: Path, repo_root: Path) -> dict[str, object]:
    site = site.resolve()
    repo_root = repo_root.resolve()
    generated_at = _utc_now()

    # Production builds target an artifact directory such as _site. When the
    # generator is invoked directly against the repository checkout, never
    # self-copy or rewrite canonical authority files from themselves.
    if site == repo_root:
        return {
            "status": "skipped-repository-root",
            "generated_at": generated_at,
            "files": [],
        }

    copied: list[str] = []
    for relative in CANONICAL_FILES:
        source = repo_root / relative
        destination = site / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix == ".json":
            _copy_json_with_fresh_timestamp(source, destination, generated_at)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        copied.append(relative)

    llms_full = _merge_llms_full(site, repo_root, generated_at)

    # The content index generated immediately before this step remains
    # authoritative and exhaustive for the final artifact. Do not replace it
    # with the curated source checkout index.
    content_index = site / "api/v1/content-index.json"
    if not content_index.is_file():
        raise FileNotFoundError(content_index)
    payload = json.loads(content_index.read_text(encoding="utf-8"))
    payload["catalogueType"] = "exhaustive-final-artifact"
    payload["isExhaustive"] = True
    payload["countMeaning"] = "Total indexable HTML records discovered in the final production artifact at generation time."
    payload["institutionalProfile"] = "https://healthrenewal.org/api/v1/institutional-profile.json"
    payload["platformFacts"] = "https://healthrenewal.org/api/v1/platform-facts.json"
    content_index.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "status": "applied",
        "generated_at": generated_at,
        "files": copied,
        "llms_full": llms_full,
        "content_index_count": payload.get("count"),
        "content_index_exhaustive": True,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    print(json.dumps(apply(args.site, args.repo_root), ensure_ascii=False, indent=2))
