#!/usr/bin/env python3
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)

FAMILY_MAP = {
    "special-needs": "sitemap-family-special-needs.xml",
    "care-guides": "sitemap-family-care-guides.xml",
    "learning-paths": "sitemap-family-learning-paths.xml",
    "comparisons": "sitemap-family-comparisons.xml",
    "daily-tools": "sitemap-family-tools.xml",
}
ROOTS = {
    "special-needs": ROOT / "special-needs/guides",
    "care-guides": ROOT / "care-guides/evidence-guided",
    "learning-paths": ROOT / "learning-paths/evidence-guided",
    "comparisons": ROOT / "comparisons/disability-support",
    "daily-tools": ROOT / "daily-tools/disability-support",
}


def url_for(path: Path) -> str:
    relative = path.parent.relative_to(ROOT).as_posix()
    return f"{BASE}/{relative}/"


def load_or_create(path: Path) -> ET.ElementTree:
    if path.exists():
        return ET.parse(path)
    return ET.ElementTree(ET.Element(f"{{{NS}}}urlset"))


def update_family(sector: str, urls: list[str]) -> None:
    path = ROOT / FAMILY_MAP[sector]
    tree = load_or_create(path)
    root = tree.getroot()
    existing = {
        node.text.strip()
        for node in root.findall(f"{{{NS}}}url/{{{NS}}}loc")
        if node.text
    }
    for url in sorted(set(urls) - existing):
        item = ET.SubElement(root, f"{{{NS}}}url")
        ET.SubElement(item, f"{{{NS}}}loc").text = url
        ET.SubElement(item, f"{{{NS}}}lastmod").text = date.today().isoformat()
        ET.SubElement(item, f"{{{NS}}}changefreq").text = "monthly"
        ET.SubElement(item, f"{{{NS}}}priority").text = "0.78"
    entries = list(root.findall(f"{{{NS}}}url"))
    entries.sort(key=lambda element: element.findtext(f"{{{NS}}}loc", default=""))
    for element in entries:
        root.remove(element)
    root.extend(entries)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def ensure_sitemap_index() -> None:
    path = ROOT / "sitemap-index.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    existing = {
        node.text.strip()
        for node in root.findall(f"{{{NS}}}sitemap/{{{NS}}}loc")
        if node.text
    }
    for filename in FAMILY_MAP.values():
        url = f"{BASE}/{filename}"
        if url in existing:
            continue
        item = ET.SubElement(root, f"{{{NS}}}sitemap")
        ET.SubElement(item, f"{{{NS}}}loc").text = url
    entries = list(root.findall(f"{{{NS}}}sitemap"))
    entries.sort(key=lambda element: element.findtext(f"{{{NS}}}loc", default=""))
    for element in entries:
        root.remove(element)
    root.extend(entries)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    report = json.loads((ROOT / "reports/content-expansion-v1.json").read_text(encoding="utf-8"))
    expected = {item["url"] for item in report["pages"]}
    observed: set[str] = set()
    summary = {}
    for sector, directory in ROOTS.items():
        urls = [url_for(path) for path in directory.rglob("index.html")]
        update_family(sector, urls)
        observed.update(urls)
        summary[sector] = len(urls)
    if not expected.issubset(observed):
        raise SystemExit(f"generated page URLs missing from scoped roots: {sorted(expected-observed)[:5]}")
    ensure_sitemap_index()
    public = {
        "schemaVersion": "1.0.0",
        "generatedAt": date.today().isoformat(),
        "pageCount": report["pageCount"],
        "distribution": report["distribution"],
        "minimumObservedWords": report["minimumObservedWords"],
        "averageWords": report["averageWords"],
        "pages": report["pages"],
    }
    api_path = ROOT / "api/v1/content-expansion-v1.json"
    api_path.parent.mkdir(parents=True, exist_ok=True)
    api_path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": summary, "pageCount": report["pageCount"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
