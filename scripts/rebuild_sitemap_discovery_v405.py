#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

VERSION = 405
BASE_URL = "https://healthrenewal.org"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
INDEX_FILENAME = "sitemap-index.xml"
ROBOTS_FILENAME = "robots.txt"
REPORT_PATH = Path("api/sitemap-discovery-v405.json")
UNDERCOVERED_REPORT = Path("api/undercovered-content-v401.json")
REQUIRED_SITEMAPS = {
    "sitemap.xml",
    "sitemap-special-needs.xml",
    "sitemap-family-special-needs.xml",
    "sitemap-family-learning-paths.xml",
    "sitemap-family-main.xml",
}


@dataclass(frozen=True)
class SitemapDocument:
    path: Path
    kind: str
    locations: tuple[str, ...]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qname(name: str) -> str:
    return f"{{{SITEMAP_NS}}}{name}"


def validate_absolute_site_url(url: str, *, context: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "healthrenewal.org":
        raise ValueError(f"Invalid sitemap URL in {context}: {url}")
    if not parsed.path.startswith("/"):
        raise ValueError(f"Invalid sitemap path in {context}: {url}")


def read_sitemap(path: Path) -> SitemapDocument:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML sitemap {path.name}: {exc}") from exc

    kind = local_name(root.tag)
    if kind == "urlset":
        locations = tuple(
            (node.text or "").strip()
            for node in root.findall("{*}url/{*}loc")
            if (node.text or "").strip()
        )
    elif kind == "sitemapindex":
        locations = tuple(
            (node.text or "").strip()
            for node in root.findall("{*}sitemap/{*}loc")
            if (node.text or "").strip()
        )
    else:
        raise ValueError(f"Unsupported root element in {path.name}: {kind}")

    if not locations:
        raise ValueError(f"Empty sitemap document: {path.name}")
    if len(locations) != len(set(locations)):
        raise ValueError(f"Duplicate locations in sitemap: {path.name}")
    for location in locations:
        validate_absolute_site_url(location, context=path.name)
    return SitemapDocument(path=path, kind=kind, locations=locations)


def discover_sitemaps(site_root: Path) -> tuple[list[SitemapDocument], list[dict[str, str]]]:
    documents: list[SitemapDocument] = []
    rejected: list[dict[str, str]] = []
    for path in sorted(site_root.glob("sitemap*.xml"), key=lambda item: item.name):
        if path.name == INDEX_FILENAME or not path.is_file():
            continue
        try:
            documents.append(read_sitemap(path))
        except ValueError as exc:
            rejected.append({"file": path.name, "reason": str(exc)})

    if not documents:
        raise ValueError("No valid sitemap documents were discovered")

    discovered_names = {document.path.name for document in documents}
    missing_required = sorted(REQUIRED_SITEMAPS - discovered_names)
    if missing_required:
        raise ValueError(f"Required sitemap documents are missing or invalid: {missing_required}")

    rejected_required = sorted(
        item["file"] for item in rejected if item["file"] in REQUIRED_SITEMAPS
    )
    if rejected_required:
        raise ValueError(f"Required sitemap documents were rejected: {rejected_required}")
    return documents, rejected


def sitemap_sort_key(document: SitemapDocument) -> tuple[int, str]:
    if document.path.name == "sitemap.xml":
        return (0, document.path.name)
    if document.kind == "urlset":
        return (1, document.path.name)
    return (2, document.path.name)


def render_index(documents: Iterable[SitemapDocument]) -> bytes:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(qname("sitemapindex"))
    for document in sorted(documents, key=sitemap_sort_key):
        sitemap = ET.SubElement(root, qname("sitemap"))
        location = ET.SubElement(sitemap, qname("loc"))
        location.text = f"{BASE_URL}/{document.path.name}"
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    from io import BytesIO

    stream = BytesIO()
    tree.write(stream, encoding="utf-8", xml_declaration=True)
    return stream.getvalue() + b"\n"


def render_robots() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {BASE_URL}/{INDEX_FILENAME}\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n"
    )


def load_undercovered_urls(site_root: Path) -> tuple[set[str], dict]:
    report_path = site_root / UNDERCOVERED_REPORT
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed" or report.get("page_count") != 100:
        raise ValueError("The v401 undercovered-content report is not in a passed 100-page state")
    routes = report.get("routes")
    if not isinstance(routes, list) or len(routes) != 100 or len(routes) != len(set(routes)):
        raise ValueError("The v401 route contract is invalid")
    urls = {f"{BASE_URL}/{route.strip('/')}/" for route in routes}
    return urls, report


def build_report(
    documents: list[SitemapDocument],
    rejected: list[dict[str, str]],
    undercovered_urls: set[str],
    undercovered_report: dict,
) -> dict:
    urlset_documents = [document for document in documents if document.kind == "urlset"]
    nested_indexes = [document for document in documents if document.kind == "sitemapindex"]
    published_urls = {
        location
        for document in urlset_documents
        for location in document.locations
    }
    missing_undercovered = sorted(undercovered_urls - published_urls)
    if missing_undercovered:
        raise ValueError(
            f"The sitemap graph does not expose {len(missing_undercovered)} v401 routes: "
            f"{missing_undercovered[:5]}"
        )

    index_locations = [f"{BASE_URL}/{document.path.name}" for document in sorted(documents, key=sitemap_sort_key)]
    if len(index_locations) != len(set(index_locations)):
        raise ValueError("Duplicate sitemap documents in the generated index")

    return {
        "version": VERSION,
        "status": "passed",
        "base_url": BASE_URL,
        "index": INDEX_FILENAME,
        "robots": ROBOTS_FILENAME,
        "sitemap_count": len(documents),
        "urlset_count": len(urlset_documents),
        "nested_index_count": len(nested_indexes),
        "rejected_count": len(rejected),
        "rejected": rejected,
        "indexed_sitemaps": [document.path.name for document in sorted(documents, key=sitemap_sort_key)],
        "published_url_count": len(published_urls),
        "undercovered_page_count": undercovered_report["page_count"],
        "undercovered_routes_exposed": len(undercovered_urls),
        "undercovered_routes_missing": [],
        "required_sitemaps": sorted(REQUIRED_SITEMAPS),
        "quality_gates": {
            "all_required_sitemaps_present": True,
            "all_index_locations_unique": True,
            "all_sitemap_urls_https": True,
            "all_undercovered_routes_exposed": True,
            "robots_declares_sitemap_index": True,
            "deterministic_output": True,
        },
    }


def publish(site_root: Path) -> dict:
    site_root = site_root.resolve()
    documents, rejected = discover_sitemaps(site_root)
    undercovered_urls, undercovered_report = load_undercovered_urls(site_root)
    report = build_report(documents, rejected, undercovered_urls, undercovered_report)

    index_path = site_root / INDEX_FILENAME
    robots_path = site_root / ROBOTS_FILENAME
    report_path = site_root / REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)

    index_path.write_bytes(render_index(documents))
    robots_path.write_text(render_robots(), encoding="utf-8")
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Re-read the generated contract so malformed serialization cannot pass silently.
    generated_index = read_sitemap(index_path)
    if generated_index.kind != "sitemapindex":
        raise ValueError("Generated sitemap index has the wrong root type")
    expected_locations = {
        f"{BASE_URL}/{document.path.name}" for document in documents
    }
    if set(generated_index.locations) != expected_locations:
        raise ValueError("Generated sitemap index does not match the discovered sitemap set")
    robots = robots_path.read_text(encoding="utf-8")
    if f"Sitemap: {BASE_URL}/{INDEX_FILENAME}" not in robots:
        raise ValueError("robots.txt does not declare the sitemap index")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the complete sitemap discovery contract.")
    parser.add_argument("site", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
