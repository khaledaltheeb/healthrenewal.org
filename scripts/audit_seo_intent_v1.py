#!/usr/bin/env python3
"""Site-wide semantic SEO and search-intent audit.

The audit is intentionally deterministic and dependency-free. It validates the
published HTML/XML surface, not authoring notes. It supports two scopes:

* priority: the 100 URLs selected for direct webmaster submission;
* all: every URL discoverable from the repository sitemap index.

It does not reward keyword stuffing. It validates meaningful headings, visible
question/answer coverage where search intent warrants it, crawlable content,
canonical metadata, social previews and structured data that matches the page.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://healthrenewal.org"
PRIORITY_FILE = ROOT / "content" / "seo-priority-urls.txt"
DEFAULT_REPORT = ROOT / "reports" / "seo-intent-audit-v1.json"
XML_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
QUESTION_MARKERS = (
    "؟",
    "ما هو",
    "ما هي",
    "كيف ",
    "متى ",
    "هل ",
    "لماذا ",
    "ما الفرق",
    "ماذا ",
)


@dataclass
class Finding:
    code: str
    severity: str
    message: str


@dataclass
class PageResult:
    url: str
    path: str
    kind: str
    indexable: bool = True
    title: str = ""
    description: str = ""
    word_count: int = 0
    h1: int = 0
    h2: int = 0
    h3: int = 0
    questions: int = 0
    schema_types: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(item.severity == "error" for item in self.findings)

    @property
    def warnings(self) -> int:
        return sum(item.severity == "warning" for item in self.findings)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_attrs: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.in_title = False
        self.skip_depth = 0
        self.current_heading: tuple[int, list[str]] | None = None
        self.headings: list[tuple[int, str]] = []
        self.visible_parts: list[str] = []
        self.meta_name: dict[str, str] = {}
        self.meta_property: dict[str, str] = {}
        self.canonical: list[str] = []
        self.hreflang: dict[str, str] = {}
        self.links: list[str] = []
        self.images: list[dict[str, str]] = []
        self.jsonld_parts: list[list[str]] = []
        self.in_jsonld = False
        self.main_count = 0
        self.article_count = 0

    @staticmethod
    def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {str(k).lower(): "" if v is None else str(v) for k, v in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = self.attrs_dict(attrs)
        if tag == "html":
            self.html_attrs = data
        if tag == "title":
            self.in_title = True
        if tag in {"script", "style", "template", "svg"}:
            self.skip_depth += 1
        if tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self.in_jsonld = True
            self.jsonld_parts.append([])
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.current_heading = (int(tag[1]), [])
        if tag == "meta":
            content = data.get("content", "").strip()
            if data.get("name"):
                self.meta_name[data["name"].lower()] = content
            if data.get("property"):
                self.meta_property[data["property"].lower()] = content
        if tag == "link":
            rel = {part.lower() for part in data.get("rel", "").split()}
            href = data.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonical.append(href)
            if "alternate" in rel and data.get("hreflang") and href:
                self.hreflang[data["hreflang"].lower()] = href
        if tag == "a" and data.get("href"):
            self.links.append(data["href"].strip())
        if tag == "img":
            self.images.append(data)
        if tag == "main":
            self.main_count += 1
        if tag == "article":
            self.article_count += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        if tag in {"script", "style", "template", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "script" and self.in_jsonld:
            self.in_jsonld = False
        if self.current_heading and tag == f"h{self.current_heading[0]}":
            level, parts = self.current_heading
            text = clean_text(" ".join(parts))
            self.headings.append((level, text))
            self.current_heading = None

    def handle_data(self, data: str) -> None:
        if self.in_jsonld and self.jsonld_parts:
            self.jsonld_parts[-1].append(data)
            return
        if self.in_title:
            self.title_parts.append(data)
        if self.current_heading is not None:
            self.current_heading[1].append(data)
        if not self.skip_depth:
            text = clean_text(data)
            if text:
                self.visible_parts.append(text)

    @property
    def title(self) -> str:
        return clean_text(" ".join(self.title_parts))

    @property
    def visible_text(self) -> str:
        return clean_text(" ".join(self.visible_parts))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def add(result: PageResult, code: str, severity: str, message: str) -> None:
    result.findings.append(Finding(code=code, severity=severity, message=message))


def url_to_path(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "healthrenewal.org":
        raise ValueError(f"URL is outside canonical origin: {url}")
    route = parsed.path.lstrip("/")
    if not route:
        return ROOT / "index.html"
    if route.endswith("/"):
        return ROOT / route / "index.html"
    return ROOT / route


def classify(url: str, path: Path) -> str:
    route = urlparse(url).path
    if path.suffix.lower() == ".xml":
        return "xml"
    if route.startswith("/family-guide/conditions/"):
        return "family_condition"
    if route.startswith("/magazine/") and route.endswith(".html"):
        return "research_article"
    if "/tools/" in route or route.startswith("/ai-search/"):
        return "tool"
    if route in {"/copyright/", "/accessibility/"}:
        return "governance"
    if route.endswith("/"):
        return "hub"
    return "page"


def iter_schema_types(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        item_type = value.get("@type")
        if isinstance(item_type, str):
            yield item_type
        elif isinstance(item_type, list):
            yield from (str(item) for item in item_type)
        for child in value.values():
            yield from iter_schema_types(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_schema_types(child)


def parse_jsonld(parser: PageParser, result: PageResult) -> list[object]:
    payloads: list[object] = []
    for index, parts in enumerate(parser.jsonld_parts, start=1):
        raw = "".join(parts).strip()
        if not raw:
            continue
        try:
            payloads.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            add(result, "jsonld_invalid", "error", f"JSON-LD block {index} is invalid: {exc.msg}")
    result.schema_types = sorted(set(t for p in payloads for t in iter_schema_types(p)))
    return payloads


def count_questions(parser: PageParser) -> int:
    candidates = [text for _, text in parser.headings]
    candidates.extend(re.split(r"(?<=[؟?!])\s+", parser.visible_text))
    normalized = {clean_text(item) for item in candidates if clean_text(item)}
    return sum(
        1
        for item in normalized
        if "؟" in item or any(item.startswith(marker) for marker in QUESTION_MARKERS[1:])
    )


def is_internal_href(href: str) -> bool:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return False
    parsed = urlparse(href)
    return not parsed.netloc or parsed.netloc == "healthrenewal.org"


def audit_heading_outline(parser: PageParser, result: PageResult) -> None:
    levels = [level for level, text in parser.headings if text]
    result.h1 = levels.count(1)
    result.h2 = levels.count(2)
    result.h3 = levels.count(3)
    if result.h1 != 1:
        add(result, "h1_count", "error", f"Expected exactly one visible H1; found {result.h1}")
    previous = 0
    for level, text in parser.headings:
        if not text:
            add(result, "empty_heading", "error", f"Empty H{level} heading")
            continue
        if previous and level > previous + 1:
            add(result, "heading_jump", "error", f"Heading jumps from H{previous} to H{level}: {text[:80]}")
        previous = level
    if result.h3 and not result.h2:
        add(result, "orphan_h3", "error", "H3 exists without an H2 parent level")


def audit_html(url: str, path: Path) -> PageResult:
    kind = classify(url, path)
    result = PageResult(url=url, path=str(path.relative_to(ROOT)), kind=kind)
    if not path.is_file():
        add(result, "missing_file", "error", "Mapped publication file does not exist")
        return result
    source = path.read_text(encoding="utf-8")
    parser = PageParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception as exc:  # defensive: malformed HTML must not abort the complete audit
        add(result, "html_parse", "error", f"HTML parser failed: {exc}")
        return result

    result.title = parser.title
    result.description = parser.meta_name.get("description", "")
    robots = parser.meta_name.get("robots", "").lower()
    result.indexable = "noindex" not in robots
    result.word_count = len(re.findall(r"[\w\u0600-\u06FF]+", parser.visible_text, flags=re.UNICODE))
    result.questions = count_questions(parser)
    audit_heading_outline(parser, result)
    parse_jsonld(parser, result)

    if parser.html_attrs.get("lang", "").lower() != "ar":
        add(result, "lang", "error", "The root HTML element must declare lang=ar")
    if parser.html_attrs.get("dir", "").lower() != "rtl":
        add(result, "dir", "error", "The root HTML element must declare dir=rtl")
    if "viewport" not in parser.meta_name:
        add(result, "viewport", "error", "Missing viewport metadata")
    if not re.search(r"<meta\s+charset=[\"']?utf-8", source, flags=re.I):
        add(result, "charset", "error", "Missing UTF-8 charset declaration")
    if not result.title:
        add(result, "title_missing", "error", "Missing title element")
    elif not 15 <= len(result.title) <= 75:
        add(result, "title_length", "warning", f"Title length is {len(result.title)} characters")
    if not result.description:
        add(result, "description_missing", "error", "Missing meta description")
    elif not 80 <= len(result.description) <= 240:
        add(result, "description_length", "warning", f"Description length is {len(result.description)} characters")

    expected = url
    if parser.canonical != [expected]:
        add(result, "canonical", "error", f"Expected one canonical equal to {expected}; found {parser.canonical}")
    if result.indexable and "index" not in robots:
        add(result, "robots_index", "warning", "Indexable page does not explicitly declare index")
    if result.indexable and "follow" not in robots:
        add(result, "robots_follow", "warning", "Indexable page does not explicitly declare follow")

    if result.indexable:
        if result.h2 < 1:
            add(result, "h2_missing", "error", "Indexable content page needs at least one meaningful H2")
        deep = kind in {"family_condition", "research_article"} or result.word_count >= 700
        if deep and result.h3 < 1:
            add(result, "h3_missing_for_deep_page", "error", "Deep content needs at least one meaningful H3 under an H2")

    minimum_words = {
        "family_condition": 650,
        "research_article": 300,
        "tool": 120,
        "hub": 120,
        "governance": 120,
        "page": 120,
    }.get(kind, 0)
    if result.indexable and result.word_count < minimum_words:
        add(result, "thin_static_html", "error", f"Initial HTML has {result.word_count} words; expected at least {minimum_words} for {kind}")

    min_questions = {"family_condition": 5, "research_article": 4, "tool": 2}.get(kind, 0)
    if result.indexable and result.questions < min_questions:
        add(result, "search_intent_questions", "error", f"Found {result.questions} visible search-intent questions; expected at least {min_questions}")

    internal_links = [href for href in parser.links if is_internal_href(href)]
    if result.indexable and len(internal_links) < 3:
        add(result, "internal_links", "error", f"Only {len(internal_links)} crawlable internal links found")
    if parser.main_count != 1:
        add(result, "main_landmark", "warning", f"Expected one main landmark; found {parser.main_count}")

    required_og = {"og:title", "og:description", "og:url", "og:type", "og:image", "og:image:alt"}
    missing_og = sorted(required_og - parser.meta_property.keys())
    if missing_og:
        add(result, "open_graph", "warning", "Missing Open Graph fields: " + ", ".join(missing_og))
    if parser.meta_property.get("og:url") and parser.meta_property["og:url"] != expected:
        add(result, "og_url", "error", "og:url differs from canonical URL")
    required_twitter = {"twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"}
    missing_twitter = sorted(required_twitter - parser.meta_name.keys())
    if missing_twitter:
        add(result, "twitter", "warning", "Missing Twitter card fields: " + ", ".join(missing_twitter))

    if result.indexable and not result.schema_types:
        add(result, "structured_data", "error", "Missing valid JSON-LD structured data")
    if kind in {"family_condition", "research_article"} and "BreadcrumbList" not in result.schema_types:
        add(result, "breadcrumb_schema", "error", "Deep content must expose BreadcrumbList structured data")
    if kind in {"family_condition", "research_article"} and "FAQPage" not in result.schema_types:
        add(result, "faq_schema", "error", "Visible intent questions must be represented by matching FAQPage data")
    if kind == "family_condition" and not ({"MedicalWebPage", "WebPage"} & set(result.schema_types)):
        add(result, "medical_schema", "error", "Family condition page needs MedicalWebPage/WebPage structured data")
    if kind == "research_article" and not ({"ScholarlyArticle", "Article", "NewsArticle"} & set(result.schema_types)):
        add(result, "article_schema", "error", "Research page needs article structured data")

    if kind in {"family_condition", "research_article"}:
        if parser.hreflang.get("ar") != expected:
            add(result, "hreflang_ar", "warning", "Missing self-referential Arabic hreflang")
        if parser.hreflang.get("x-default") != expected:
            add(result, "hreflang_default", "warning", "Missing x-default hreflang")

    for index, image in enumerate(parser.images, start=1):
        alt = image.get("alt")
        decorative = image.get("role") == "presentation" or image.get("aria-hidden") == "true"
        if alt is None:
            add(result, "image_alt_missing", "error", f"Image {index} has no alt attribute")
        elif not alt.strip() and not decorative:
            add(result, "image_alt_empty", "warning", f"Image {index} has empty alt without decorative semantics")

    if "keywords" in parser.meta_name:
        add(result, "meta_keywords", "warning", "Obsolete meta keywords tag is present; remove it rather than stuffing terms")
    return result



def audit_resource(url: str, path: Path) -> PageResult:
    result = PageResult(url=url, path=str(path.relative_to(ROOT)), kind="resource", indexable=False)
    if not path.is_file():
        add(result, "missing_file", "error", "Sitemap-listed resource does not exist")
        return result
    if path.stat().st_size == 0:
        add(result, "empty_resource", "error", "Sitemap-listed resource is empty")
    if path.suffix.lower() == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            add(result, "json_invalid", "error", f"Invalid JSON resource: {exc}")
    return result

def audit_xml(url: str, path: Path) -> PageResult:
    result = PageResult(url=url, path=str(path.relative_to(ROOT)), kind="xml")
    if not path.is_file():
        add(result, "missing_file", "error", "XML publication file does not exist")
        return result
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        add(result, "xml_invalid", "error", f"Invalid XML: {exc}")
        return result
    root_tag = tree.getroot().tag.rsplit("}", 1)[-1]
    if root_tag not in {"urlset", "sitemapindex"}:
        add(result, "xml_root", "error", f"Unexpected sitemap root: {root_tag}")
    locations = [clean_text(node.text or "") for node in tree.findall(".//sm:loc", XML_NS)]
    if not locations:
        add(result, "xml_empty", "error", "Sitemap contains no loc elements")
    for location in locations:
        if not location.startswith(ORIGIN + "/"):
            add(result, "xml_origin", "error", f"Sitemap location is outside canonical origin: {location}")
    return result


def read_priority_urls() -> list[str]:
    urls = [line.strip() for line in PRIORITY_FILE.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    if len(urls) != 100 or len(set(urls)) != 100:
        raise RuntimeError(f"Priority URL contract requires exactly 100 unique URLs; found {len(urls)} / {len(set(urls))}")
    return urls


def local_sitemap_path(location: str) -> Path | None:
    parsed = urlparse(location)
    if parsed.netloc != "healthrenewal.org":
        return None
    candidate = ROOT / parsed.path.lstrip("/")
    return candidate if candidate.is_file() else None


def sitemap_urls() -> list[str]:
    entry = ROOT / "sitemap-index.xml"
    if not entry.is_file():
        entry = ROOT / "sitemap.xml"
    tree = ET.parse(entry)
    root_tag = tree.getroot().tag.rsplit("}", 1)[-1]
    if root_tag == "urlset":
        return sorted({clean_text(node.text or "") for node in tree.findall(".//sm:loc", XML_NS) if clean_text(node.text or "")})
    if root_tag != "sitemapindex":
        raise RuntimeError(f"Unsupported sitemap entry root: {root_tag}")
    urls: set[str] = set()
    for node in tree.findall(".//sm:loc", XML_NS):
        location = clean_text(node.text or "")
        local = local_sitemap_path(location)
        if local is None:
            raise RuntimeError(f"Sitemap child is missing locally: {location}")
        child = ET.parse(local)
        for child_node in child.findall(".//sm:loc", XML_NS):
            value = clean_text(child_node.text or "")
            if value:
                urls.add(value)
    return sorted(urls)


def write_report(results: list[PageResult], output: Path, scope: str) -> dict:
    title_counts = Counter(result.title for result in results if result.title and result.indexable)
    for result in results:
        if result.title and title_counts[result.title] > 1:
            add(result, "duplicate_title", "error", f"Title is shared by {title_counts[result.title]} indexable pages")
    summary = {
        "contract": "sitewide-semantic-seo-search-intent-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "pages": len(results),
        "indexable": sum(result.indexable for result in results),
        "errors": sum(result.errors for result in results),
        "warnings": sum(result.warnings for result in results),
        "passed": sum(result.errors == 0 for result in results),
        "failed": sum(result.errors > 0 for result in results),
        "by_kind": dict(Counter(result.kind for result in results)),
    }
    payload = {"summary": summary, "results": [{**asdict(result), "errors": result.errors, "warnings": result.warnings} for result in results]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = output.with_suffix(".md")
    lines = [
        "# Site-wide SEO and search-intent audit",
        "",
        f"- Scope: `{scope}`",
        f"- URLs: **{summary['pages']}**",
        f"- Passed: **{summary['passed']}**",
        f"- Failed: **{summary['failed']}**",
        f"- Errors: **{summary['errors']}**",
        f"- Warnings: **{summary['warnings']}**",
        "",
        "## Failed URLs",
        "",
    ]
    for result in results:
        if not result.errors:
            continue
        lines.append(f"### {result.url}")
        for item in result.findings:
            if item.severity == "error":
                lines.append(f"- `{item.code}` — {item.message}")
        lines.append("")
    markdown.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("priority", "all"), default="priority")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    urls = read_priority_urls() if args.scope == "priority" else sitemap_urls()
    results: list[PageResult] = []
    for url in urls:
        try:
            path = url_to_path(url)
        except ValueError as exc:
            result = PageResult(url=url, path="", kind="invalid")
            add(result, "url", "error", str(exc))
            results.append(result)
            continue
        suffix = path.suffix.lower()
        if suffix == ".xml":
            results.append(audit_xml(url, path))
        elif suffix in {".json", ".txt", ".webmanifest", ".rss", ".atom"}:
            results.append(audit_resource(url, path))
        else:
            results.append(audit_html(url, path))
    summary = write_report(results, args.report, args.scope)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if args.strict and summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
