#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

CANONICAL = "https://healthrenewal.org/sectors/"
REQUIRED_SCHEMAS = {"CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"}
REQUIRED_SECTIONS = {
    "choose-sector",
    "distinction",
    "need-map",
    "method",
    "safety",
    "evidence",
    "faq",
}
SECTOR_LINKS = ("child/", "youth/", "family/", "home/", "women/")
REQUIRED_MARKERS = (
    "عند وجود خطر مباشر لا تبدأ بالتصفح",
    "ثلاثة مستويات للحاجة إلى المساعدة",
    "لا تثبت تشخيصًا",
    "مراجعة تحريرية ومنهجية داخلية",
    "لا يُفهم منها اكتمال مراجعة سريرية خارجية مستقلة",
)
BANNED_TERMS = ("معاقين", "علاج مضمون", "نتائج مضمونة للجميع")
MIN_VISIBLE_WORDS = 1850
ALLOWED_SOURCE_HOSTS = {"www.who.int", "www.unicef.org"}


class PortalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.visible_parts: list[str] = []
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.headings: list[int] = []
        self.tag_counts: Counter[str] = Counter()
        self.meta: dict[str, str] = {}
        self.canonicals: list[str] = []
        self.json_ld_raw: list[str] = []
        self._json_buffer: list[str] | None = None
        self.html_attrs: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): value or "" for key, value in attrs}
        self.stack.append(tag)
        self.tag_counts[tag] += 1
        if tag == "html":
            self.html_attrs = attr
        if "id" in attr:
            self.ids.append(attr["id"])
        if tag == "a":
            self.hrefs.append(attr.get("href", ""))
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "meta":
            key = attr.get("name") or attr.get("property")
            if key:
                self.meta[key.lower()] = attr.get("content", "")
        if tag == "link" and attr.get("rel", "").lower() == "canonical":
            self.canonicals.append(attr.get("href", ""))
        if tag == "script" and attr.get("type", "").lower() == "application/ld+json":
            self._json_buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._json_buffer is not None:
            self.json_ld_raw.append("".join(self._json_buffer))
            self._json_buffer = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._json_buffer is not None:
            self._json_buffer.append(data)
            return
        if any(tag in self.stack for tag in ("script", "style", "svg", "template", "noscript")):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.visible_parts.append(value)


def _schema_types(payload: object) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        value = payload.get("@type")
        if isinstance(value, str):
            found.add(value)
        elif isinstance(value, list):
            found.update(item for item in value if isinstance(item, str))
        for child in payload.values():
            found.update(_schema_types(child))
    elif isinstance(payload, list):
        for child in payload:
            found.update(_schema_types(child))
    return found


def _faq_count(payload: object) -> int:
    if isinstance(payload, dict):
        if payload.get("@type") == "FAQPage":
            entities = payload.get("mainEntity")
            return len(entities) if isinstance(entities, list) else 0
        return max((_faq_count(value) for value in payload.values()), default=0)
    if isinstance(payload, list):
        return max((_faq_count(value) for value in payload), default=0)
    return 0


def validate(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    parser = PortalParser()
    parser.feed(source)

    errors: list[str] = []
    if not re.match(r"\s*<!doctype html>", source, flags=re.I):
        errors.append("missing HTML5 doctype")
    if parser.html_attrs.get("lang") != "ar" or parser.html_attrs.get("dir") != "rtl":
        errors.append("html must declare lang=ar and dir=rtl")
    if parser.tag_counts["h1"] != 1:
        errors.append(f"expected one H1, found {parser.tag_counts['h1']}")
    if parser.tag_counts["main"] != 1:
        errors.append(f"expected one main, found {parser.tag_counts['main']}")
    if parser.tag_counts["header"] != 1 or parser.tag_counts["footer"] != 1:
        errors.append("expected one semantic header and footer")
    if parser.tag_counts["details"] < 5:
        errors.append("expected at least five visible FAQ details")

    duplicate_ids = sorted(key for key, count in Counter(parser.ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate ids: {duplicate_ids}")
    missing_sections = sorted(REQUIRED_SECTIONS.difference(parser.ids))
    if missing_sections:
        errors.append(f"missing section ids: {missing_sections}")

    for previous, current in zip(parser.headings, parser.headings[1:]):
        if current > previous + 1:
            errors.append(f"heading level jump: H{previous} to H{current}")
            break

    visible_text = " ".join(parser.visible_parts)
    visible_words = len(re.findall(r"[\w\u0600-\u06ff]+", visible_text, flags=re.UNICODE))
    if visible_words < MIN_VISIBLE_WORDS:
        errors.append(f"visible word count {visible_words} is below {MIN_VISIBLE_WORDS}")

    lower = source.lower()
    if "noindex" in lower:
        errors.append("portal must remain indexable")
    for term in BANNED_TERMS:
        if term in source:
            errors.append(f"banned term present: {term}")
    for marker in REQUIRED_MARKERS:
        if marker not in visible_text:
            errors.append(f"required safety/method marker missing: {marker}")

    if parser.canonicals != [CANONICAL]:
        errors.append(f"canonical mismatch: {parser.canonicals}")
    required_meta = {
        "description",
        "robots",
        "googlebot",
        "og:title",
        "og:description",
        "og:url",
        "twitter:card",
        "twitter:title",
        "twitter:description",
    }
    missing_meta = sorted(key for key in required_meta if not parser.meta.get(key))
    if missing_meta:
        errors.append(f"missing metadata: {missing_meta}")
    description_length = len(parser.meta.get("description", ""))
    if not 120 <= description_length <= 190:
        errors.append(f"meta description length is {description_length}, expected 120-190")
    if parser.meta.get("og:url") != CANONICAL:
        errors.append("og:url must equal canonical")

    for href in SECTOR_LINKS:
        count = parser.hrefs.count(href)
        if count < 2:
            errors.append(f"sector link {href} appears only {count} time(s)")
    empty_links = [href for href in parser.hrefs if not href or href.strip() == "#"]
    if empty_links:
        errors.append("empty or placeholder links found")

    external_sources = [
        href for href in parser.hrefs
        if href.startswith("http://") or href.startswith("https://")
    ]
    if len(external_sources) < 4:
        errors.append("expected at least four institutional source links")
    for href in external_sources:
        parsed = urlparse(href)
        if parsed.scheme != "https":
            errors.append(f"non-HTTPS external link: {href}")
        if parsed.hostname not in ALLOWED_SOURCE_HOSTS:
            errors.append(f"unexpected external source host: {parsed.hostname}")

    schemas: list[object] = []
    for raw in parser.json_ld_raw:
        try:
            schemas.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON-LD: {exc}")
    types: set[str] = set()
    for payload in schemas:
        types.update(_schema_types(payload))
    missing_schemas = sorted(REQUIRED_SCHEMAS.difference(types))
    if missing_schemas:
        errors.append(f"missing schema types: {missing_schemas}")
    faq_count = max((_faq_count(payload) for payload in schemas), default=0)
    if faq_count < 5:
        errors.append(f"FAQPage has {faq_count} questions, expected at least 5")

    report: dict[str, object] = {
        "status": "passed" if not errors else "failed",
        "version": 327,
        "path": str(path),
        "visible_words": visible_words,
        "h1": parser.tag_counts["h1"],
        "h2": parser.tag_counts["h2"],
        "h3": parser.tag_counts["h3"],
        "faq_items": parser.tag_counts["details"],
        "schema_types": sorted(types),
        "sector_link_counts": {href: parser.hrefs.count(href) for href in SECTOR_LINKS},
        "external_source_links": len(external_sources),
        "duplicate_ids": duplicate_ids,
        "errors": errors,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Verify the institutional sectors portal v327.")
    cli.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "sectors" / "index.html",
    )
    cli.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = cli.parse_args(argv)
    report = validate(args.path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
