#!/usr/bin/env python3
"""Materialize the HTML-only surface used by heading and intent contracts.

A sitemap graph may legitimately expose non-HTML resources such as public JSON
registries. Those resources do not have H1/H2/H3 elements and must not be
misclassified as failed pages. This builder recursively reads the canonical
sitemap graph, retains only root, trailing-slash, and explicit .html URLs, and
fails on ambiguous extensionless routes rather than silently dropping them.
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

try:
    from .enforce_sitewide_heading_intent_v2 import DEFAULT_BASE_URLS, DEFAULT_ROOT, sitemap_urls
except ImportError:
    from enforce_sitewide_heading_intent_v2 import DEFAULT_BASE_URLS, DEFAULT_ROOT, sitemap_urls

NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)


def classify_url(url: str) -> str:
    path = urlparse(url).path
    if path == "/" or path.endswith("/") or path.lower().endswith(".html"):
        return "html"
    name = Path(path).name
    if "." in name:
        return "resource"
    return "ambiguous"


def build(source: Path, output: Path, base_urls: tuple[str, ...]) -> dict[str, object]:
    urls = sitemap_urls(DEFAULT_ROOT, source.resolve(), base_urls)
    html_urls: list[str] = []
    resources: list[str] = []
    ambiguous: list[str] = []
    for url in urls:
        kind = classify_url(url)
        if kind == "html":
            html_urls.append(url)
        elif kind == "resource":
            resources.append(url)
        else:
            ambiguous.append(url)
    if ambiguous:
        raise SystemExit("Ambiguous sitemap URLs without a page suffix or trailing slash:\n" + "\n".join(ambiguous))

    root = ET.Element(f"{{{NS}}}urlset")
    for url in sorted(set(html_urls)):
        item = ET.SubElement(root, f"{{{NS}}}url")
        ET.SubElement(item, f"{{{NS}}}loc").text = url
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return {
        "source_urls": len(urls),
        "html_urls": len(set(html_urls)),
        "non_html_resources": len(set(resources)),
        "ambiguous_urls": 0,
        "output": str(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_ROOT / "sitemap-index.xml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", action="append", dest="base_urls")
    args = parser.parse_args()
    report = build(args.source, args.output, tuple(args.base_urls or DEFAULT_BASE_URLS))
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
