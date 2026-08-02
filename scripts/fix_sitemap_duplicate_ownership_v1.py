#!/usr/bin/env python3
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)
INDEX = ROOT / "sitemap-index.xml"
BROAD = "sitemap-family-main.xml"
REPORT = ROOT / "reports/sitemap-duplicate-ownership-v1.json"


def local_filename(url: str) -> str:
    path = urlparse(url).path.lstrip("/")
    return Path(path).name


def indexed_sitemaps() -> list[str]:
    tree = ET.parse(INDEX)
    return [
        local_filename((node.text or "").strip())
        for node in tree.findall("{*}sitemap/{*}loc")
        if (node.text or "").strip()
    ]


def load_urls(filename: str) -> tuple[ET.ElementTree, dict[str, ET.Element]]:
    path = ROOT / filename
    tree = ET.parse(path)
    nodes: dict[str, ET.Element] = {}
    for node in tree.getroot().findall("{*}url"):
        location = node.find("{*}loc")
        if location is not None and (location.text or "").strip():
            nodes[(location.text or "").strip()] = node
    return tree, nodes


def duplicates(files: list[str]) -> dict[str, list[str]]:
    ownership: dict[str, list[str]] = defaultdict(list)
    for filename in files:
        _, urls = load_urls(filename)
        for url in urls:
            ownership[url].append(filename)
    return {url: owners for url, owners in ownership.items() if len(owners) > 1}


def main() -> None:
    files = indexed_sitemaps()
    before = duplicates(files)
    removable = {url: owners for url, owners in before.items() if BROAD in owners}
    broad_tree, broad_nodes = load_urls(BROAD)
    root = broad_tree.getroot()
    removed = []
    for url, owners in sorted(removable.items()):
        node = broad_nodes.get(url)
        if node is None:
            continue
        root.remove(node)
        removed.append({"url": url, "from": BROAD, "retainedIn": [item for item in owners if item != BROAD]})
    if removed:
        ET.indent(broad_tree, space="  ")
        broad_tree.write(ROOT / BROAD, encoding="utf-8", xml_declaration=True)
    after = duplicates(files)
    unresolved = {url: owners for url, owners in after.items()}
    REPORT.parent.mkdir(exist_ok=True)
    payload = {
        "schemaVersion": "1.0.0",
        "indexedSitemapCount": len(files),
        "duplicatesBefore": len(before),
        "removedFromBroadMain": removed,
        "duplicatesAfter": len(after),
        "unresolved": unresolved,
        "passed": not unresolved,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if unresolved:
        raise SystemExit(json.dumps({"unresolvedDuplicates": unresolved}, ensure_ascii=False, indent=2))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
