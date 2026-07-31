#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VERSION = 247
BASE_URL = "https://healthrenewal.org/"
BASE_PATH = "/"
BLOCKED_SLUG = "autism-family-practical-guide"
MINIMUM_GUIDES = 100
MINIMUM_VISIBLE_WORDS = 650
MINIMUM_META_DESCRIPTION = 60
MAXIMUM_META_DESCRIPTION = 180
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == lowered:
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
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("JSON root must be an object", path.as_posix())
    return value


def visible_words(source: str) -> int:
    parser = VisibleTextParser()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def expected_core_slugs() -> list[str]:
    from care_guides_catalog_v246 import institutional_guides
    from publish_care_guides_v246 import DATA_FILES

    guides: list[dict[str, Any]] = []
    for path in DATA_FILES:
        guides.extend(json.loads(path.read_text(encoding="utf-8")).get("guides", []))
    guides.extend(institutional_guides())
    published = [
        guide
        for guide in guides
        if guide.get("review_status") != "needs-specialist-review"
    ]
    slugs = [str(guide.get("slug", "")) for guide in published]
    if len(slugs) != MINIMUM_GUIDES:
        fail("Expected exactly one hundred published core guides", len(slugs))
    if len(slugs) != len(set(slugs)):
        fail("Duplicate published care-guide slugs", slugs)
    if BLOCKED_SLUG in slugs:
        fail("Blocked specialist-review guide entered the published inventory")
    return sorted(slugs)


def sitemap_urls(path: Path) -> list[str]:
    if not path.is_file():
        fail("Missing care-guide sitemap", path.as_posix())
    root = ET.parse(path).getroot()
    urls = [
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if (node.text or "").strip()
    ]
    if len(urls) != len(set(urls)):
        fail("Duplicate URLs in care-guide sitemap")
    return urls


def _single_tag(source: str, pattern: str, label: str, path: Path) -> str:
    matches = re.findall(pattern, source, flags=re.I | re.S)
    if len(matches) != 1:
        fail(f"Page must contain exactly one {label}", {"path": path.as_posix(), "count": len(matches)})
    value = matches[0]
    return value if isinstance(value, str) else value[0]


def _meta_content(tag: str) -> str:
    match = re.search(r'\bcontent=(["\'])(.*?)\1', tag, flags=re.I | re.S)
    if not match:
        fail("Metadata tag is missing its content attribute", tag)
    return html.unescape(match.group(2)).strip()


def validate_guide_page(path: Path, canonical: str) -> dict[str, Any]:
    if not path.is_file():
        fail("Missing deployed care-guide page", path.as_posix())
    source = path.read_text(encoding="utf-8")
    lower = source.lower()

    if len(re.findall(r"<main\b", source, flags=re.I)) != 1:
        fail("Guide page must contain exactly one main element", path.as_posix())
    h1 = _single_tag(source, r"<h1\b[^>]*>(.*?)</h1>", "H1", path)
    title_text = re.sub(r"<[^>]+>", " ", html.unescape(h1)).strip()
    if len(title_text) < 8:
        fail("Guide H1 is too short", {"path": path.as_posix(), "title": title_text})

    canonical_tag = _single_tag(
        source,
        r'<link\b[^>]*rel=["\']canonical["\'][^>]*>',
        "canonical link",
        path,
    )
    if canonical not in canonical_tag:
        fail("Canonical URL does not match the guide route", {"path": path.as_posix(), "canonical": canonical})

    description_tag = _single_tag(
        source,
        r'<meta\b[^>]*name=["\']description["\'][^>]*>',
        "meta description",
        path,
    )
    description = _meta_content(description_tag)
    if not MINIMUM_META_DESCRIPTION <= len(description) <= MAXIMUM_META_DESCRIPTION:
        fail(
            "Guide meta description length is outside the production contract",
            {"path": path.as_posix(), "length": len(description)},
        )

    for meta_name in ("robots", "googlebot", "keywords"):
        tag = _single_tag(
            source,
            rf'<meta\b[^>]*name=["\']{meta_name}["\'][^>]*>',
            f"{meta_name} metadata",
            path,
        )
        if meta_name in {"robots", "googlebot"} and "noindex" in tag.lower():
            fail("Published guide must remain indexable", {"path": path.as_posix(), "meta": meta_name})

    for schema_type in ("Article", "HowTo", "BreadcrumbList"):
        if not re.search(rf'"@type"\s*:\s*"{schema_type}"', source):
            fail("Required structured-data type is missing", {"path": path.as_posix(), "type": schema_type})

    if "مصادر مؤسسية للمراجعة" not in source:
        fail("Institutional source section is missing", path.as_posix())
    if "خدمات الطوارئ المحلية" not in source and "جهة صحية عاجلة" not in source:
        fail("Emergency escalation wording is missing", path.as_posix())
    if "معاقين" in source:
        fail("Prohibited terminology remains in a deployed guide", path.as_posix())
    if BLOCKED_SLUG in source:
        fail("Blocked specialist-review route is linked from a deployed guide", path.as_posix())

    words = visible_words(source)
    if words < MINIMUM_VISIBLE_WORDS:
        fail(
            "Deployed guide is below the minimum visible depth",
            {"path": path.as_posix(), "words": words, "minimum": MINIMUM_VISIBLE_WORDS},
        )

    return {
        "slug": path.parent.name,
        "title": title_text,
        "visible_words": words,
        "meta_description_length": len(description),
        "canonical": canonical,
        "indexable": "noindex" not in lower,
    }


def verify(site: Path, *, expected_sha: str | None, mode: str) -> dict[str, Any]:
    site = site.resolve()
    slugs = expected_core_slugs()
    deployment = read_json(site / "deployment.json")
    report = read_json(site / "api/care-guides-v21.json")
    sitemap = sitemap_urls(site / "sitemap-care-guides.xml")
    hub = site / "care-guides/index.html"
    robots = site / "robots.txt"

    if expected_sha and deployment.get("commit") != expected_sha:
        fail("Live deployment SHA does not match the expected commit", {"expected": expected_sha, "actual": deployment.get("commit")})
    if report.get("source_guides") != 101:
        fail("Care-guide source inventory must equal 101", report.get("source_guides"))
    if report.get("published_core_guides") != MINIMUM_GUIDES:
        fail("Published core guide count must equal 100", report.get("published_core_guides"))
    if report.get("core_guides") != 101:
        fail("Compatibility core-guide count must equal 101", report.get("core_guides"))
    if report.get("minimum_published_guides_met") is not True:
        fail("Minimum published guide gate is not marked as passed", report)
    if report.get("needs_specialist_review_published") is not False:
        fail("A guide requiring specialist review was published", report)
    if report.get("autism_published") is not False:
        fail("Blocked autism guide is reported as published", report)
    if report.get("blocked_review_slugs") != [BLOCKED_SLUG]:
        fail("Blocked review inventory is unexpected", report.get("blocked_review_slugs"))

    if not hub.is_file():
        fail("Missing deployed care-guide hub", hub.as_posix())
    hub_source = hub.read_text(encoding="utf-8")
    if BLOCKED_SLUG in hub_source:
        fail("Blocked autism route appears in the care-guide hub")
    for token in ("data-care-library", "CollectionPage", "ItemList", "FAQPage", "المنهجية التحريرية وضبط الجودة"):
        if token not in hub_source:
            fail("Care-guide hub institutional contract is missing", token)
    if not robots.is_file() or "sitemap-care-guides.xml" not in robots.read_text(encoding="utf-8"):
        fail("Robots file does not advertise the care-guide sitemap")

    expected_urls = {BASE_URL + f"care-guides/{slug}/" for slug in slugs}
    sitemap_set = set(sitemap)
    missing_urls = sorted(expected_urls.difference(sitemap_set))
    if missing_urls:
        fail("Published core guides are missing from the sitemap", missing_urls[:10])
    blocked_url = BASE_URL + f"care-guides/{BLOCKED_SLUG}/"
    if blocked_url in sitemap_set:
        fail("Blocked specialist-review route appears in the sitemap")

    pages: list[dict[str, Any]] = []
    for slug in slugs:
        pages.append(
            validate_guide_page(
                site / "care-guides" / slug / "index.html",
                BASE_URL + f"care-guides/{slug}/",
            )
        )

    titles = [page["title"] for page in pages]
    if len(titles) != len(set(titles)):
        fail("Duplicate live care-guide H1 titles detected")

    result = {
        "version": VERSION,
        "mode": mode,
        "status": "passed",
        "deployment_commit": deployment.get("commit"),
        "expected_commit": expected_sha,
        "source_guides": report.get("source_guides"),
        "published_core_guides": report.get("published_core_guides"),
        "verified_core_pages": len(pages),
        "sitemap_urls": len(sitemap),
        "blocked_review_route_absent": blocked_url not in sitemap_set and BLOCKED_SLUG not in hub_source,
        "minimum_visible_words": min((page["visible_words"] for page in pages), default=0),
        "maximum_meta_description_length": max((page["meta_description_length"] for page in pages), default=0),
        "minimum_meta_description_length": min((page["meta_description_length"] for page in pages), default=0),
        "unique_titles": len(set(titles)),
        "all_indexable": all(page["indexable"] for page in pages),
        "pages": pages,
    }
    output = site / "api/care-guides-deployment-v247.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _download(url: str, destination: Path, *, attempts: int = 6) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "User-Agent": "care-guides-live-v247",
                },
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read()
                if response.status != 200 or not body:
                    raise RuntimeError(f"Unexpected response: {response.status}, bytes={len(body)}")
                destination.write_bytes(body)
                return
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(3 + attempt)
    raise RuntimeError(f"Failed to download {url}: {last_error}")


def download_live(site: Path, *, base_url: str, token: str) -> None:
    base = base_url.rstrip("/") + "/"
    static_targets = {
        "deployment.json": site / "deployment.json",
        "api/care-guides-v21.json": site / "api/care-guides-v21.json",
        "sitemap-care-guides.xml": site / "sitemap-care-guides.xml",
        "care-guides/": site / "care-guides/index.html",
        "robots.txt": site / "robots.txt",
    }
    for relative, destination in static_targets.items():
        _download(f"{base}{relative}?v={token}", destination)

    slugs = expected_core_slugs()
    failures: list[str] = []

    def fetch_slug(slug: str) -> None:
        try:
            _download(
                f"{base}care-guides/{slug}/?v={token}",
                site / "care-guides" / slug / "index.html",
            )
        except Exception as error:  # pragma: no cover - network diagnostics
            failures.append(f"{slug}: {error}")

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(fetch_slug, slug) for slug in slugs]
        for future in as_completed(futures):
            future.result()
    if failures:
        fail("Failed to download one or more live care-guide pages", failures)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the deployed care-guide library and all one hundred core guides.")
    parser.add_argument("site", type=Path)
    parser.add_argument("--expected-sha", default=None)
    parser.add_argument("--mode", choices=("source", "live"), default="source")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--token", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.base_url:
        download_live(
            args.site,
            base_url=args.base_url,
            token=args.token or args.expected_sha or str(int(time.time())),
        )
    result = verify(args.site, expected_sha=args.expected_sha, mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
