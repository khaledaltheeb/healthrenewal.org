#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VERSION = 240
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
CORRECTED_GRIEF_TEXT = "تربط النوم بالموت"
CORRUPTED_GRIEF_TEXT = "قد أراد العتودة"


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
        fail("Child-sector source must declare twenty articles", len(articles) if isinstance(articles, list) else articles)
    slugs: list[str] = []
    for item in articles:
        if not isinstance(item, dict):
            fail("Article entry must be an object", item)
        slug = item.get("slug")
        title = item.get("title")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            fail("Invalid child-sector slug", slug)
        if not isinstance(title, str) or len(title.strip()) < 8:
            fail("Invalid child-sector title", title)
        slugs.append(slug)
    if len(slugs) != len(set(slugs)):
        fail("Duplicate child-sector slugs", slugs)
    if "child-grief" not in slugs:
        fail("Child-grief guide is missing from the source inventory")
    return articles


def validate_indexable_page(path: Path, canonical: str, *, article: bool, minimum_words: int) -> dict[str, Any]:
    if not path.is_file():
        fail("Missing deployed page", path.as_posix())
    source = path.read_text(encoding="utf-8")
    lower = source.lower()
    if len(re.findall(r"<h1\b", source, flags=re.I)) != 1:
        fail("Page must contain exactly one H1", path.as_posix())
    if canonical not in source:
        fail("Canonical URL is missing", canonical)
    robots = re.findall(r'<meta\b[^>]*name=["\']robots["\'][^>]*>', source, flags=re.I | re.S)
    if len(robots) != 1:
        fail("Page must contain exactly one robots meta", {"path": path.as_posix(), "count": len(robots)})
    if any("noindex" in item.lower() for item in robots):
        fail("Published page must not be noindex", path.as_posix())
    if article and not re.search(r'"@type"\s*:\s*"Article"', source):
        fail("Article JSON-LD is missing", path.as_posix())
    words = visible_words(source)
    if words < minimum_words:
        fail("Deployed page is below its minimum depth", {"path": path.as_posix(), "words": words, "minimum": minimum_words})
    return {"path": path.as_posix(), "words": words, "indexable": "noindex" not in lower}


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

    report = read_json(site / "api" / "child-sector-v239.json")
    required: dict[str, Any] = {
        "version": 239,
        "status": "passed",
        "source_articles": 20,
        "source_corrections": ["child-grief"],
        "banned_term_present": False,
        "diagnostic_claim_present": False,
    }
    for key, expected in required.items():
        if report.get(key) != expected:
            fail("Child-sector report contract mismatch", {"key": key, "found": report.get(key), "expected": expected})
    if int(report.get("hub_words", 0)) < 2200:
        fail("Child-sector hub report depth is too low", report.get("hub_words"))
    if int(report.get("minimum_article_words", 0)) < 650:
        fail("Child-sector article report depth is too low", report.get("minimum_article_words"))

    hub_path = site / "sectors" / "child" / "index.html"
    hub = validate_indexable_page(
        hub_path,
        f"{BASE}/sectors/child/",
        article=False,
        minimum_words=2200,
    )
    hub_source = hub_path.read_text(encoding="utf-8")
    for schema in ("CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"):
        if schema not in hub_source:
            fail("Child-sector hub schema is missing", schema)
    missing_hub_links = [slug for slug in slugs if f"{BASE_PATH}sectors/child/{slug}/" not in hub_source]
    if missing_hub_links:
        fail("Child-sector hub is missing article links", missing_hub_links)

    pages: list[dict[str, Any]] = []
    for slug in slugs:
        pages.append(
            validate_indexable_page(
                site / "sectors" / "child" / slug / "index.html",
                f"{BASE}/sectors/child/{slug}/",
                article=True,
                minimum_words=650,
            )
        )

    grief_path = site / "sectors" / "child" / "child-grief" / "index.html"
    grief_source = grief_path.read_text(encoding="utf-8")
    if CORRECTED_GRIEF_TEXT not in grief_source:
        fail("Corrected child-grief wording is missing", CORRECTED_GRIEF_TEXT)
    if CORRUPTED_GRIEF_TEXT in grief_source:
        fail("Corrupted child-grief wording remains", CORRUPTED_GRIEF_TEXT)

    robots_path = site / "robots.txt"
    if not robots_path.is_file():
        fail("Missing robots.txt")
    robots = robots_path.read_text(encoding="utf-8")
    if "Allow: /sectors/child/" not in robots:
        fail("Child-sector Allow rule is missing from robots.txt")
    if "Sitemap: https://healthrenewal.org/sitemap.xml" not in robots:
        fail("Main sitemap declaration is missing from robots.txt")

    result = {
        "version": VERSION,
        "status": "passed",
        "mode": mode,
        "deployment_commit": deployed_sha,
        "source_articles": len(articles),
        "hub_words": hub["words"],
        "article_pages_verified": len(pages),
        "minimum_live_article_words": min(item["words"] for item in pages),
        "all_indexable": all(item["indexable"] for item in [hub, *pages]),
        "robots_allow": True,
        "report_version": report["version"],
        "grief_correction_verified": True,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "child-sector-deployment-v240.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the live child-sector deployment")
    parser.add_argument("site", type=Path)
    parser.add_argument("--source", type=Path, default=Path("content/sectors-v10/child.json"))
    parser.add_argument("--expected-sha")
    parser.add_argument("--mode", choices=("live", "artifact"), default="live")
    args = parser.parse_args()
    result = verify(args.site, args.source, args.expected_sha, args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
