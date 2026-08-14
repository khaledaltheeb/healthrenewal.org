#!/usr/bin/env python3
"""Publish a complete, deterministic sitemap and an open robots policy.

Discovery is path-authoritative. Canonical metadata is used only as a safety
signal: pages explicitly canonicalized to an unrelated external host are
excluded, while relative, current-domain, and trusted legacy/stale first-party
canonicals remain eligible. Emitted URLs always use the real published path on
https://healthrenewal.org, so old metadata cannot collapse or duplicate routes.

Before discovery, close the institutional internal-route contract so parent hubs,
learning paths, and legacy aliases exist before sitemap enumeration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree as ET

from repair_internal_routes_v1 import apply as repair_internal_routes

BASE_URL = "https://healthrenewal.org/"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
MAX_URLS = 50_000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
REPORT_VERSION = 362

EXCLUDED_DIR_PARTS = {
    ".git", ".github", ".idea", ".vscode", "node_modules", "vendor",
    "tests", "test", "fixtures", "fixture", "scripts", "coverage", "tmp", "temp",
}
EXCLUDED_FILENAMES = {"404.html", "403.html", "500.html", "offline.html"}
VERIFICATION_FILE_RE = re.compile(
    r"^(?:google[a-z0-9_-]+|bing[a-z0-9_-]+|yandex_[a-z0-9_-]+)\.html$", re.IGNORECASE
)
NOINDEX_META_RE = re.compile(
    r"<meta\b(?=[^>]*\bname\s*=\s*(['\"])(?:robots|googlebot|bingbot)\1)"
    r"(?=[^>]*\bcontent\s*=\s*(['\"])[^'\"]*\bnoindex\b[^'\"]*\2)[^>]*>",
    re.IGNORECASE,
)
CANONICAL_RE = re.compile(
    r"<link\b(?=[^>]*\brel\s*=\s*(['\"])[^'\"]*\bcanonical\b[^'\"]*\1)"
    r"(?=[^>]*\bhref\s*=\s*(['\"])([^'\"]+)\2)[^>]*>",
    re.IGNORECASE,
)
TRUSTED_FIRST_PARTY_HOSTS = {
    "healthrenewal.org",
    "www.healthrenewal.org",
    "khaledaltheeb.github.io",
    "pterminology.com",
    "www.pterminology.com",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="Published site root")
    parser.add_argument("--minimum-urls", type=int, default=1)
    return parser.parse_args()


def is_excluded(path: Path, root: Path) -> tuple[bool, str | None]:
    relative = path.relative_to(root)
    parts = {part.lower() for part in relative.parts[:-1]}
    if parts & EXCLUDED_DIR_PARTS:
        return True, "excluded_directory"
    filename = relative.name.lower()
    if filename in EXCLUDED_FILENAMES:
        return True, "error_or_offline_page"
    if VERIFICATION_FILE_RE.fullmatch(filename):
        return True, "search_verification_file"
    return False, None


def route_for(path: Path, root: Path) -> str:
    relative = PurePosixPath(path.relative_to(root).as_posix())
    if relative.as_posix() == "index.html":
        route = ""
    elif relative.name == "index.html":
        route = relative.parent.as_posix().rstrip("/") + "/"
    else:
        route = relative.as_posix()
    return quote(route, safe="/-._~")


def canonical_is_safe(value: str) -> bool:
    """Return True for relative/current/known first-party historical canonicals."""
    parsed = urlsplit(value.strip())
    if not parsed.scheme and not parsed.netloc:
        return True
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in TRUSTED_FIRST_PARTY_HOSTS


def discover(root: Path) -> tuple[list[str], dict[str, list[str] | int]]:
    urls: list[str] = []
    excluded: dict[str, list[str]] = {
        "excluded_directory": [],
        "error_or_offline_page": [],
        "search_verification_file": [],
        "explicit_noindex": [],
        "external_canonical": [],
        "unreadable": [],
    }
    html_files = sorted(path for path in root.rglob("*.html") if path.is_file())

    for path in html_files:
        relative = path.relative_to(root).as_posix()
        skip, reason = is_excluded(path, root)
        if skip:
            assert reason is not None
            excluded[reason].append(relative)
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            excluded["unreadable"].append(relative)
            continue
        if NOINDEX_META_RE.search(source):
            excluded["explicit_noindex"].append(relative)
            continue
        canonical = CANONICAL_RE.search(source)
        if canonical and not canonical_is_safe(canonical.group(3)):
            excluded["external_canonical"].append(relative)
            continue
        urls.append(BASE_URL + route_for(path, root))

    counts = Counter(urls)
    duplicates = sorted(url for url, count in counts.items() if count > 1)
    if duplicates:
        raise SystemExit(f"Duplicate public routes discovered: {duplicates[:25]}")
    return sorted(counts), {"html_files_discovered": len(html_files), **excluded}


def indent_xml(element: ET.Element, level: int = 0) -> None:
    padding = "\n" + "  " * level
    if len(element):
        if not element.text or not element.text.strip():
            element.text = padding + "  "
        for child in element:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = padding
    if level and (not element.tail or not element.tail.strip()):
        element.tail = padding


def xml_bytes_for_urls(urls: list[str]) -> bytes:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = url
    indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def xml_bytes_for_index() -> bytes:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}sitemapindex")
    node = ET.SubElement(root, f"{{{SITEMAP_NS}}}sitemap")
    ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = BASE_URL + "sitemap.xml"
    indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def validate_sitemap(payload: bytes, expected_urls: list[str]) -> None:
    if len(payload) > MAX_UNCOMPRESSED_BYTES:
        raise SystemExit("sitemap.xml exceeds the 50 MiB protocol limit")
    parsed = ET.fromstring(payload)
    namespace = {"sm": SITEMAP_NS}
    actual = [node.text or "" for node in parsed.findall("sm:url/sm:loc", namespace)]
    if actual != expected_urls:
        raise SystemExit("sitemap.xml URL order or coverage differs from discovery")
    if len(actual) > MAX_URLS:
        raise SystemExit("sitemap.xml exceeds the 50,000 URL protocol limit")
    for url in actual:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != "healthrenewal.org":
            raise SystemExit(f"Invalid sitemap host or scheme: {url}")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Site root does not exist: {root}")

    route_repair = repair_internal_routes(root)
    if route_repair.get("status") != "passed":
        raise SystemExit(f"Internal route repair failed: {route_repair}")

    urls, discovery = discover(root)
    if len(urls) < args.minimum_urls:
        raise SystemExit(f"Only {len(urls)} real indexable URLs discovered; minimum is {args.minimum_urls}")

    sitemap = xml_bytes_for_urls(urls)
    validate_sitemap(sitemap, urls)
    sitemap_index = xml_bytes_for_index()
    ET.fromstring(sitemap_index)
    robots = ("User-agent: *\nAllow: /\n\n" f"Sitemap: {BASE_URL}sitemap.xml\n").encode("utf-8")

    (root / "sitemap.xml").write_bytes(sitemap)
    (root / "sitemap-index.xml").write_bytes(sitemap_index)
    (root / "robots.txt").write_bytes(robots)

    report_dir = root / "api"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "version": REPORT_VERSION,
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "base_url": BASE_URL,
        "sitemap": "sitemap.xml",
        "sitemap_index": "sitemap-index.xml",
        "robots": "robots.txt",
        "real_indexable_urls": len(urls),
        "claimed_target_urls": 3600,
        "target_reached": len(urls) >= 3600,
        "html_files_discovered": discovery.pop("html_files_discovered"),
        "excluded_counts": {key: len(value) for key, value in discovery.items()},
        "excluded_pages": discovery,
        "internal_route_repair": {
            "status": route_repair["status"],
            "generatedRoutes": route_repair["generatedRoutes"],
            "hubs": route_repair["hubs"],
            "learningPaths": route_repair["learningPaths"],
            "aliases": route_repair["aliases"],
            "missingOccurrences": route_repair["audit"]["missingOccurrences"],
        },
        "protocol": {
            "maximum_urls_per_sitemap": MAX_URLS,
            "maximum_uncompressed_bytes": MAX_UNCOMPRESSED_BYTES,
            "actual_bytes": len(sitemap),
            "https_only": True,
            "single_host": "healthrenewal.org",
            "duplicates": 0,
            "legacy_urls": 0,
            "path_authoritative": True,
        },
        "sha256": {
            "sitemap.xml": hashlib.sha256(sitemap).hexdigest(),
            "sitemap-index.xml": hashlib.sha256(sitemap_index).hexdigest(),
            "robots.txt": hashlib.sha256(robots).hexdigest(),
        },
        "sample": {"first": urls[:10], "last": urls[-10:]},
    }
    (report_dir / "sitemap-completeness-v360.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "passed",
        "real_indexable_urls": len(urls),
        "html_files_discovered": report["html_files_discovered"],
        "target_reached": report["target_reached"],
        "sitemap_bytes": len(sitemap),
        "internal_route_repair": report["internal_route_repair"],
        "root": str(root),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
