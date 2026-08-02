#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, payload, *, compact: bool = False) -> bool:
    before = path.read_text(encoding="utf-8")
    after = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        if compact
        else json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )
    if before == after:
        return False
    path.write_text(after, encoding="utf-8")
    return True


def migrate_expansion_evidence() -> list[str]:
    changed: list[str] = []
    for relative in (
        "data/content-expansion-v1/official-evidence.json",
        "data/content-expansion-v1/official-evidence-overrides.json",
    ):
        path = ROOT / relative
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "sources" in payload:
            payload["source_registry"] = payload.pop("sources")
        for profile in payload.get("profiles", []):
            if "sources" in profile:
                profile["source_refs"] = profile.pop("sources")
        if write_json(path, payload):
            changed.append(relative)
    return changed


def migrate_family_tools() -> list[str]:
    changed: list[str] = []
    directory = ROOT / "content/family-guide-special-education-tools-v1"
    for path in sorted(directory.glob("tools-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for tool in payload:
            if "sources" in tool:
                tool["source_refs"] = tool.pop("sources")
        if write_json(path, payload):
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def migrate_women_youth() -> list[str]:
    path = ROOT / "content/v406/women-youth-expansion-ar.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for page in payload.get("pages", []):
        if "sources" in page:
            page["source_refs"] = page.pop("sources")
    return [path.relative_to(ROOT).as_posix()] if write_json(path, payload, compact=True) else []


def patch_text(path: Path, replacements: list[tuple[str, str]], regexes: list[tuple[str, str]] = []) -> bool:
    before = path.read_text(encoding="utf-8")
    after = before
    for old, new in replacements:
        after = after.replace(old, new)
    for pattern, replacement in regexes:
        after = re.sub(pattern, replacement, after)
    if after == before:
        return False
    path.write_text(after, encoding="utf-8")
    return True


def migrate_consumers() -> list[str]:
    changed: list[str] = []
    updates = {
        "data/content-expansion-v1/apply_evidence_profiles.py": [
            ('profile.get("sources", [])', 'profile.get("source_refs", [])'),
            ('config["sources"]', 'config["source_registry"]'),
            ('overrides.get("sources", {})', 'overrides.get("source_registry", {})'),
        ],
        "scripts/family_tools_v1_render.py": [
            ('tool["sources"]', 'tool["source_refs"]'),
            ("tool['sources']", "tool['source_refs']"),
        ],
        "scripts/publish_family_guide_special_education_tools_v1.py": [
            ('t["sources"]', 't["source_refs"]'),
            ("t['sources']", "t['source_refs']"),
        ],
    }
    for relative, replacements in updates.items():
        path = ROOT / relative
        if patch_text(path, replacements):
            changed.append(relative)

    women = ROOT / "scripts/publish_women_youth_v406.py"
    patterns = [
        (r'\b(page|item|entry|record)\["sources"\]', r'\1["source_refs"]'),
        (r"\b(page|item|entry|record)\['sources'\]", r"\1['source_refs']"),
        (r'\b(page|item|entry|record)\.get\("sources"', r'\1.get("source_refs"'),
        (r"\b(page|item|entry|record)\.get\('sources'", r"\1.get('source_refs'"),
    ]
    if patch_text(women, [], patterns):
        changed.append(women.relative_to(ROOT).as_posix())
    return changed


def validate() -> None:
    evidence = json.loads((ROOT / "data/content-expansion-v1/official-evidence.json").read_text(encoding="utf-8"))
    assert "source_registry" in evidence and "sources" not in evidence
    assert all("source_refs" in item and "sources" not in item for item in evidence["profiles"])

    overrides = json.loads((ROOT / "data/content-expansion-v1/official-evidence-overrides.json").read_text(encoding="utf-8"))
    assert all("source_refs" in item and "sources" not in item for item in overrides["profiles"])

    for path in (ROOT / "content/family-guide-special-education-tools-v1").glob("tools-*.json"):
        tools = json.loads(path.read_text(encoding="utf-8"))
        assert all("source_refs" in item and "sources" not in item for item in tools)

    women_youth = json.loads((ROOT / "content/v406/women-youth-expansion-ar.json").read_text(encoding="utf-8"))
    assert all("source_refs" in item and "sources" not in item for item in women_youth["pages"])


def main() -> None:
    changed = [
        *migrate_expansion_evidence(),
        *migrate_family_tools(),
        *migrate_women_youth(),
        *migrate_consumers(),
    ]
    validate()
    print(json.dumps({"changed": sorted(changed), "count": len(changed)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
