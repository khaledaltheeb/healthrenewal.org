#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from publish_magazine_v201 import FEED_LIMIT, publish as publish_magazine

BASE = "https://healthrenewal.org"
LEGACY_BASE = "https://khaledaltheeb.github.io/pterminology-site"
HTML_SUFFIXES = {".html", ".htm"}
REDIRECT_RE = re.compile(r"http-equiv\s*=\s*[\"']refresh|location\.replace\s*\(", re.I)
NOINDEX_RE = re.compile(
    r"<meta[^>]+(?:name=[\"']robots[\"'][^>]+content=[\"'][^\"']*noindex|content=[\"'][^\"']*noindex[^\"']*[\"'][^>]+name=[\"']robots[\"'])",
    re.I,
)
LOC_RE = re.compile(r"<loc>(.*?)</loc>", re.I | re.S)
BLOCKED_PREFIXES = (
    "admin/",
    "account/",
    "auth/",
    "login/",
    "register/",
    "provider-assessment-platform/",
    "specialists-partners/admin/",
    "specialists-partners/portal/",
)
BLOCKED_FILES = {"404.html"}


def route_for(rel: str) -> str:
    path = Path(rel)
    if path.name == "index.html":
        parent = path.parent.as_posix().strip(".")
        return "/" if not parent else f"/{parent.strip('/')}/"
    return f"/{path.as_posix()}"


def canonical_url(rel: str) -> str:
    return BASE + route_for(rel)


def is_blocked(rel: str) -> bool:
    normalized = rel.replace("\\", "/").lstrip("/")
    return normalized in BLOCKED_FILES or normalized.startswith(BLOCKED_PREFIXES)


def is_indexable(path: Path, site: Path) -> bool:
    rel = path.relative_to(site).as_posix()
    if is_blocked(rel):
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if REDIRECT_RE.search(text) or NOINDEX_RE.search(text):
        return False
    return True


def indexable_html(site: Path) -> list[str]:
    output = []
    for path in sorted(site.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in HTML_SUFFIXES:
            continue
        if is_indexable(path, site):
            output.append(path.relative_to(site).as_posix())
    return output


def write_urlset(path: Path, urls: list[str]) -> None:
    rows = [
        "<?xml version='1.0' encoding='utf-8'?>",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        rows.extend(["  <url>", f"    <loc>{html.escape(url)}</loc>", "  </url>"])
    rows.append("</urlset>")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def canonicalize_family_sitemaps(site: Path) -> dict[str, int]:
    """Correct the legacy host without destroying specialized XML metadata.

    Some historical family sitemaps contain image metadata, lastmod, priority,
    and changefreq. The root sitemap is rebuilt from the final validated HTML
    inventory, while auxiliary maps retain their richer structure and only have
    the obsolete GitHub Pages base URL normalized to the canonical domain.
    """
    stats: dict[str, int] = {}
    for sitemap in sorted(site.glob("sitemap*.xml")):
        if sitemap.name in {"sitemap.xml", "sitemap-index.xml"}:
            continue
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        updated = text.replace(LEGACY_BASE, BASE)
        if updated != text:
            sitemap.write_text(updated, encoding="utf-8")
        stats[sitemap.name] = len(LOC_RE.findall(updated))
    return stats


def write_index(site: Path) -> None:
    (site / "sitemap-index.xml").write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <sitemap>\n"
        f"    <loc>{BASE}/sitemap.xml</loc>\n"
        "  </sitemap>\n"
        "</sitemapindex>\n",
        encoding="utf-8",
    )


def write_robots(site: Path) -> None:
    (site / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {BASE}/sitemap.xml\n",
        encoding="utf-8",
    )


def republish_release_derived_surfaces(site: Path) -> dict[str, object]:
    """Rebuild generated magazine surfaces after historical recovery.

    Historical recovery is allowed to restore rich HTML, but generated release
    artifacts must always be recreated from the current source contract so an
    older RSS/API/sitemap snapshot cannot survive into the deployable package.
    """
    report = publish_magazine(site)
    expected_items = min(FEED_LIMIT, report["research_summaries_published"])
    actual_items = report.get("robots", {}).get("rss_items")
    if actual_items != expected_items:
        raise SystemExit(
            f"Magazine RSS contract failed after release regeneration: "
            f"expected {expected_items}, got {actual_items}"
        )
    if report.get("unwired_research_pages") != 0:
        raise SystemExit(f"Magazine release contains unwired research pages: {report}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="_site")
    args = parser.parse_args()
    site = Path(args.site).resolve()
    if not site.is_dir():
        raise SystemExit(f"Site directory missing: {site}")

    magazine = republish_release_derived_surfaces(site)

    all_html = [
        p.relative_to(site).as_posix()
        for p in site.rglob("*")
        if p.is_file() and p.suffix.lower() in HTML_SUFFIXES
    ]
    eligible_list = indexable_html(site)
    canonical_urls = sorted(canonical_url(rel) for rel in eligible_list)

    legacy_loc_count = 0
    legacy_host_count = 0
    for sitemap in site.glob("sitemap*.xml"):
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        locs = LOC_RE.findall(text)
        legacy_loc_count += len(locs)
        legacy_host_count += sum(LEGACY_BASE in loc for loc in locs)

    write_urlset(site / "sitemap.xml", canonical_urls)
    family_counts = canonicalize_family_sitemaps(site)
    write_index(site)
    write_robots(site)

    stale = []
    for sitemap in site.glob("sitemap*.xml"):
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        if LEGACY_BASE in text:
            stale.append(sitemap.name)

    root_urls = LOC_RE.findall((site / "sitemap.xml").read_text(encoding="utf-8"))
    report = {
        "schemaVersion": 1,
        "status": "passed" if not stale and len(root_urls) == len(eligible_list) else "failed",
        "htmlPages": len(all_html),
        "indexableHtmlPages": len(eligible_list),
        "canonicalRootSitemapUrls": len(root_urls),
        "legacyLocEntriesBefore": legacy_loc_count,
        "legacyGithubUrlsRemoved": legacy_host_count,
        "familySitemapsCanonicalized": len(family_counts),
        "familySitemapUrlCounts": family_counts,
        "staleLegacySitemaps": stale,
        "excludedHtmlPages": len(all_html) - len(eligible_list),
        "magazineReleaseContract": {
            "version": magazine["version"],
            "researchSummariesPublished": magazine["research_summaries_published"],
            "rssItems": magazine["robots"]["rss_items"],
            "unwiredResearchPages": magazine["unwired_research_pages"],
        },
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "sitemap-finalization-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if report["status"] != "passed":
        raise SystemExit(report)
    if root_urls != canonical_urls:
        raise SystemExit("Root sitemap does not exactly match indexable HTML routes")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
