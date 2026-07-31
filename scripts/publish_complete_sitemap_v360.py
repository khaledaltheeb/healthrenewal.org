#!/usr/bin/env python3
"""Publish a complete, deterministic sitemap and an open robots policy.

The publisher discovers real public HTML files under a site root, converts each
file to its public canonical route on https://healthrenewal.org, excludes error,
fixture, verification, and explicit noindex pages, then writes:

- sitemap.xml
- sitemap-index.xml
- robots.txt
- api/sitemap-completeness-v360.json

It deliberately never pads the sitemap with invented URLs. A sitemap is valid
only when every listed URL corresponds to a real public page.
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

BASE_URL = "https://healthrenewal.org/"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
MAX_URLS = 50_000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
REPORT_VERSION = 360

EXCLUDED_DIR_PARTS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "node_modules",
    "vendor",
    "tests",
    "test",
    "fixtures",
    "fixture",
    "scripts",
    "coverage",
    "tmp",
    "temp",
}
EXCLUDED_FILENAMES = {
    "404.html",
    "403.html",
    "500.html",
    "offline.html",
}
VERIFICATION_FILE_RE = re.compile(
    r"^(?:google[a-z0-9_-]+|bing[a-z0-9_-]+|yandex_[a-z0-9_-]+)\.html$",
    re.IGNORECASE,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="Published site root")
    parser.add_argument(
        "--minimum-urls",
        type=int,
        default=1,
        help="Fail if fewer real indexable URLs are discovered",
    )
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


def canonical_host_is_allowed(value: str) -> bool:
    """Accept current canonicals and the trusted pre-migration GitHub Pages host.

    The public URL is always derived from the real file path and emitted on the
    custom domain. The legacy host is accepted only so old canonical metadata
    cannot make every genuine page disappear from the migration sitemap.
    """

    parsed = urlsplit(value)
    if not parsed.scheme and not parsed.netloc:
        return True
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    if host == "healthrenewal.org":
        return True
    if host == "khaledaltheeb.github.io":
        legacy_path = parsed.path.rstrip("/")
        return legacy_path == "/pterminology-site" or legacy_path.startswith(
            "/pterminology-site/"
        )
    return False


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
        if canonical and not canonical_host_is_allowed(canonical.group(3).strip()):
            excluded["external_canonical"].append(relative)
            continue
        urls.append(BASE_URL + route_for(path, root))

    counts = Counter(urls)
    duplicates = sorted(url for url, count in counts.items() if count > 1)
    if duplicates:
        raise SystemExit(f"Duplicate canonical sitemap URLs: {duplicates[:25]}")
    urls = sorted(counts)
    return urls, {
        "html_files_discovered": len(html_files),
        **excluded,
    }


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
        if "khaledaltheeb.github.io" in url or "/pterminology-site/" in url:
            raise SystemExit(f"Legacy production URL survived: {url}")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Site root does not exist: {root}")

    urls, discovery = discover(root)
    if len(urls) < args.minimum_urls:
        raise SystemExit(
            f"Only {len(urls)} real indexable URLs discovered; minimum is {args.minimum_urls}"
        )

    sitemap = xml_bytes_for_urls(urls)
    validate_sitemap(sitemap, urls)
    sitemap_index = xml_bytes_for_index()
    ET.fromstring(sitemap_index)

    robots = (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {BASE_URL}sitemap.xml\n"
    ).encode("utf-8")

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
        "protocol": {
            "maximum_urls_per_sitemap": MAX_URLS,
            "maximum_uncompressed_bytes": MAX_UNCOMPRESSED_BYTES,
            "actual_bytes": len(sitemap),
            "https_only": True,
            "single_host": "healthrenewal.org",
            "duplicates": 0,
            "legacy_urls": 0,
        },
        "sha256": {
            "sitemap.xml": hashlib.sha256(sitemap).hexdigest(),
            "sitemap-index.xml": hashlib.sha256(sitemap_index).hexdigest(),
            "robots.txt": hashlib.sha256(robots).hexdigest(),
        },
        "sample": {
            "first": urls[:10],
            "last": urls[-10:],
        },
    }
    report_path = report_dir / "sitemap-completeness-v360.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": "passed",
                "real_indexable_urls": len(urls),
                "html_files_discovered": report["html_files_discovered"],
                "target_reached": report["target_reached"],
                "sitemap_bytes": len(sitemap),
                "root": str(root),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
