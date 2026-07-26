from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE = "https://khaledaltheeb.github.io/pterminology-site/"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
OUT = SITE / "api" / "seo-surface-audit-v278.json"


def one(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def local_path(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc and url.startswith(BASE):
        value = parsed.path.removeprefix("/pterminology-site/")
    elif not parsed.scheme and not parsed.netloc:
        value = parsed.path.lstrip("/")
        if value.startswith("pterminology-site/"):
            value = value.removeprefix("pterminology-site/")
    else:
        return None
    value = unquote(value).split("#", 1)[0].split("?", 1)[0]
    return value


def resolves(path: str) -> bool:
    target = SITE / path
    return target.is_file() or (target / "index.html").is_file()


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing generated site: {SITE}")

    errors: list[str] = []
    warnings: list[str] = []
    pages: list[dict[str, object]] = []
    titles: defaultdict[str, list[str]] = defaultdict(list)
    descriptions: defaultdict[str, list[str]] = defaultdict(list)
    canonicals: defaultdict[str, list[str]] = defaultdict(list)
    broken_links: list[dict[str, str]] = []

    html_files = sorted(SITE.rglob("*.html"))
    for page in html_files:
        rel = page.relative_to(SITE).as_posix()
        text = page.read_text(encoding="utf-8", errors="replace")
        title = one(r"<title>(.*?)</title>", text)
        description = one(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', text)
        canonical = one(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', text)
        robots = one(r'<meta\s+name=["\']robots["\']\s+content=["\'](.*?)["\']', text).lower()
        h1_count = len(re.findall(r"<h1\b", text, re.I))
        jsonld_blocks = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', text, re.I | re.S)

        if not title:
            errors.append(f"{rel}: missing title")
        if not description:
            errors.append(f"{rel}: missing meta description")
        if not canonical:
            errors.append(f"{rel}: missing canonical")
        if h1_count != 1:
            errors.append(f"{rel}: expected one H1, found {h1_count}")
        if "noindex" in robots and not rel.startswith(("404", "offline")):
            errors.append(f"{rel}: unintended noindex")
        if canonical and not canonical.startswith(BASE):
            errors.append(f"{rel}: canonical outside deployment base: {canonical}")
        if not jsonld_blocks:
            errors.append(f"{rel}: missing JSON-LD")
        for index, block in enumerate(jsonld_blocks, start=1):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: invalid JSON-LD block {index}: {exc}")

        if title:
            titles[title.casefold()].append(rel)
        if description:
            descriptions[description.casefold()].append(rel)
        if canonical:
            canonicals[canonical].append(rel)

        for href in re.findall(r'<a\b[^>]*\shref=["\']([^"\']+)["\']', text, re.I):
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            path = local_path(href)
            if path is not None and not resolves(path):
                broken_links.append({"page": rel, "href": href})

        pages.append({
            "path": rel,
            "title": title,
            "description_length": len(description),
            "canonical": canonical,
            "h1_count": h1_count,
            "jsonld_blocks": len(jsonld_blocks),
            "robots": robots,
        })

    for label, groups in (("title", titles), ("description", descriptions), ("canonical", canonicals)):
        for value, paths in groups.items():
            if value and len(paths) > 1:
                errors.append(f"duplicate {label}: {paths}")

    if broken_links:
        errors.extend(f"{item['page']}: broken internal link {item['href']}" for item in broken_links)

    sitemap_urls: set[str] = set()
    sitemap_files = sorted(SITE.glob("sitemap*.xml"))
    if not sitemap_files:
        errors.append("no sitemap XML files generated")
    for sitemap in sitemap_files:
        try:
            root = ET.parse(sitemap).getroot()
        except ET.ParseError as exc:
            errors.append(f"{sitemap.name}: invalid XML: {exc}")
            continue
        for node in root.iter():
            if node.tag.endswith("loc") and node.text:
                sitemap_urls.add(node.text.strip())

    indexable_canonicals = {
        str(page["canonical"])
        for page in pages
        if page["canonical"] and "noindex" not in str(page["robots"])
    }
    missing_from_sitemaps = sorted(indexable_canonicals - sitemap_urls)
    if missing_from_sitemaps:
        errors.extend(f"canonical missing from sitemaps: {url}" for url in missing_from_sitemaps)

    robots_path = SITE / "robots.txt"
    if not robots_path.is_file():
        errors.append("robots.txt missing")
    else:
        robots_text = robots_path.read_text(encoding="utf-8", errors="replace")
        if "Sitemap:" not in robots_text:
            errors.append("robots.txt has no Sitemap directive")
        if "Disallow: /" in robots_text:
            errors.append("robots.txt blocks the whole site")

    manifest_path = SITE / "manifest.webmanifest"
    if not manifest_path.is_file():
        errors.append("manifest.webmanifest missing")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key in ("name", "short_name", "start_url", "display", "icons"):
                if not manifest.get(key):
                    errors.append(f"manifest missing {key}")
        except json.JSONDecodeError as exc:
            errors.append(f"manifest invalid JSON: {exc}")

    feed_path = SITE / "magazine" / "feed.xml"
    if not feed_path.is_file():
        warnings.append("magazine/feed.xml is not present in this artifact")
    else:
        try:
            feed = ET.parse(feed_path).getroot()
            items = feed.findall("./channel/item")
            if not items:
                errors.append("RSS feed has no items")
            for item in items:
                if item.findtext("link", "").strip() == "":
                    errors.append("RSS item missing link")
        except ET.ParseError as exc:
            errors.append(f"RSS invalid XML: {exc}")

    report = {
        "contract": 278,
        "html_pages": len(html_files),
        "unique_titles": len(titles),
        "unique_descriptions": len(descriptions),
        "unique_canonicals": len(canonicals),
        "sitemap_files": [item.name for item in sitemap_files],
        "sitemap_urls": len(sitemap_urls),
        "broken_internal_links": len(broken_links),
        "missing_from_sitemaps": len(missing_from_sitemaps),
        "errors": errors,
        "warnings": warnings,
        "pages": pages,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key != "pages"}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(f"SEO surface audit failed with {len(errors)} error(s)")


if __name__ == "__main__":
    main()
