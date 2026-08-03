#!/usr/bin/env python3
"""Register Quick Information in the site's canonical sitemap index.

The repository uses one robots.txt sitemap declaration pointing to sitemap-index.xml.
This script removes duplicate Quick Information URLs from the general sitemap,
registers the dedicated section sitemap once, and restores the single-declaration
robots contract.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", SITEMAP_NS)


def q(tag: str) -> str:
    return f"{{{SITEMAP_NS}}}{tag}"


def normalize_root_sitemap() -> int:
    path = ROOT / "sitemap.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    removed = 0
    for node in list(root.findall(q("url"))):
        loc = node.find(q("loc"))
        if loc is not None and (loc.text or "").startswith(f"{BASE}/quick-info/"):
            root.remove(node)
            removed += 1
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return removed


def register_section_sitemap() -> None:
    path = ROOT / "sitemap-index.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    target = f"{BASE}/sitemap-quick-info.xml"
    entries = []
    for node in list(root.findall(q("sitemap"))):
        loc = node.find(q("loc"))
        value = (loc.text or "").strip() if loc is not None else ""
        if value == target:
            entries.append(node)
    for duplicate in entries[1:]:
        root.remove(duplicate)
    if not entries:
        node = ET.SubElement(root, q("sitemap"))
        ET.SubElement(node, q("loc")).text = target
    tree.write(path, encoding="utf-8", xml_declaration=True)


def normalize_robots() -> None:
    path = ROOT / "robots.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not line.strip().lower().startswith("sitemap:")]
    while lines and not lines[-1].strip():
        lines.pop()
    lines.extend(["", f"Sitemap: {BASE}/sitemap-index.xml"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate() -> dict:
    root_tree = ET.parse(ROOT / "sitemap.xml")
    quick_tree = ET.parse(ROOT / "sitemap-quick-info.xml")
    index_tree = ET.parse(ROOT / "sitemap-index.xml")

    root_urls = [
        (node.find(q("loc")).text or "").strip()
        for node in root_tree.getroot().findall(q("url"))
        if node.find(q("loc")) is not None
    ]
    quick_urls = [
        (node.find(q("loc")).text or "").strip()
        for node in quick_tree.getroot().findall(q("url"))
        if node.find(q("loc")) is not None
    ]
    index_urls = [
        (node.find(q("loc")).text or "").strip()
        for node in index_tree.getroot().findall(q("sitemap"))
        if node.find(q("loc")) is not None
    ]
    sitemap_lines = [
        line.strip()
        for line in (ROOT / "robots.txt").read_text(encoding="utf-8").splitlines()
        if line.strip().lower().startswith("sitemap:")
    ]

    assert len(quick_urls) == 151, len(quick_urls)
    assert len(quick_urls) == len(set(quick_urls)), "duplicate Quick Information URLs"
    assert not any(url.startswith(f"{BASE}/quick-info/") for url in root_urls)
    assert index_urls.count(f"{BASE}/sitemap-quick-info.xml") == 1
    assert sitemap_lines == [f"Sitemap: {BASE}/sitemap-index.xml"], sitemap_lines
    return {
        "quick_info_urls": len(quick_urls),
        "registered_in_sitemap_index": True,
        "duplicate_root_entries": 0,
        "robots_sitemap_declarations": 1,
    }


def main() -> None:
    removed = normalize_root_sitemap()
    register_section_sitemap()
    normalize_robots()
    report = validate()
    report["removed_from_general_sitemap"] = removed
    print(report)


if __name__ == "__main__":
    main()
