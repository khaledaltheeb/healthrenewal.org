#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import enhance_sitewide_seo_v216_core_v235 as core

for _name in dir(core):
    if not _name.startswith("_"):
        globals().setdefault(_name, getattr(core, _name))

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DEDUPE_VERSION = 235

MANAGED_META_NAMES = {
    "description",
    "robots",
    "keywords",
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
    "twitter:image:alt",
}
MANAGED_META_PROPERTIES = {
    "og:type",
    "og:site_name",
    "og:locale",
    "og:title",
    "og:description",
    "og:url",
    "og:image",
    "og:image:alt",
}

_ORIGINAL_ENRICH_PAGE = core.enrich_page


def _managed_key(tag: str) -> tuple[str, str] | None:
    parsed = core.attrs(tag)
    lowered = tag.lstrip().lower()
    if lowered.startswith("<meta"):
        name = parsed.get("name", "").strip().lower()
        if name in MANAGED_META_NAMES:
            return "meta-name", name
        property_name = parsed.get("property", "").strip().lower()
        if property_name in MANAGED_META_PROPERTIES:
            return "meta-property", property_name
    if lowered.startswith("<link"):
        rel = parsed.get("rel", "").strip().lower()
        if rel == "canonical":
            return "link-rel", "canonical"
    return None


def _dedupe_managed_metadata(path: Path) -> Counter[str]:
    source = path.read_text(encoding="utf-8")
    head_match = core.HEAD_RE.search(source)
    if not head_match:
        return Counter()
    head = head_match.group(1)
    cursor = 0
    chunks: list[str] = []
    seen: set[tuple[str, str]] = set()
    removed: Counter[str] = Counter()

    for match in core.TAG_RE.finditer(head):
        key = _managed_key(match.group(0))
        if key is None or key not in seen:
            if key is not None:
                seen.add(key)
            continue
        chunks.append(head[cursor:match.start()])
        cursor = match.end()
        removed[f"{key[0]}:{key[1]}"] += 1

    if not removed:
        return removed
    chunks.append(head[cursor:])
    new_head = "".join(chunks)
    updated = source[: head_match.start(1)] + new_head + source[head_match.end(1) :]
    path.write_text(updated, encoding="utf-8")
    return removed


def enrich_page(path: Path) -> tuple[bool, dict[str, int | str | bool]]:
    core.SITE = SITE
    changed, result = _ORIGINAL_ENRICH_PAGE(path)
    removed = _dedupe_managed_metadata(path)
    removed_count = sum(removed.values())
    if removed_count:
        result["metadata_duplicates_removed"] = removed_count
        result["metadata_dedupe_version"] = DEDUPE_VERSION
        changed = True
    return changed, result


def main() -> int:
    core.SITE = SITE
    original = core.enrich_page
    core.enrich_page = enrich_page
    try:
        result = core.main()
    finally:
        core.enrich_page = original

    report_path = SITE / "api" / "sitewide-seo-v216.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["metadata_dedupe_version"] = DEDUPE_VERSION
        report.setdefault("policy", {})["remove_duplicate_managed_metadata"] = True
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
