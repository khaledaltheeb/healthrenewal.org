#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from care_guides_v234_core import (
    BASE, CORE_CATEGORY_BY_SLUG, SECTION_ORDER, category_map, compact,
    normalize_guide, valid_date, words,
)
from care_guides_v234_pages import guide_page, index_page

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()
MANIFEST = ROOT / "content" / "v234" / "care-guides-manifest-ar.json"
ASSET_FILES = ("care-guides-v234.css", "care-guides-v234.js")
CORE_FILES = (
    ROOT / "content" / "v18" / "care-guides-ar.json",
    ROOT / "content" / "v18" / "care-guides-adhd-ar.json",
    ROOT / "content" / "v18" / "care-guides-autism-ar.json",
)
BLOCKED_REVIEW_STATUSES = {"needs-specialist-review"}

def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def load_all() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    expansion = load_payload(MANIFEST)
    slugs = expansion.get("guide_slugs", [])
    files = expansion.get("guide_files", [])
    if len(slugs) != len(set(slugs)) or not files:
        raise SystemExit("Invalid v234 guide manifest")
    expansion["guides"] = []
    for relative in files:
        payload = load_payload(MANIFEST.parent / relative)
        expansion["guides"].extend(payload.get("guides", [payload]))
    if [guide.get("slug") for guide in expansion["guides"]] != slugs:
        raise SystemExit("v234 guide files do not match the ordered manifest")
    guides: list[dict[str, Any]] = []
    for path in CORE_FILES:
        guides.extend(load_payload(path).get("guides", []))
    guides.extend(expansion["guides"])
    blocked = [g for g in guides if g.get("review_status") in BLOCKED_REVIEW_STATUSES]
    allowed = [normalize_guide(g) for g in guides if g not in blocked]
    return expansion, allowed, blocked

def validate(expansion: dict[str, Any], guides: list[dict[str, Any]], blocked: list[dict[str, Any]]) -> None:
    category_ids = {item["id"] for item in expansion.get("categories", [])}
    if len(expansion.get("guides", [])) < 12:
        raise SystemExit("v234 must contain at least twelve expansion guides")
    slugs = [g.get("slug", "") for g in guides + blocked]
    titles = [g.get("title", "") for g in guides + blocked]
    if len(slugs) != len(set(slugs)) or len(titles) != len(set(titles)):
        raise SystemExit("Duplicate care-guide slug or title")
    for guide in guides + blocked:
        slug = guide.get("slug", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise SystemExit(f"Invalid slug: {slug}")
        if len(compact(guide.get("summary", ""))) < 90:
            raise SystemExit(f"Thin summary: {slug}")
        if guide.get("category", CORE_CATEGORY_BY_SLUG.get(slug, "family-care")) not in category_ids:
            raise SystemExit(f"Unknown category: {slug}")
        sources = guide.get("sources", [])
        if len(sources) < 2:
            raise SystemExit(f"Guide requires two sources: {slug}")
        for source in sources:
            parsed = urlparse(source.get("url", ""))
            if parsed.scheme != "https" or not parsed.netloc:
                raise SystemExit(f"Non-HTTPS source: {slug}")
        populated = [key for key in SECTION_ORDER if isinstance(guide.get(key), list) and guide.get(key)]
        if len(populated) < 2:
            raise SystemExit(f"Guide has too few practical sections: {slug}")
    for guide in expansion["guides"]:
        if guide.get("review_status") != "internally-reviewed":
            raise SystemExit(f"Dishonest v234 review status: {guide['slug']}")
        if guide.get("external_specialist_review") is not False:
            raise SystemExit(f"v234 must not claim specialist review: {guide['slug']}")
        if len([key for key in SECTION_ORDER if guide.get(key)]) < 5:
            raise SystemExit(f"v234 guide lacks depth: {guide['slug']}")
    if not blocked:
        raise SystemExit("Safety fixture disappeared; at least one specialist-review guide should remain blocked")

def read_extension_urls(site: Path, known_slugs: set[str]) -> list[str]:
    path = site / "sitemap-care-guides.xml"
    if not path.is_file():
        return []
    urls: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    for node in root.findall("{*}url/{*}loc"):
        url = compact(node.text or "")
        if not url.startswith(BASE + "care-guides/") or url == BASE + "care-guides/":
            continue
        relative = url.removeprefix(BASE).strip("/")
        slug = relative.split("/")[-1]
        if slug in known_slugs:
            continue
        if (site / relative / "index.html").is_file():
            urls.append(url)
    return sorted(set(urls))

def write_sitemap(site: Path, guides: list[dict[str, Any]], extension_urls: list[str]) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    urlset = ET.Element(f"{{{namespace}}}urlset")
    entries: list[tuple[str, str, str]] = [(BASE + "care-guides/", TODAY, "0.95")]
    entries.extend(
        (BASE + "care-guides/" + guide["slug"] + "/", guide.get("reviewed_at") if valid_date(guide.get("reviewed_at")) else TODAY, "0.82")
        for guide in guides
    )
    entries.extend((url, TODAY, "0.75") for url in extension_urls)
    seen: set[str] = set()
    for url, modified, priority in entries:
        if url in seen:
            continue
        seen.add(url)
        item = ET.SubElement(urlset, f"{{{namespace}}}url")
        ET.SubElement(item, f"{{{namespace}}}loc").text = url
        ET.SubElement(item, f"{{{namespace}}}lastmod").text = modified
        ET.SubElement(item, f"{{{namespace}}}changefreq").text = "monthly"
        ET.SubElement(item, f"{{{namespace}}}priority").text = priority
    ET.ElementTree(urlset).write(site / "sitemap-care-guides.xml", encoding="utf-8", xml_declaration=True)
    return len(seen)

def write_robots(site: Path) -> None:
    content = (
        "User-agent: *\n"
        "Allow: /pterminology-site/\n"
        "Disallow: /pterminology-site/api/\n\n"
        f"Sitemap: {BASE}sitemap.xml\n"
        f"Sitemap: {BASE}sitemap-care-guides.xml\n"
    )
    (site / "robots.txt").write_text(content, encoding="utf-8")

def metadata_audit(output: Path) -> dict[str, Any]:
    pages = sorted(output.rglob("index.html"))
    titles: set[str] = set()
    descriptions: set[str] = set()
    failures: list[str] = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        rel = page.relative_to(output.parent).as_posix()
        required = (
            '<meta name="description"', '<meta name="robots"', '<meta name="keywords"',
            '<link rel="canonical"', 'application/ld+json',
        )
        missing = [token for token in required if token not in text]
        if missing:
            failures.append(f"{rel}: missing {missing}")
        title_match = re.search(r"<title>(.*?)</title>", text, re.S)
        desc_match = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
        if not title_match or not desc_match:
            failures.append(f"{rel}: metadata parse failure")
            continue
        title = compact(title_match.group(1))
        desc = compact(desc_match.group(1))
        if title in titles:
            failures.append(f"{rel}: duplicate title")
        if desc in descriptions:
            failures.append(f"{rel}: duplicate description")
        titles.add(title)
        descriptions.add(desc)
    return {"pages": len(pages), "unique_titles": len(titles), "unique_descriptions": len(descriptions), "failures": failures}

def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    expansion, guides, blocked = load_all()
    validate(expansion, guides, blocked)
    categories = category_map(expansion)
    output = site / "care-guides"
    output.mkdir(parents=True, exist_ok=True)
    site_assets = site / "assets"
    site_assets.mkdir(parents=True, exist_ok=True)
    for name in ASSET_FILES:
        shutil.copy2(ROOT / "assets" / name, site_assets / name)
    known_slugs = {guide["slug"] for guide in guides} | {guide["slug"] for guide in blocked}
    extension_urls = read_extension_urls(site, known_slugs)
    for guide in blocked:
        shutil.rmtree(output / guide["slug"], ignore_errors=True)
    for guide in guides:
        page = output / guide["slug"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(guide_page(guide, categories, guides), encoding="utf-8")
    (output / "index.html").write_text(index_page(expansion, guides, len(blocked)), encoding="utf-8")
    sitemap_urls = write_sitemap(site, guides, extension_urls)
    write_robots(site)
    audit = metadata_audit(output)
    if audit["failures"]:
        raise SystemExit(f"Care-guide SEO audit failed: {audit['failures'][:10]}")
    page_count = len(list(output.rglob("index.html")))
    if page_count != sitemap_urls:
        raise SystemExit(f"Care-guide page/sitemap mismatch: pages={page_count}, urls={sitemap_urls}")
    blocked_routes = [
        guide["slug"] for guide in blocked
        if (output / guide["slug"] / "index.html").exists()
        or (BASE + "care-guides/" + guide["slug"] + "/") in (site / "sitemap-care-guides.xml").read_text(encoding="utf-8")
    ]
    if blocked_routes:
        raise SystemExit(f"Blocked guides leaked into production: {blocked_routes}")
    source_domains = sorted({urlparse(src["url"]).netloc for guide in guides for src in guide["sources"]})
    report = {
        "version": 234,
        "status": "passed",
        "review_status": "internally-reviewed",
        "external_specialist_review_completed": False,
        "source_guides": len(guides) + len(blocked),
        "published_known_guides": len(guides),
        "expansion_guides": len(expansion["guides"]),
        "blocked_review_guides": len(blocked),
        "blocked_review_slugs": [g["slug"] for g in blocked],
        "extension_guides_preserved": len(extension_urls),
        "guides": page_count - 1,
        "pages": page_count,
        "sitemap_urls": sitemap_urls,
        "categories": len(categories),
        "source_references": sum(len(g["sources"]) for g in guides),
        "source_domains": source_domains,
        "minimum_section_count": min(sum(1 for key in SECTION_ORDER if g.get(key)) for g in guides),
        "minimum_source_count": min(len(g["sources"]) for g in guides),
        "minimum_summary_words": min(words(g["summary"]) for g in guides),
        "seo": {
            "pages_checked": audit["pages"],
            "unique_titles": audit["unique_titles"],
            "unique_descriptions": audit["unique_descriptions"],
            "canonical_coverage": "100%",
            "robots_meta_coverage": "100%",
            "keywords_meta_coverage": "100%",
            "json_ld_coverage": "100%",
            "sitemap_parity": True,
            "robots_file": True,
            "assets": list(ASSET_FILES),
        },
        "safety": {
            "blocked_routes_absent": True,
            "specialist_review_claimed": False,
            "emergency_escalation_present": all(bool(g.get("emergency_note")) for g in expansion["guides"]),
            "diagnostic_positioning": False,
        },
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-v234.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    legacy_path = api / "care-guides-v21.json"
    legacy = load_payload(legacy_path) if legacy_path.is_file() else {}
    legacy.update({
        "version": legacy.get("version", 194),
        "guides": report["guides"],
        "pages": report["pages"],
        "sitemap_urls": report["sitemap_urls"],
        "all_have_sources": True,
        "all_have_unique_titles": True,
        "expansion_version": 234,
        "published_known_guides": report["published_known_guides"],
        "extension_guides_preserved": report["extension_guides_preserved"],
        "blocked_review_guides": report["blocked_review_guides"],
        "blocked_review_slugs": report["blocked_review_slugs"],
        "needs_specialist_review_published": False,
    })
    legacy_path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
