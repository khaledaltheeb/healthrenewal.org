#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE = "https://healthrenewal.org"
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


def normalize_existing_url(url: str) -> str:
    path = unquote(urlparse(url.strip()).path).lstrip("/")
    if path == "pterminology-site":
        return ""
    if path.startswith("pterminology-site/"):
        return path[len("pterminology-site/"):]
    return path


def candidate_files(path: str) -> list[str]:
    if not path:
        return ["index.html"]
    if path.endswith("/"):
        return [path + "index.html"]
    output = [path]
    if not Path(path).suffix:
        output.extend([path + "/index.html", path + ".html"])
    return output


def resolve_existing_url(site: Path, url: str, eligible: set[str]) -> str | None:
    normalized = normalize_existing_url(url)
    for candidate in candidate_files(normalized):
        if candidate in eligible and (site / candidate).is_file():
            return candidate
    return None


def write_urlset(path: Path, urls: list[str]) -> None:
    rows = ["<?xml version='1.0' encoding='utf-8'?>", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        rows.extend(["  <url>", f"    <loc>{html.escape(url)}</loc>", "  </url>"])
    rows.append("</urlset>")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def rewrite_family_sitemaps(site: Path, eligible: set[str]) -> dict[str, int]:
    stats: dict[str, int] = {}
    for sitemap in sorted(site.glob("sitemap*.xml")):
        if sitemap.name in {"sitemap.xml", "sitemap-index.xml"}:
            continue
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        files = []
        for raw in LOC_RE.findall(text):
            resolved = resolve_existing_url(site, raw, eligible)
            if resolved and resolved not in files:
                files.append(resolved)
        urls = sorted(canonical_url(rel) for rel in files)
        write_urlset(sitemap, urls)
        stats[sitemap.name] = len(urls)
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="_site")
    args = parser.parse_args()
    site = Path(args.site).resolve()
    if not site.is_dir():
        raise SystemExit(f"Site directory missing: {site}")

    all_html = [
        p.relative_to(site).as_posix()
        for p in site.rglob("*")
        if p.is_file() and p.suffix.lower() in HTML_SUFFIXES
    ]
    eligible_list = indexable_html(site)
    eligible = set(eligible_list)
    canonical_urls = sorted(canonical_url(rel) for rel in eligible_list)

    legacy_loc_count = 0
    legacy_host_count = 0
    for sitemap in site.glob("sitemap*.xml"):
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        locs = LOC_RE.findall(text)
        legacy_loc_count += len(locs)
        legacy_host_count += sum("khaledaltheeb.github.io/pterminology-site" in loc for loc in locs)

    write_urlset(site / "sitemap.xml", canonical_urls)
    family_counts = rewrite_family_sitemaps(site, eligible)
    write_index(site)
    write_robots(site)

    post_files = list(site.glob("sitemap*.xml"))
    stale = []
    for sitemap in post_files:
        text = sitemap.read_text(encoding="utf-8", errors="replace")
        if "khaledaltheeb.github.io/pterminology-site" in text:
            stale.append(sitemap.name)

    root_urls = LOC_RE.findall((site / "sitemap.xml").read_text(encoding="utf-8"))
    report = {
        "schemaVersion": 1,
        "status": "passed" if not stale and len(root_urls) == len(eligible) else "failed",
        "htmlPages": len(all_html),
        "indexableHtmlPages": len(eligible),
        "canonicalRootSitemapUrls": len(root_urls),
        "legacyLocEntriesBefore": legacy_loc_count,
        "legacyGithubUrlsRemoved": legacy_host_count,
        "familySitemapsRewritten": len(family_counts),
        "familySitemapUrlCounts": family_counts,
        "staleLegacySitemaps": stale,
        "excludedHtmlPages": len(all_html) - len(eligible),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "sitemap-finalization-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if report["status"] != "passed":
        raise SystemExit(report)
    if set(root_urls) != set(canonical_urls):
        raise SystemExit("Root sitemap does not exactly match indexable HTML routes")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
