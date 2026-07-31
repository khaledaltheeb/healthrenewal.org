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
SITEMAP_INDEX_URL = f"{PUBLIC_ORIGIN}/sitemap-index.xml"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLATFORM_TIMEZONE = ZoneInfo("Asia/Amman")


class ContractError(RuntimeError):
    pass


def platform_today() -> date:
    return datetime.now(PLATFORM_TIMEZONE).date()


def validate_lastmod(value: str, context: str) -> None:
    if DATE_RE.fullmatch(value):
        parsed = date.fromisoformat(value)
    else:
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized).date()
        except ValueError as exc:
            raise ContractError(f"Invalid lastmod in {context}: {value}") from exc
    if parsed > platform_today():
        raise ContractError(f"Future lastmod in {context}: {value}")


def public_url_to_path(url: str) -> Path:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin != PUBLIC_ORIGIN:
        raise ContractError(f"Sitemap URL must remain on the canonical origin: {url}")
    if parsed.query or parsed.fragment:
        raise ContractError(f"Sitemap discovery URL contains query or fragment: {url}")
    relative = parsed.path.lstrip("/")
    if not relative:
        raise ContractError(f"Sitemap discovery URL has no file path: {url}")
    return ROOT / relative


def parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ContractError(f"Invalid XML file {path.relative_to(ROOT)}: {exc}") from exc


def validate_urlset(path: Path, global_seen: dict[str, Path]) -> int:
    root = parse_xml(path)
    if root.tag != f"{{{SITEMAP_NS}}}urlset":
        raise ContractError(f"Expected urlset in {path.relative_to(ROOT)}")

    count = 0
    local_seen: set[str] = set()
    for node in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = (node.findtext(f"{{{SITEMAP_NS}}}loc") or "").strip()
        if not loc:
            raise ContractError(f"Missing loc in {path.relative_to(ROOT)}")
        if loc in local_seen:
            raise ContractError(f"Duplicate URL inside {path.relative_to(ROOT)}: {loc}")
        local_seen.add(loc)
        if loc in global_seen:
            previous = global_seen[loc].relative_to(ROOT)
            raise ContractError(
                f"URL appears in multiple indexed child sitemaps: "
                f"{loc} ({previous}, {path.relative_to(ROOT)})"
            )
        global_seen[loc] = path

        parsed = urlparse(loc)
        if f"{parsed.scheme}://{parsed.netloc}" != PUBLIC_ORIGIN:
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


def read_robots_sitemaps() -> list[str]:
    robots = ROBOTS.read_text(encoding="utf-8")
    lines = [
        line.split(":", 1)[1].strip()
        for line in robots.splitlines()
        if line.strip().lower().startswith("sitemap:")
    ]
    if not lines:
        raise ContractError("robots.txt exposes no sitemap entry point")
    if len(lines) != len(set(lines)):
        raise ContractError("robots.txt contains duplicate Sitemap directives")
    for url in lines:
        path = public_url_to_path(url)
        if not path.is_file():
            raise ContractError(
                f"robots.txt sitemap entry does not exist: {path.relative_to(ROOT)}"
            )
    if SITEMAP_INDEX_URL not in lines:
        raise ContractError(
            f"robots.txt must expose the canonical sitemap index: {SITEMAP_INDEX_URL}"
        )
    return lines


def validate_canonical_index(index_path: Path) -> tuple[list[str], int]:
    root = parse_xml(index_path)
    if root.tag != f"{{{SITEMAP_NS}}}sitemapindex":
        raise ContractError("sitemap-index.xml must be a sitemapindex")

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
    return child_urls, indexed_urls


def validate_direct_robots_sitemaps(
    robots_sitemaps: list[str], child_urls: list[str]
) -> tuple[int, int]:
    """Validate standalone leaf sitemaps advertised directly in robots.txt.

    A direct leaf sitemap is a valid discovery endpoint and is not required to be
    listed again in the canonical sitemap index. It is validated independently
    because a compatibility/root sitemap may intentionally overlap URLs already
    grouped across indexed child sitemaps.
    """

    direct_entries = [url for url in robots_sitemaps if url != SITEMAP_INDEX_URL]
    validated_entries = 0
    validated_urls = 0
    for url in direct_entries:
        if url in child_urls:
            # Already fully validated through the canonical index.
            continue
        path = public_url_to_path(url)
        root = parse_xml(path)
        if root.tag != f"{{{SITEMAP_NS}}}urlset":
            raise ContractError(
                f"Additional robots sitemap must be a urlset: {path.relative_to(ROOT)}"
            )
        validated_urls += validate_urlset(path, {})
        validated_entries += 1
    return validated_entries, validated_urls


def main() -> int:
    robots_sitemaps = read_robots_sitemaps()
    index_path = public_url_to_path(SITEMAP_INDEX_URL)
    child_urls, indexed_urls = validate_canonical_index(index_path)
    direct_entries, direct_urls = validate_direct_robots_sitemaps(
        robots_sitemaps, child_urls
    )

    print(
        f"Sitemap discovery contract passed: {len(robots_sitemaps)} robots entries; "
        f"canonical index {index_path.name}; {len(child_urls)} child sitemaps; "
        f"{indexed_urls} unique indexed URLs; {direct_entries} standalone leaf "
        f"sitemap(s) with {direct_urls} independently validated URLs; publishing "
        f"date {platform_today().isoformat()} ({PLATFORM_TIMEZONE.key})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"Sitemap discovery contract failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
