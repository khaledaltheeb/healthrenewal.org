#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ROBOTS = ROOT / "robots.txt"
PUBLIC_ORIGIN = "https://healthrenewal.org"
BASE_PATH = "/"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLATFORM_TIMEZONE = ZoneInfo("Asia/Amman")


class ContractError(RuntimeError):
    pass


def public_url_to_path(url: str) -> Path:
    parsed = urlparse(url)
    if f"{parsed.scheme}://{parsed.netloc}" != PUBLIC_ORIGIN:
        raise ContractError(f"Sitemap URL must remain on the canonical origin: {url}")
    if not parsed.path.startswith(BASE_PATH):
        raise ContractError(f"Sitemap URL must remain under {BASE_PATH}: {url}")
    if parsed.query or parsed.fragment:
        raise ContractError(f"Sitemap URL must not contain query or fragment: {url}")
    relative = parsed.path[len(BASE_PATH) :]
    if not relative or relative.endswith("/"):
        raise ContractError(f"Sitemap URL must identify an XML file: {url}")
    return ROOT / relative


def parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ContractError(f"Invalid XML in {path.relative_to(ROOT)}: {exc}") from exc


def platform_today() -> date:
    """Return the publishing date used by the platform, independent of runner timezone."""
    return datetime.now(PLATFORM_TIMEZONE).date()


def validate_lastmod(value: str, source: str) -> None:
    if not DATE_RE.fullmatch(value):
        raise ContractError(f"Invalid lastmod format in {source}: {value}")
    parsed = date.fromisoformat(value)
    if parsed > platform_today():
        raise ContractError(f"Future lastmod date in {source}: {value}")


def validate_urlset(path: Path, global_seen: dict[str, Path]) -> int:
    root = parse_xml(path)
    if root.tag != f"{{{SITEMAP_NS}}}urlset":
        raise ContractError(f"Child sitemap is not a urlset: {path.relative_to(ROOT)}")

    local_seen: set[str] = set()
    count = 0
    for node in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = (node.findtext(f"{{{SITEMAP_NS}}}loc") or "").strip()
        if not loc:
            raise ContractError(f"Missing loc in {path.relative_to(ROOT)}")
        if loc in local_seen:
            raise ContractError(f"Duplicate URL in {path.relative_to(ROOT)}: {loc}")
        local_seen.add(loc)

        first_source = global_seen.get(loc)
        if first_source is not None:
            raise ContractError(
                "URL appears in multiple child sitemaps: "
                f"{loc} ({first_source.relative_to(ROOT)} and {path.relative_to(ROOT)})"
            )
        global_seen[loc] = path

        parsed = urlparse(loc)
        if f"{parsed.scheme}://{parsed.netloc}" != PUBLIC_ORIGIN or not parsed.path.startswith(BASE_PATH):
            raise ContractError(f"Non-canonical URL in {path.relative_to(ROOT)}: {loc}")
        if parsed.query or parsed.fragment:
            raise ContractError(f"Indexed URL contains query or fragment: {loc}")
        lastmod = (node.findtext(f"{{{SITEMAP_NS}}}lastmod") or "").strip()
        if lastmod:
            validate_lastmod(lastmod, f"{path.relative_to(ROOT)} -> {loc}")
        count += 1

    if count == 0:
        raise ContractError(f"Empty sitemap: {path.relative_to(ROOT)}")
    return count


def main() -> int:
    robots = ROBOTS.read_text(encoding="utf-8")
    sitemap_lines = [
        line.split(":", 1)[1].strip()
        for line in robots.splitlines()
        if line.lower().startswith("sitemap:")
    ]
    if len(sitemap_lines) != 1:
        raise ContractError(
            f"robots.txt must expose exactly one sitemap entry point; found {len(sitemap_lines)}"
        )

    index_url = sitemap_lines[0]
    index_path = public_url_to_path(index_url)
    if not index_path.is_file():
        raise ContractError(
            f"robots.txt sitemap entry does not exist: {index_path.relative_to(ROOT)}"
        )

    root = parse_xml(index_path)
    if root.tag != f"{{{SITEMAP_NS}}}sitemapindex":
        raise ContractError("robots.txt must point to a sitemapindex, not a leaf urlset")

    child_urls: list[str] = []
    indexed_urls = 0
    global_seen: dict[str, Path] = {}
    for node in root.findall(f"{{{SITEMAP_NS}}}sitemap"):
        loc = (node.findtext(f"{{{SITEMAP_NS}}}loc") or "").strip()
        if not loc:
            raise ContractError("Sitemap index contains an entry without loc")
        if loc in child_urls:
            raise ContractError(f"Duplicate child sitemap in sitemap-index.xml: {loc}")
        child_urls.append(loc)
        lastmod = (node.findtext(f"{{{SITEMAP_NS}}}lastmod") or "").strip()
        if lastmod:
            validate_lastmod(lastmod, f"sitemap-index.xml -> {loc}")
        child_path = public_url_to_path(loc)
        if child_path == index_path:
            raise ContractError("Sitemap index must not reference itself")
        if not child_path.is_file():
            raise ContractError(
                f"Referenced child sitemap does not exist: {child_path.relative_to(ROOT)}"
            )
        indexed_urls += validate_urlset(child_path, global_seen)

    if not child_urls:
        raise ContractError("Sitemap index contains no child sitemaps")

    print(
        f"Sitemap discovery contract passed: robots -> {index_path.name}; "
        f"{len(child_urls)} child sitemaps; {indexed_urls} unique indexed URLs; "
        f"publishing date {platform_today().isoformat()} ({PLATFORM_TIMEZONE.key})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"Sitemap discovery contract failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
