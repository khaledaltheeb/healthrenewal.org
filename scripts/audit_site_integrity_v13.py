from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://healthrenewal.org/"
_BASE_PARSED = urlparse(BASE_URL)
BASE_HOST = _BASE_PARSED.netloc
BASE_PATH = _BASE_PARSED.path or "/"
VERIFY = "google644f1f7a8b7aaa2b.html"
LOCALE_CONTRACTS = {
    "en": ("en", "ltr"),
    "es": ("es", "ltr"),
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []
        self.ids: list[str] = []
        self.html_attrs: dict[str, str | None] = {}
        self.title_count = 0
        self.description_count = 0
        self.canonical_count = 0
        self.viewport_count = 0
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "html":
            self.html_attrs = data
        if tag == "title":
            self.title_count += 1
        if tag == "h1":
            self.h1_count += 1
        if data.get("id"):
            self.ids.append(str(data["id"]))
        if tag == "meta" and str(data.get("name", "")).lower() == "description":
            self.description_count += 1
        if tag == "meta" and str(data.get("name", "")).lower() == "viewport":
            self.viewport_count += 1
        if tag == "link" and "canonical" in str(data.get("rel", "")).lower().split():
            self.canonical_count += 1
        for attr in ("href", "src", "poster"):
            value = data.get(attr)
            if value:
                self.refs.append((attr, str(value)))
        if data.get("srcset"):
            for candidate in str(data["srcset"]).split(","):
                url = candidate.strip().split()[0] if candidate.strip() else ""
                if url:
                    self.refs.append(("srcset", url))


def expected_language_direction(relative_path: str) -> tuple[str, str]:
    parts = Path(relative_path).parts
    if parts and parts[0] in LOCALE_CONTRACTS:
        return LOCALE_CONTRACTS[parts[0]]
    return "ar", "rtl"


def target_from_reference(page: Path, value: str) -> tuple[Path | None, str | None, bool]:
    value = value.strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None, None, False
    parsed = urlparse(value)
    fragment = parsed.fragment or None
    external = False
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc != BASE_HOST or not parsed.path.startswith(BASE_PATH):
            return None, fragment, True
        raw_path = parsed.path[len(BASE_PATH):]
    elif parsed.scheme:
        return None, fragment, True
    elif parsed.path.startswith(BASE_PATH):
        raw_path = parsed.path[len(BASE_PATH):]
    elif parsed.path.startswith("/"):
        return None, fragment, True
    else:
        raw_path = parsed.path
        base = page.parent.relative_to(SITE)
        raw_path = (base / unquote(raw_path)).as_posix()

    raw_path = unquote(raw_path).lstrip("/")
    target = (SITE / raw_path).resolve()
    try:
        target.relative_to(SITE)
    except ValueError:
        return target, fragment, external
    if value.endswith("/") or parsed.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    elif not target.suffix and not target.exists():
        target = target / "index.html"
    return target, fragment, external


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    return parser


def main() -> int:
    if not SITE.exists():
        raise SystemExit(f"Site directory does not exist: {SITE}")

    errors: list[str] = []
    warnings: list[str] = []
    html_files = sorted(SITE.rglob("*.html"))
    verification = SITE / VERIFY
    content_pages = [p for p in html_files if p != verification]
    parsed_pages: dict[Path, PageParser] = {}
    ids_by_page: dict[Path, set[str]] = {}
    internal_reference_count = 0
    external_reference_count = 0
    checked_targets: set[Path] = set()
    locale_page_counts: Counter[str] = Counter()

    for page in content_pages:
        rel = page.relative_to(SITE).as_posix()
        try:
            parser = parse_page(page)
        except Exception as exc:
            errors.append(f"Unreadable HTML {rel}: {exc}")
            continue
        parsed_pages[page] = parser
        ids_by_page[page] = set(parser.ids)
        duplicate_ids = [value for value, count in Counter(parser.ids).items() if count > 1]
        if duplicate_ids:
            errors.append(f"Duplicate IDs in {rel}: {duplicate_ids[:8]}")
        expected_lang, expected_dir = expected_language_direction(rel)
        locale_page_counts[expected_lang] += 1
        if parser.html_attrs.get("lang") != expected_lang:
            errors.append(f"Missing or incorrect lang={expected_lang} in {rel}")
        if parser.html_attrs.get("dir") != expected_dir:
            errors.append(f"Missing or incorrect dir={expected_dir} in {rel}")
        if parser.title_count != 1:
            errors.append(f"Expected one title in {rel}, found {parser.title_count}")
        if parser.description_count != 1:
            errors.append(f"Expected one meta description in {rel}, found {parser.description_count}")
        if parser.canonical_count != 1:
            errors.append(f"Expected one canonical in {rel}, found {parser.canonical_count}")
        if parser.viewport_count != 1:
            errors.append(f"Expected one viewport in {rel}, found {parser.viewport_count}")
        if parser.h1_count != 1:
            errors.append(f"Expected one h1 in {rel}, found {parser.h1_count}")

    for page, parser in parsed_pages.items():
        page_rel = page.relative_to(SITE).as_posix()
        for attr, value in parser.refs:
            target, fragment, external = target_from_reference(page, value)
            if external:
                external_reference_count += 1
                parsed = urlparse(value)
                if parsed.scheme == "http":
                    warnings.append(f"Non-HTTPS external reference in {page_rel}: {value}")
                continue
            if target is None:
                continue
            internal_reference_count += 1
            checked_targets.add(target)
            try:
                rel_target = target.relative_to(SITE).as_posix()
            except ValueError:
                errors.append(f"Reference escapes site root in {page_rel}: {value}")
                continue
            if not target.exists():
                errors.append(f"Broken internal {attr} in {page_rel}: {value} -> {rel_target}")
                continue
            if fragment and target.suffix.lower() in {".html", ""}:
                target_page = target if target.suffix.lower() == ".html" else target / "index.html"
                if target_page.exists():
                    if target_page not in ids_by_page:
                        try:
                            parsed_target = parse_page(target_page)
                            ids_by_page[target_page] = set(parsed_target.ids)
                        except Exception as exc:
                            errors.append(f"Could not parse anchor target {rel_target}: {exc}")
                            continue
                    if fragment not in ids_by_page[target_page]:
                        errors.append(f"Missing anchor #{fragment} in {rel_target}, referenced from {page_rel}")

    required = [
        "index.html",
        "robots.txt",
        "sitemap.xml",
        "manifest.webmanifest",
        VERIFY,
        "assets/css/theme-v10.css",
        "assets/css/marshmallow-v12.css",
        "assets/css/encyclopedia-v13.css",
        "assets/js/app-v10.js",
        "assets/js/lab-v12.js",
        "api/encyclopedia-audit-v13.json",
    ]
    for rel in required:
        if not (SITE / rel).exists():
            errors.append(f"Missing required production file: {rel}")

    sitemap_index = SITE / "sitemap.xml"
    sitemap_files: list[Path] = []
    sitemap_urls: list[str] = []
    if sitemap_index.exists():
        try:
            root = ET.parse(sitemap_index).getroot()
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            if not root.tag.endswith("sitemapindex"):
                errors.append("sitemap.xml is not a sitemapindex")
            for node in root.findall("s:sitemap/s:loc", ns):
                if not node.text:
                    errors.append("Empty sitemap loc in sitemap index")
                    continue
                parsed = urlparse(node.text)
                if parsed.netloc != BASE_HOST or not parsed.path.startswith(BASE_PATH):
                    errors.append(f"Unexpected sitemap location: {node.text}")
                    continue
                rel = unquote(parsed.path[len(BASE_PATH):])
                path = SITE / rel
                sitemap_files.append(path)
                if not path.exists():
                    errors.append(f"Missing sitemap referenced by index: {rel}")
            for path in sitemap_files:
                try:
                    map_root = ET.parse(path).getroot()
                except Exception as exc:
                    errors.append(f"Unreadable sitemap {path.name}: {exc}")
                    continue
                for node in map_root.findall("s:url/s:loc", ns):
                    if node.text:
                        sitemap_urls.append(node.text)
                        parsed = urlparse(node.text)
                        if parsed.netloc == BASE_HOST and parsed.path.startswith(BASE_PATH):
                            rel = unquote(parsed.path[len(BASE_PATH):])
                            target = SITE / rel
                            if parsed.path.endswith("/") or target.is_dir():
                                target = target / "index.html"
                            elif not target.suffix:
                                target = target / "index.html"
                            if not target.exists():
                                errors.append(f"Sitemap URL has no published target: {node.text}")
        except Exception as exc:
            errors.append(f"Could not parse sitemap.xml: {exc}")
    duplicate_sitemap_urls = [url for url, count in Counter(sitemap_urls).items() if count > 1]
    if duplicate_sitemap_urls:
        errors.append(f"Duplicate sitemap URLs: {duplicate_sitemap_urls[:10]}")

    if verification.exists():
        expected = "google-site-verification: google644f1f7a8b7aaa2b.html"
        if verification.read_text(encoding="utf-8").strip() != expected:
            errors.append("Google Search Console verification file changed")

    report = {
        "version": "13-integrity-i18n-v72",
        "html_pages": len(html_files),
        "content_pages": len(content_pages),
        "parsed_pages": len(parsed_pages),
        "locale_page_counts": dict(sorted(locale_page_counts.items())),
        "locale_contracts": {
            locale: {"lang": contract[0], "dir": contract[1]}
            for locale, contract in LOCALE_CONTRACTS.items()
        },
        "internal_references_checked": internal_reference_count,
        "external_references_seen": external_reference_count,
        "unique_internal_targets": len(checked_targets),
        "sitemap_files": len(sitemap_files),
        "sitemap_urls": len(sitemap_urls),
        "warnings": warnings[:200],
        "warning_count": len(warnings),
        "errors": errors[:500],
        "error_count": len(errors),
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "site-integrity-v13.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("\n".join(errors[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
