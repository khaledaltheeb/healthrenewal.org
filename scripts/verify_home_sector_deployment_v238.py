#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VERSION = 244
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
MINIMUM_HUB_WORDS = 2919
MINIMUM_ARTICLE_WORDS = 819
WORD_COUNT_METHOD = "semantic-visible-tokens-v244"


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in self.stack for tag in ("script", "style", "svg", "template", "noscript")):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.parts.append(value)


def fail(message: str, detail: Any | None = None) -> None:
    if detail is None:
        raise AssertionError(message)
    raise AssertionError(f"{message}: {detail}")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail("Missing JSON file", path.as_posix())
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("JSON root must be an object", path.as_posix())
    return data


def visible_words(source: str) -> int:
    parser = TextParser()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def source_articles(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    articles = data.get("articles")
    if not isinstance(articles, list) or len(articles) != 20:
        fail("Home-sector source must declare twenty articles", len(articles) if isinstance(articles, list) else articles)
    slugs: list[str] = []
    for item in articles:
        if not isinstance(item, dict):
            fail("Article entry must be an object", item)
        slug = item.get("slug")
        title = item.get("title")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            fail("Invalid home-sector slug", slug)
        if not isinstance(title, str) or len(title.strip()) < 8:
            fail("Invalid home-sector title", title)
        slugs.append(slug)
    if len(slugs) != len(set(slugs)):
        fail("Duplicate home-sector slugs", slugs)
    return articles


def _require_single(source: str, pattern: str, message: str, detail: str) -> None:
    matches = re.findall(pattern, source, flags=re.I | re.S)
    if len(matches) != 1:
        fail(message, {"page": detail, "count": len(matches)})


def _has_shell_component(source: str, component: str) -> bool:
    """Accept the current v10 shell and retained institutional shell variants."""
    if component == "header":
        patterns = (
            r'<header\b[^>]*\bid\s*=\s*["\']global-header["\']',
            r'<header\b[^>]*\bclass\s*=\s*["\'][^"\']*\bsite-header-v10\b[^"\']*["\']',
            r'<header\b[^>]*\bdata-platform-shell\s*=\s*["\']header["\']',
        )
    elif component == "footer":
        patterns = (
            r'<footer\b[^>]*\bid\s*=\s*["\']global-footer["\']',
            r'<footer\b[^>]*\bclass\s*=\s*["\'][^"\']*\bsite-footer-v10\b[^"\']*["\']',
            r'<footer\b[^>]*\bdata-platform-shell\s*=\s*["\']footer["\']',
        )
    else:
        raise ValueError(f"Unknown shell component: {component}")
    return any(re.search(pattern, source, flags=re.I | re.S) for pattern in patterns)


def validate_indexable_page(path: Path, canonical: str, *, article: bool, minimum_words: int) -> dict[str, Any]:
    if not path.is_file():
        fail("Missing deployed page", path.as_posix())
    source = path.read_text(encoding="utf-8")
    lower = source.lower()
    if len(re.findall(r"<h1\b", source, flags=re.I)) != 1:
        fail("Page must contain exactly one H1", path.as_posix())
    canonical_pattern = rf'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']{re.escape(canonical)}["\'][^>]*>'
    if len(re.findall(canonical_pattern, source, flags=re.I | re.S)) != 1:
        fail("Page must contain exactly one matching canonical URL", canonical)
    _require_single(source, r'<meta\b[^>]*name=["\']description["\'][^>]*content=["\'][^"\']+["\']', "Page must contain one meta description", path.as_posix())
    _require_single(source, r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']+["\']', "Page must contain one robots meta tag", path.as_posix())
    if re.search(r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', source, flags=re.I | re.S):
        fail("Published page must not be noindex", path.as_posix())
    for required in ('property="og:title"', 'name="twitter:card"', "navigator.serviceWorker.register"):
        if required not in source:
            fail("Published page is missing SEO or PWA integration", {"page": path.as_posix(), "required": required})
    if not _has_shell_component(source, "header"):
        fail("Published page is missing institutional header", path.as_posix())
    if not _has_shell_component(source, "footer"):
        fail("Published page is missing institutional footer", path.as_posix())
    if "application/ld+json" not in source:
        fail("Structured data block is missing", path.as_posix())
    if article and not re.search(r'"@type"\s*:\s*"Article"', source):
        fail("Article JSON-LD is missing", path.as_posix())
    if "معاقين" in source:
        fail("Published page contains the prohibited term", path.as_posix())
    words = visible_words(source)
    if words < minimum_words:
        fail("Deployed page is below its minimum depth", {"path": path.as_posix(), "words": words, "minimum": minimum_words})
    return {
        "path": path.as_posix(),
        "words": words,
        "indexable": "noindex" not in lower,
        "canonical": canonical,
        "shell": True,
        "pwa": True,
    }


def verify(site: Path, source_file: Path, expected_sha: str | None = None, mode: str = "live") -> dict[str, Any]:
    site = site.resolve()
    source_file = source_file.resolve()
    if not site.is_dir():
        fail("Site directory does not exist", site.as_posix())

    articles = source_articles(source_file)
    slugs = [str(item["slug"]) for item in articles]

    deployment = read_json(site / "deployment.json")
    if deployment.get("schema_version") not in {29, 30}:
        fail("Unexpected deployment schema", deployment.get("schema_version"))
    deployed_sha = deployment.get("commit")
    if not isinstance(deployed_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", deployed_sha):
        fail("Deployment commit must be a full SHA", deployed_sha)
    if expected_sha and deployed_sha != expected_sha:
        fail("Deployment SHA does not match expected SHA", {"deployed": deployed_sha, "expected": expected_sha})

    report = read_json(site / "api" / "home-sector-v234.json")
    required = {
        "version": 234,
        "status": "passed",
        "source_articles": 20,
        "banned_term_present": False,
        "diagnostic_claim_present": False,
        "word_count_method": WORD_COUNT_METHOD,
        "depth_contract_version": 244,
    }
    for key, expected in required.items():
        if report.get(key) != expected:
            fail("Home-sector report contract mismatch", {"key": key, "found": report.get(key), "expected": expected})
    if int(report.get("hub_words", 0)) < MINIMUM_HUB_WORDS:
        fail("Home-sector hub report depth is too low", report.get("hub_words"))
    if int(report.get("minimum_article_words", 0)) < MINIMUM_ARTICLE_WORDS:
        fail("Home-sector article report depth is too low", report.get("minimum_article_words"))

    hub = validate_indexable_page(
        site / "sectors" / "home" / "index.html",
        f"{BASE}/sectors/home/",
        article=False,
        minimum_words=MINIMUM_HUB_WORDS,
    )
    hub_source = (site / "sectors" / "home" / "index.html").read_text(encoding="utf-8")
    for schema in ("CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"):
        if schema not in hub_source:
            fail("Home-sector hub schema is missing", schema)
    missing_hub_links = [slug for slug in slugs if f"{BASE_PATH}sectors/home/{slug}/" not in hub_source]
    if missing_hub_links:
        fail("Home-sector hub is missing article links", missing_hub_links)

    pages: list[dict[str, Any]] = []
    for slug in slugs:
        pages.append(
            validate_indexable_page(
                site / "sectors" / "home" / slug / "index.html",
                f"{BASE}/sectors/home/{slug}/",
                article=True,
                minimum_words=MINIMUM_ARTICLE_WORDS,
            )
        )

    robots_path = site / "robots.txt"
    if not robots_path.is_file():
        fail("Missing robots.txt")
    robots = robots_path.read_text(encoding="utf-8")
    if "Allow: /sectors/home/" not in robots:
        fail("Home-sector Allow rule is missing from robots.txt")
    if "Sitemap: https://healthrenewal.org/sitemap.xml" not in robots:
        fail("Main sitemap declaration is missing from robots.txt")

    minimum_live_article_words = min(item["words"] for item in pages)
    if int(report["hub_words"]) != hub["words"] or int(report["minimum_article_words"]) != minimum_live_article_words:
        fail("Production report and live semantic word counts differ", {
            "report_hub": report["hub_words"],
            "live_hub": hub["words"],
            "report_minimum_article": report["minimum_article_words"],
            "live_minimum_article": minimum_live_article_words,
        })

    result = {
        "version": VERSION,
        "status": "passed",
        "mode": mode,
        "deployment_commit": deployed_sha,
        "source_articles": len(articles),
        "hub_words": hub["words"],
        "article_pages_verified": len(pages),
        "minimum_live_article_words": minimum_live_article_words,
        "word_count_method": WORD_COUNT_METHOD,
        "all_indexable": all(item["indexable"] for item in [hub, *pages]),
        "all_have_shell": all(item["shell"] for item in [hub, *pages]),
        "all_have_pwa": all(item["pwa"] for item in [hub, *pages]),
        "robots_allow": True,
        "report_version": report["version"],
        "depth_contract_version": report["depth_contract_version"],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "home-sector-deployment-v238.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the live home-sector deployment")
    parser.add_argument("site", type=Path)
    parser.add_argument("--source", type=Path, default=Path("content/sectors-v10/home.json"))
    parser.add_argument("--expected-sha")
    parser.add_argument("--mode", choices=("live", "artifact"), default="live")
    args = parser.parse_args()
    result = verify(args.site, args.source, args.expected_sha, args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
