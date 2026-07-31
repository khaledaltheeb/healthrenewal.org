from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from xml.etree import ElementTree as ET

BASE_ORIGIN = "https://healthrenewal.org"
BASE_PATH = "/"
BASE_URL = BASE_ORIGIN + BASE_PATH
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
GENERIC_ANCHORS = {
    "هنا",
    "اضغط هنا",
    "انقر هنا",
    "المزيد",
    "اقرأ المزيد",
    "رابط",
    "click here",
    "read more",
    "more",
}


@dataclass
class Link:
    href: str
    text: str


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.html_lang = ""
        self.title_parts: list[str] = []
        self.h1_parts: list[list[str]] = []
        self.meta_description = ""
        self.robots = ""
        self.canonical = ""
        self.hreflang: dict[str, str] = {}
        self.links: list[Link] = []
        self._current_anchor: dict[str, Any] | None = None
        self._json_ld_active = False
        self._json_ld_parts: list[str] = []
        self.json_ld_payloads: list[Any] = []
        self.h2_count = 0
        self.h3_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = {key.lower(): (value or "") for key, value in attrs}
        self.stack.append(tag)
        if tag == "html":
            self.html_lang = data.get("lang", "").strip().lower()
        elif tag == "meta":
            name = data.get("name", "").strip().lower()
            if name == "description":
                self.meta_description = data.get("content", "").strip()
            elif name == "robots":
                self.robots = data.get("content", "").strip().lower()
        elif tag == "link":
            rel = {item.strip().lower() for item in data.get("rel", "").split() if item.strip()}
            href = data.get("href", "").strip()
            if "canonical" in rel:
                self.canonical = href
            if "alternate" in rel and data.get("hreflang", "").strip():
                self.hreflang[data["hreflang"].strip().lower()] = href
        elif tag == "a":
            self._current_anchor = {"href": data.get("href", "").strip(), "parts": []}
        elif tag == "h1":
            self.h1_parts.append([])
        elif tag == "h2":
            self.h2_count += 1
        elif tag == "h3":
            self.h3_count += 1
        elif tag == "script" and data.get("type", "").strip().lower() == "application/ld+json":
            self._json_ld_active = True
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._current_anchor is not None:
            text = normalized_text(" ".join(self._current_anchor["parts"]))
            self.links.append(Link(self._current_anchor["href"], text))
            self._current_anchor = None
        elif tag == "script" and self._json_ld_active:
            raw = "".join(self._json_ld_parts).strip()
            if raw:
                try:
                    self.json_ld_payloads.append(json.loads(raw))
                except json.JSONDecodeError:
                    self.json_ld_payloads.append({"_invalid_json_ld": True})
            self._json_ld_active = False
            self._json_ld_parts = []
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._json_ld_active:
            self._json_ld_parts.append(data)
            return
        text = normalized_text(data)
        if not text:
            return
        if self.stack and self.stack[-1] == "title":
            self.title_parts.append(text)
        if "h1" in self.stack and self.h1_parts:
            self.h1_parts[-1].append(text)
        if self._current_anchor is not None:
            self._current_anchor["parts"].append(text)

    @property
    def title(self) -> str:
        return normalized_text(" ".join(self.title_parts))

    @property
    def h1_values(self) -> list[str]:
        return [normalized_text(" ".join(parts)) for parts in self.h1_parts]


def normalized_text(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip()


def normalized_key(value: str) -> str:
    return normalized_text(value).casefold()


def expected_url(site: Path, path: Path) -> str:
    rel = path.relative_to(site).as_posix()
    if rel == "index.html":
        return BASE_URL
    if rel.endswith("/index.html"):
        return BASE_ORIGIN + BASE_PATH + rel[: -len("index.html")]
    return BASE_ORIGIN + BASE_PATH + rel


def normalize_url(value: str, source_url: str | None = None) -> str:
    if not value:
        return ""
    absolute = urljoin(source_url or BASE_URL, value)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlparse(absolute)
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    if not path.endswith("/") and not Path(path).suffix:
        path += "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def is_internal(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc == "khaledaltheeb.github.io" and parsed.path.startswith(BASE_PATH)


def is_indexable(robots: str) -> bool:
    directives = {item.strip() for item in robots.split(",") if item.strip()}
    return "noindex" not in directives


def flatten_schema_types(payload: Any) -> list[str]:
    types: list[str] = []
    if isinstance(payload, dict):
        value = payload.get("@type")
        if isinstance(value, str):
            types.append(value)
        elif isinstance(value, list):
            types.extend(str(item) for item in value)
        for child in payload.values():
            types.extend(flatten_schema_types(child))
    elif isinstance(payload, list):
        for child in payload:
            types.extend(flatten_schema_types(child))
    return types


def sitemap_urls(site: Path) -> tuple[set[str], list[str]]:
    urls: set[str] = set()
    errors: list[str] = []
    seen: set[Path] = set()
    queue = [site / "sitemap.xml"]
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            errors.append(f"Missing sitemap file: {path.relative_to(site).as_posix()}")
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            errors.append(f"Invalid XML {path.relative_to(site).as_posix()}: {exc}")
            continue
        kind = root.tag.rsplit("}", 1)[-1]
        if kind == "sitemapindex":
            for loc in root.findall(f"{namespace}sitemap/{namespace}loc"):
                value = normalized_text(loc.text or "")
                parsed = urlparse(value)
                if parsed.netloc != "khaledaltheeb.github.io" or not parsed.path.startswith(BASE_PATH):
                    errors.append(f"External or off-base sitemap reference: {value}")
                    continue
                child = site / parsed.path[len(BASE_PATH) :]
                queue.append(child)
        elif kind == "urlset":
            for loc in root.findall(f"{namespace}url/{namespace}loc"):
                value = normalize_url(normalized_text(loc.text or ""))
                if value:
                    urls.add(value)
        else:
            errors.append(f"Unsupported sitemap root {kind}: {path.relative_to(site).as_posix()}")
    return urls, errors


def audit(site: Path) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    page_by_url: dict[str, dict[str, Any]] = {}
    titles: Counter[str] = Counter()
    descriptions: Counter[str] = Counter()
    canonicals: defaultdict[str, list[str]] = defaultdict(list)
    outgoing: defaultdict[str, set[str]] = defaultdict(set)
    incoming: Counter[str] = Counter()
    generic_anchors: list[dict[str, str]] = []

    html_files = sorted(site.rglob("*.html"))
    for path in html_files:
        raw = path.read_text(encoding="utf-8", errors="strict")
        parser = PageParser()
        parser.feed(raw)
        url = normalize_url(expected_url(site, path))
        canonical = normalize_url(parser.canonical, url) if parser.canonical else ""
        indexable = is_indexable(parser.robots)
        schema_types = sorted(set(type_name for payload in parser.json_ld_payloads for type_name in flatten_schema_types(payload)))
        internal_links: set[str] = set()
        for link in parser.links:
            if not link.href or link.href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
                continue
            target = normalize_url(link.href, url)
            if is_internal(target):
                internal_links.add(target)
                if not link.text or normalized_key(link.text) in GENERIC_ANCHORS:
                    generic_anchors.append({"source": url, "target": target, "anchor": link.text})

        page = {
            "path": path.relative_to(site).as_posix(),
            "url": url,
            "lang": parser.html_lang,
            "title": parser.title,
            "description": parser.meta_description,
            "h1_values": parser.h1_values,
            "h2_count": parser.h2_count,
            "h3_count": parser.h3_count,
            "canonical": canonical,
            "robots": parser.robots,
            "indexable": indexable,
            "hreflang": parser.hreflang,
            "schema_types": schema_types,
            "internal_outgoing": len(internal_links),
        }
        pages.append(page)
        page_by_url[url] = page
        outgoing[url] = internal_links
        if parser.title:
            titles[normalized_key(parser.title)] += 1
        if parser.meta_description:
            descriptions[normalized_key(parser.meta_description)] += 1
        if canonical:
            canonicals[canonical].append(url)

        def add_error(code: str, message: str) -> None:
            errors.append({"code": code, "url": url, "message": message})

        def add_warning(code: str, message: str) -> None:
            warnings.append({"code": code, "url": url, "message": message})

        if not parser.title:
            add_error("missing-title", "Page has no title element.")
        if not parser.meta_description:
            add_error("missing-description", "Page has no meta description.")
        if len(parser.h1_values) != 1 or not parser.h1_values[0]:
            add_error("invalid-h1-count", f"Expected one non-empty H1, found {len(parser.h1_values)}.")
        if not canonical:
            add_error("missing-canonical", "Page has no canonical URL.")
        elif canonical != url:
            add_warning("non-self-canonical", f"Canonical {canonical} differs from page URL {url}.")
        parsed_canonical = urlparse(canonical) if canonical else None
        if parsed_canonical and (parsed_canonical.scheme != "https" or parsed_canonical.netloc != "khaledaltheeb.github.io" or not parsed_canonical.path.startswith(BASE_PATH)):
            add_error("invalid-canonical-scope", f"Canonical is outside the HTTPS production base: {canonical}.")
        if any(isinstance(payload, dict) and payload.get("_invalid_json_ld") for payload in parser.json_ld_payloads):
            add_error("invalid-json-ld", "Page contains invalid JSON-LD.")
        if not schema_types:
            add_warning("missing-schema", "Page contains no parseable schema.org @type.")
        if parser.html_lang and parser.html_lang not in {"ar", "en", "es"}:
            add_warning("unexpected-language", f"Unexpected html lang value: {parser.html_lang}.")
        for language, href in parser.hreflang.items():
            normalized = normalize_url(href, url)
            if not is_internal(normalized):
                add_error("invalid-hreflang-target", f"hreflang {language} points outside the production base: {href}.")

    for source, targets in outgoing.items():
        for target in targets:
            if target in page_by_url:
                incoming[target] += 1
            else:
                warnings.append({"code": "broken-internal-link", "url": source, "message": f"Internal target is not an HTML page in the artifact: {target}."})

    indexed_urls, sitemap_errors = sitemap_urls(site)
    for message in sitemap_errors:
        errors.append({"code": "sitemap-error", "url": BASE_URL, "message": message})

    for canonical, source_urls in canonicals.items():
        if len(source_urls) > 1:
            errors.append({"code": "duplicate-canonical", "url": canonical, "message": f"Canonical is claimed by {len(source_urls)} pages: {', '.join(source_urls[:8])}."})

    for key, count in titles.items():
        if count > 1:
            warnings.append({"code": "duplicate-title", "url": BASE_URL, "message": f"Title is reused {count} times: {key[:160]}."})
    for key, count in descriptions.items():
        if count > 1:
            warnings.append({"code": "duplicate-description", "url": BASE_URL, "message": f"Meta description is reused {count} times: {key[:180]}."})

    for page in pages:
        url = page["url"]
        if page["indexable"] and url not in indexed_urls:
            warnings.append({"code": "indexable-page-missing-from-sitemap", "url": url, "message": "Indexable HTML page is absent from the discovered sitemap set."})
        if not page["indexable"] and url in indexed_urls:
            errors.append({"code": "noindex-in-sitemap", "url": url, "message": "A noindex page is included in a sitemap."})
        if url != BASE_URL and incoming[url] == 0:
            warnings.append({"code": "orphan-page", "url": url, "message": "Page has no incoming internal link from another HTML page in the artifact."})
        page["internal_incoming"] = incoming[url]
        page["in_sitemap"] = url in indexed_urls

    rows = sorted(pages, key=lambda item: item["url"])
    report = {
        "version": "162-search-architecture",
        "pages_scanned": len(rows),
        "sitemap_urls": len(indexed_urls),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "indexable_pages": sum(bool(page["indexable"]) for page in rows),
        "pages_in_sitemap": sum(bool(page["in_sitemap"]) for page in rows),
        "orphan_pages": sum(page["url"] != BASE_URL and int(page["internal_incoming"]) == 0 for page in rows),
        "pages_with_schema": sum(bool(page["schema_types"]) for page in rows),
        "duplicate_canonical_values": sum(len(urls) > 1 for urls in canonicals.values()),
        "duplicate_title_values": sum(count > 1 for count in titles.values()),
        "duplicate_description_values": sum(count > 1 for count in descriptions.values()),
        "generic_or_empty_internal_anchors": len(generic_anchors),
        "errors": errors[:2000],
        "warnings": warnings[:4000],
        "generic_anchors": generic_anchors[:1000],
        "pages": rows,
        "policy": {
            "advisory_only": True,
            "automatic_url_or_canonical_changes": False,
            "automatic_redirect_merge_delete_or_noindex": False,
            "blocking_codes": [
                "missing-title",
                "missing-description",
                "invalid-h1-count",
                "missing-canonical",
                "invalid-canonical-scope",
                "invalid-json-ld",
                "duplicate-canonical",
                "noindex-in-sitemap",
                "sitemap-error"
            ],
        },
    }
    return report


def write_csv(report: dict[str, Any], path: Path) -> None:
    fields = [
        "path",
        "url",
        "lang",
        "title",
        "description",
        "h1_count",
        "h2_count",
        "h3_count",
        "canonical",
        "indexable",
        "in_sitemap",
        "internal_incoming",
        "internal_outgoing",
        "schema_types",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for page in report["pages"]:
            writer.writerow({
                "path": page["path"],
                "url": page["url"],
                "lang": page["lang"],
                "title": page["title"],
                "description": page["description"],
                "h1_count": len(page["h1_values"]),
                "h2_count": page["h2_count"],
                "h3_count": page["h3_count"],
                "canonical": page["canonical"],
                "indexable": page["indexable"],
                "in_sitemap": page["in_sitemap"],
                "internal_incoming": page["internal_incoming"],
                "internal_outgoing": page["internal_outgoing"],
                "schema_types": "|".join(page["schema_types"]),
            })


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit SEO and internal search architecture of a generated static site.")
    parser.add_argument("site", nargs="?", default="_site")
    parser.add_argument("--json", default="artifacts/search-architecture-v162.json")
    parser.add_argument("--csv", default="artifacts/search-architecture-v162.csv")
    parser.add_argument("--fail-on-errors", action="store_true")
    args = parser.parse_args()
    site = Path(args.site).resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    report = audit(site)
    json_path = Path(args.json).resolve()
    csv_path = Path(args.csv).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(report, csv_path)
    print(json.dumps({
        key: report[key]
        for key in (
            "pages_scanned",
            "sitemap_urls",
            "error_count",
            "warning_count",
            "orphan_pages",
            "duplicate_canonical_values",
            "duplicate_title_values",
            "duplicate_description_values",
        )
    }, ensure_ascii=False, indent=2))
    if args.fail_on_errors and report["error_count"]:
        raise SystemExit("\n".join(f"{item['code']}: {item['url']}: {item['message']}" for item in report["errors"][:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
