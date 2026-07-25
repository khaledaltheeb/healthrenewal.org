#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
BANNED_RE = re.compile(
    r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)"
)
NETWORK_RE = re.compile(r"\b(?:fetch|XMLHttpRequest|sendBeacon|WebSocket)\s*\(")
ARABIC_WORD_RE = re.compile(r"[\u0600-\u06ff]+")
SPACE_RE = re.compile(r"\s+")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.title_parts: list[str] = []
        self.visible_parts: list[str] = []
        self.h1_count = 0
        self.description = ""
        self.keywords = ""
        self.robots = ""
        self.canonical = ""
        self.hreflang: set[str] = set()
        self.og_title = ""
        self.og_description = ""
        self.twitter_card = ""
        self.json_ld: list[str] = []
        self._json_buffer: list[str] | None = None
        self.internal_links: list[str] = []
        self.has_header = False
        self.has_footer = False
        self.has_skip_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = {key.lower(): (value or "") for key, value in attrs}
        self.stack.append(tag)
        if tag == "h1":
            self.h1_count += 1
        elif tag == "header":
            self.has_header = True
        elif tag == "footer":
            self.has_footer = True
        elif tag == "a":
            classes = data.get("class", "").split()
            if "skip-link" in classes:
                self.has_skip_link = True
            href = data.get("href", "").strip()
            if href and self._is_internal(href):
                self.internal_links.append(href)
        elif tag == "meta":
            name = data.get("name", "").strip().lower()
            prop = data.get("property", "").strip().lower()
            content = data.get("content", "").strip()
            if name == "description":
                self.description = content
            elif name == "keywords":
                self.keywords = content
            elif name == "robots":
                self.robots = content
            elif name == "twitter:card":
                self.twitter_card = content
            elif prop == "og:title":
                self.og_title = content
            elif prop == "og:description":
                self.og_description = content
        elif tag == "link":
            rel = data.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonical = data.get("href", "").strip()
            if "alternate" in rel and data.get("hreflang"):
                self.hreflang.add(data["hreflang"].strip().lower())
        elif tag == "script" and data.get("type", "").strip().lower() == "application/ld+json":
            self._json_buffer = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._json_buffer is not None:
            self.json_ld.append("".join(self._json_buffer).strip())
            self._json_buffer = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._json_buffer is not None:
            self._json_buffer.append(data)
            return
        value = SPACE_RE.sub(" ", data).strip()
        if not value:
            return
        if self.stack and self.stack[-1] == "title":
            self.title_parts.append(value)
        if not any(tag in self.stack for tag in ("script", "style", "svg", "noscript", "template")):
            self.visible_parts.append(value)

    @staticmethod
    def _is_internal(href: str) -> bool:
        if href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
            return False
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https"}:
            return parsed.netloc == "khaledaltheeb.github.io" and parsed.path.startswith(BASE_PATH)
        return not parsed.scheme and not href.startswith("//")

    @property
    def title(self) -> str:
        return SPACE_RE.sub(" ", " ".join(self.title_parts)).strip()

    @property
    def visible_text(self) -> str:
        return SPACE_RE.sub(" ", " ".join(self.visible_parts)).strip()


def validate_page(path: Path, site: Path) -> tuple[dict[str, object], list[str]]:
    raw = path.read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(raw)
    relative = path.relative_to(site).as_posix()
    errors: list[str] = []

    if not parser.title:
        errors.append(f"{relative}: missing title")
    if parser.h1_count != 1:
        errors.append(f"{relative}: expected one h1, found {parser.h1_count}")
    if not 70 <= len(parser.description) <= 170:
        errors.append(f"{relative}: description length {len(parser.description)} outside 70..170")
    if not parser.keywords:
        errors.append(f"{relative}: missing keywords")
    if not parser.robots.startswith("index,follow"):
        errors.append(f"{relative}: invalid robots")
    if not parser.canonical.startswith(BASE + "tips/"):
        errors.append(f"{relative}: invalid canonical {parser.canonical!r}")
    if not {"ar", "x-default"}.issubset(parser.hreflang):
        errors.append(f"{relative}: incomplete hreflang {sorted(parser.hreflang)}")
    if not parser.og_title or not parser.og_description or not parser.twitter_card:
        errors.append(f"{relative}: incomplete social metadata")
    if len(parser.json_ld) != 1:
        errors.append(f"{relative}: expected one JSON-LD block, found {len(parser.json_ld)}")
    else:
        try:
            payload = json.loads(parser.json_ld[0])
            if payload.get("@context") != "https://schema.org":
                errors.append(f"{relative}: invalid JSON-LD context")
        except json.JSONDecodeError as exc:
            errors.append(f"{relative}: malformed JSON-LD: {exc}")
    if not parser.has_header or not parser.has_footer or not parser.has_skip_link:
        errors.append(f"{relative}: incomplete semantic shell")
    if len(parser.internal_links) < 3:
        errors.append(f"{relative}: insufficient internal links {len(parser.internal_links)}")
    if len(ARABIC_WORD_RE.findall(parser.visible_text)) < 100:
        errors.append(f"{relative}: fewer than 100 Arabic words")
    if BANNED_RE.search(raw):
        errors.append(f"{relative}: banned person-label language")
    if NETWORK_RE.search(raw):
        errors.append(f"{relative}: network API found in local tips runtime")

    for href in parser.internal_links:
        parsed = urlparse(href)
        if not parsed.scheme and href.startswith("/") and not href.startswith(BASE_PATH):
            errors.append(f"{relative}: internal link misses base path: {href}")

    return {
        "path": relative,
        "title": html.unescape(parser.title),
        "description": html.unescape(parser.description),
        "canonical": parser.canonical,
        "arabic_words": len(ARABIC_WORD_RE.findall(parser.visible_text)),
        "internal_links": len(parser.internal_links),
    }, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    tips = site / "tips"
    if not tips.is_dir():
        raise SystemExit(f"Missing tips directory: {tips}")

    audit_path = site / "api/tips-audit-v234.json"
    data_path = site / "api/v1/tips.json"
    if not audit_path.is_file() or not data_path.is_file():
        raise SystemExit("Missing tips v234 audit or API export")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    data = json.loads(data_path.read_text(encoding="utf-8"))

    errors: list[str] = []
    expected = {
        "guide_count": 36,
        "category_count": 9,
        "static_pages": 3,
        "page_count": 49,
        "sitemap_urls": 49,
    }
    for key, value in expected.items():
        if audit.get(key) != value:
            errors.append(f"audit {key}={audit.get(key)!r}, expected {value}")
    if data.get("guide_count") != 36 or data.get("category_count") != 9 or data.get("page_count") != 49:
        errors.append("API counts do not match production contract")
    safety = data.get("safety", {})
    if safety.get("diagnostic") is not False or safety.get("medication_advice") is not False:
        errors.append("API safety contract is invalid")

    pages = sorted(tips.rglob("index.html"))
    if len(pages) != 49:
        errors.append(f"generated page count={len(pages)}, expected 49")
    metrics: list[dict[str, object]] = []
    for page in pages:
        metric, page_errors = validate_page(page, site)
        metrics.append(metric)
        errors.extend(page_errors)

    for field in ("title", "description", "canonical"):
        values = [str(metric[field]).casefold() for metric in metrics]
        if len(values) != len(set(values)):
            errors.append(f"duplicate {field} values detected")

    sitemap_path = site / "sitemap-tips.xml"
    if not sitemap_path.is_file():
        errors.append("missing sitemap-tips.xml")
        sitemap_urls: list[str] = []
    else:
        sitemap = ET.parse(sitemap_path).getroot()
        sitemap_urls = [node.text or "" for node in sitemap.findall("{*}url/{*}loc")]
        if len(sitemap_urls) != 49 or len(sitemap_urls) != len(set(sitemap_urls)):
            errors.append(f"sitemap URL contract failed: {len(sitemap_urls)} URLs")
        expected_urls = {str(metric["canonical"]) for metric in metrics}
        if set(sitemap_urls) != expected_urls:
            errors.append("sitemap URLs do not exactly match generated canonicals")

    root_sitemap = site / "sitemap.xml"
    if not root_sitemap.is_file() or (BASE + "sitemap-tips.xml") not in root_sitemap.read_text(encoding="utf-8"):
        errors.append("root sitemap does not reference sitemap-tips.xml")
    robots = site / "robots.txt"
    if not robots.is_file() or (BASE + "sitemap.xml") not in robots.read_text(encoding="utf-8"):
        errors.append("robots.txt does not reference root sitemap")

    report = {
        "version": 234,
        "status": "passed" if not errors else "failed",
        "pages": len(pages),
        "guides": data.get("guide_count"),
        "categories": data.get("category_count"),
        "sitemap_urls": len(sitemap_urls),
        "minimum_arabic_words": min((int(metric["arabic_words"]) for metric in metrics), default=0),
        "minimum_internal_links": min((int(metric["internal_links"]) for metric in metrics), default=0),
        "unique_titles": len({str(metric["title"]).casefold() for metric in metrics}),
        "unique_descriptions": len({str(metric["description"]).casefold() for metric in metrics}),
        "unique_canonicals": len({str(metric["canonical"]).casefold() for metric in metrics}),
        "errors": errors[:200],
    }
    output = site / "api/tips-verification-v234.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("\n".join(errors[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
