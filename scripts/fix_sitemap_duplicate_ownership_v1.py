#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)
INDEX = ROOT / "sitemap-index.xml"
BROAD = "sitemap-family-main.xml"
REPORT = ROOT / "reports/sitemap-duplicate-ownership-v1.json"

PREFIX_DESTINATIONS = {
    "accessibility": "sitemap-accessibility.xml",
    "ai-search": "sitemap-ai-search.xml",
    "family-guide": "sitemap-family-guide.xml",
    "learning-paths": "sitemap-family-learning-paths.xml",
    "magazine": "sitemap-family-magazine.xml",
    "provider-assessment-demo": "sitemap-family-provider-platform.xml",
    "care-guides": "sitemap-family-care-guides.xml",
    "comparisons": "sitemap-family-comparisons.xml",
    "daily-tools": "sitemap-family-tools.xml",
    "outside-the-box": "sitemap-outside-the-box-evidence.xml",
    "source-registry": "sitemap-source-registry.xml",
    "specialists-partners": "sitemap-specialists-partners.xml",
}


def local_filename(url: str) -> str:
    return Path(urlparse(url).path.lstrip("/")).name


def indexed_sitemaps() -> list[str]:
    tree = ET.parse(INDEX)
    return [
        local_filename((node.text or "").strip())
        for node in tree.findall("{*}sitemap/{*}loc")
        if (node.text or "").strip()
    ]


def path_segments(url: str) -> list[str]:
    return [part for part in urlparse(url).path.split("/") if part]


def is_urlset(path: Path) -> bool:
    try:
        return ET.parse(path).getroot().tag.endswith("urlset")
    except (ET.ParseError, OSError):
        return False


def load_urlset(filename: str) -> tuple[ET.ElementTree, dict[str, ET.Element]]:
    path = ROOT / filename
    if path.exists():
        tree = ET.parse(path)
        if not tree.getroot().tag.endswith("urlset"):
            raise ValueError(f"{filename} is not a URL-set sitemap")
    else:
        tree = ET.ElementTree(ET.Element(f"{{{NS}}}urlset"))
    nodes: dict[str, ET.Element] = {}
    for node in tree.getroot().findall("{*}url"):
        location = node.find("{*}loc")
        if location is not None and (location.text or "").strip():
            nodes[(location.text or "").strip()] = node
    return tree, nodes


def destination_for(url: str, existing_owners: list[str]) -> str:
    segments = path_segments(url)
    first = segments[0] if segments else "root"

    non_broad = [owner for owner in existing_owners if owner != BROAD]
    if non_broad:
        # Keep an existing specialist owner. Prefer the most specific named map.
        return sorted(
            non_broad,
            key=lambda name: (
                0 if "phase" in name else 1,
                0 if name.startswith("sitemap-sector-") else 1,
                len(name),
                name,
            ),
        )[0]

    if first == "special-needs":
        # Existing condition maps and the new guides use different specialist maps.
        if len(segments) > 1 and segments[1] == "guides":
            return "sitemap-family-special-needs.xml"
        return "sitemap-special-needs.xml"
    if first == "sectors":
        if len(segments) > 1 and segments[1] == "women":
            return "sitemap-sector-women.xml"
        if len(segments) > 1 and segments[1] == "youth":
            return "sitemap-sector-youth.xml"
        return "sitemap-family-sectors.xml"
    if first in PREFIX_DESTINATIONS:
        return PREFIX_DESTINATIONS[first]

    safe = re.sub(r"[^a-z0-9-]+", "-", first.lower()).strip("-") or "secondary"
    return f"sitemap-family-{safe}.xml"


def save_urlset(filename: str, tree: ET.ElementTree) -> None:
    root = tree.getroot()
    entries = list(root.findall("{*}url"))
    entries.sort(key=lambda item: item.findtext("{*}loc", default=""))
    for item in entries:
        root.remove(item)
    root.extend(entries)
    ET.indent(tree, space="  ")
    tree.write(ROOT / filename, encoding="utf-8", xml_declaration=True)


def ensure_index_entries(filenames: set[str]) -> None:
    tree = ET.parse(INDEX)
    root = tree.getroot()
    existing = {
        local_filename((node.text or "").strip())
        for node in root.findall("{*}sitemap/{*}loc")
        if (node.text or "").strip()
    }
    for filename in sorted(filenames - existing):
        item = ET.SubElement(root, f"{{{NS}}}sitemap")
        ET.SubElement(item, f"{{{NS}}}loc").text = f"{BASE}/{filename}"
    entries = list(root.findall("{*}sitemap"))
    entries.sort(key=lambda item: item.findtext("{*}loc", default=""))
    for item in entries:
        root.remove(item)
    root.extend(entries)
    ET.indent(tree, space="  ")
    tree.write(INDEX, encoding="utf-8", xml_declaration=True)


def collect_ownership(files: list[str]) -> tuple[dict[str, list[str]], dict[str, tuple[ET.ElementTree, dict[str, ET.Element]]]]:
    ownership: dict[str, list[str]] = defaultdict(list)
    loaded: dict[str, tuple[ET.ElementTree, dict[str, ET.Element]]] = {}
    for filename in files:
        path = ROOT / filename
        if not path.exists() or not is_urlset(path):
            continue
        tree, nodes = load_urlset(filename)
        loaded[filename] = (tree, nodes)
        for url in nodes:
            ownership[url].append(filename)
    return ownership, loaded


def main() -> None:
    files = indexed_sitemaps()
    ownership_before, loaded = collect_ownership(files)
    if BROAD not in loaded:
        raise SystemExit(f"missing broad URL-set sitemap: {BROAD}")

    broad_tree, broad_nodes = loaded[BROAD]
    broad_root = broad_tree.getroot()
    migrated: list[dict] = []
    created_maps: set[str] = set()
    touched: set[str] = {BROAD}

    for url, node in sorted(broad_nodes.items()):
        owners = ownership_before.get(url, [BROAD])
        segments = path_segments(url)
        is_child = len(segments) > 1
        has_other_owner = any(owner != BROAD for owner in owners)
        if not is_child and not has_other_owner:
            continue

        destination = destination_for(url, owners)
        if destination == BROAD:
            continue
        if destination not in loaded:
            tree, nodes = load_urlset(destination)
            loaded[destination] = (tree, nodes)
            created_maps.add(destination)
        destination_tree, destination_nodes = loaded[destination]
        if url not in destination_nodes:
            cloned = copy.deepcopy(node)
            destination_tree.getroot().append(cloned)
            destination_nodes[url] = cloned
        broad_root.remove(node)
        touched.add(destination)
        migrated.append({
            "url": url,
            "from": BROAD,
            "to": destination,
            "reason": "child-url" if is_child else "duplicate-root-owner",
        })

    # Resolve any remaining duplicate ownership by keeping the semantic owner.
    ensure_index_entries(created_maps)
    files = indexed_sitemaps()
    ownership_mid, loaded = collect_ownership(files)
    deduplicated: list[dict] = []
    for url, owners in sorted(ownership_mid.items()):
        if len(owners) < 2:
            continue
        keeper = destination_for(url, owners)
        if keeper not in owners:
            keeper = sorted(owners)[0]
        for owner in owners:
            if owner == keeper:
                continue
            tree, nodes = loaded[owner]
            node = nodes.get(url)
            if node is None:
                continue
            tree.getroot().remove(node)
            touched.add(owner)
            deduplicated.append({"url": url, "removedFrom": owner, "retainedIn": keeper})

    for filename in sorted(touched | created_maps):
        if filename in loaded:
            save_urlset(filename, loaded[filename][0])
    ensure_index_entries(created_maps)

    final_files = indexed_sitemaps()
    ownership_after, final_loaded = collect_ownership(final_files)
    duplicates_after = {url: owners for url, owners in ownership_after.items() if len(owners) > 1}
    broad_children = sorted(
        url for url in final_loaded[BROAD][1]
        if len(path_segments(url)) > 1
    )
    before_urls = set(ownership_before)
    after_urls = set(ownership_after)
    lost_urls = sorted(before_urls - after_urls)

    REPORT.parent.mkdir(exist_ok=True)
    payload = {
        "schemaVersion": "2.0.0",
        "indexedSitemapCountBefore": len(files),
        "indexedSitemapCountAfter": len(final_files),
        "migratedFromBroadMain": migrated,
        "deduplicated": deduplicated,
        "createdFamilyMaps": sorted(created_maps),
        "duplicatesAfter": duplicates_after,
        "broadChildUrlsAfter": broad_children,
        "lostUrls": lost_urls,
        "passed": not duplicates_after and not broad_children and not lost_urls,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not payload["passed"]:
        raise SystemExit(json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
