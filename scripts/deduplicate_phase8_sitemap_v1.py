#!/usr/bin/env python3
"""Keep phase 8 family-guide URLs in one indexed child sitemap only."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "sitemap-family-main.xml"
PHASE8 = ROOT / "sitemap-family-guide-phase8.xml"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)


def locs(path: Path) -> set[str]:
    tree = ET.parse(path)
    return {
        node.text.strip()
        for node in tree.getroot().findall(f"{{{NS}}}url/{{{NS}}}loc")
        if node.text and node.text.strip()
    }


def render_deduplicated() -> tuple[bytes, int]:
    phase8 = locs(PHASE8)
    if not phase8:
        raise SystemExit(f"No URLs found in {PHASE8.name}")

    tree = ET.parse(MAIN)
    root = tree.getroot()
    removed = 0
    for url in list(root.findall(f"{{{NS}}}url")):
        loc = url.find(f"{{{NS}}}loc")
        if loc is not None and loc.text and loc.text.strip() in phase8:
            root.remove(url)
            removed += 1

    remaining = {
        node.text.strip()
        for node in root.findall(f"{{{NS}}}url/{{{NS}}}loc")
        if node.text and node.text.strip()
    }
    overlap = remaining & phase8
    if overlap:
        raise SystemExit(
            "Phase-8 URLs still appear in the main sitemap: " + ", ".join(sorted(overlap))
        )

    ET.indent(tree, space="  ")
    rendered = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    return rendered, removed


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected, removed = render_deduplicated()
    current = MAIN.read_bytes()
    if args.check:
        if current != expected:
            print(f"{MAIN.name} is not in the deterministic deduplicated form")
            return 1
        print(f"{MAIN.name} has unique phase-8 ownership")
        return 0

    if current == expected:
        print(f"{MAIN.name} is already deduplicated")
        return 0

    MAIN.write_bytes(expected)
    print(f"Removed {removed} duplicate phase-8 URLs from {MAIN.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
