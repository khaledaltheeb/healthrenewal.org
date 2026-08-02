from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://healthrenewal.org/"
BASE_HOST = urlparse(BASE_URL).netloc
BASE_PATH = "/"
VERIFY = "google644f1f7a8b7aaa2b.html"


class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: Counter[str] = Counter()
        self.refs: list[tuple[str, str, str]] = []
        self.ids: list[str] = []
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.current_title = False
        self.meta: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.scripts: list[dict[str, str | None]] = []
        self.images: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []
        self.inputs: list[dict[str, str | None]] = []
        self.labels_for: set[str] = set()
        self.html_attrs: dict[str, str | None] = {}
        self.heading_levels: list[int] = []
        self.inline_style_values: list[str] = []
        self.jsonld_blocks: list[str] = []
        self._jsonld = False
        self._jsonld_parts: list[str] = []
        self._button_depth = 0
        self._button_text: list[str] = []
        self.button_texts: list[str] = []
        self._anchor_depth = 0
        self._anchor_text: list[str] = []
        self.anchor_texts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        self.tags[tag] += 1
        if tag == "html":
            self.html_attrs = data
        if tag == "title":
            self.current_title = True
        if re.fullmatch(r"h[1-6]", tag):
            self.heading_levels.append(int(tag[1]))
        if data.get("id"):
            self.ids.append(str(data["id"]))
        if data.get("style"):
            self.inline_style_values.append(str(data["style"]))
        if tag == "meta":
            self.meta.append(data)
        if tag == "link":
            self.links.append(data)
        if tag == "script":
            self.scripts.append(data)
            if str(data.get("type", "")).lower() == "application/ld+json":
                self._jsonld = True
                self._jsonld_parts = []
        if tag == "img":
            self.images.append(data)
        if tag == "button":
            self.buttons.append(data)
            self._button_depth += 1
            self._button_text = []
        if tag == "a":
            self._anchor_depth += 1
            self._anchor_text = []
        if tag == "input":
            self.inputs.append(data)
        if tag == "label" and data.get("for"):
            self.labels_for.add(str(data["for"]))
        for attr in ("href", "src", "poster"):
            if data.get(attr):
                self.refs.append((tag, attr, str(data[attr])))
        if data.get("srcset"):
            for candidate in str(data["srcset"]).split(","):
                value = candidate.strip().split()[0] if candidate.strip() else ""
                if value:
                    self.refs.append((tag, "srcset", value))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.current_title = False
        if tag == "script" and self._jsonld:
            self.jsonld_blocks.append("".join(self._jsonld_parts).strip())
            self._jsonld = False
            self._jsonld_parts = []
        if tag == "button" and self._button_depth:
            self.button_texts.append(" ".join(self._button_text).strip())
            self._button_depth -= 1
            self._button_text = []
        if tag == "a" and self._anchor_depth:
            self.anchor_texts.append(" ".join(self._anchor_text).strip())
            self._anchor_depth -= 1
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        clean = re.sub(r"\s+", " ", data).strip()
        if self.current_title and clean:
            self.title_parts.append(clean)
        if self._jsonld:
            self._jsonld_parts.append(data)
            return
        if clean:
            self.text_parts.append(clean)
            if self._button_depth:
                self._button_text.append(clean)
            if self._anchor_depth:
                self._anchor_text.append(clean)


def parse_page(path: Path) -> AuditParser:
    parser = AuditParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    return parser


def meta_value(parser: AuditParser, key: str, *, prop: bool = False) -> list[str]:
    attr = "property" if prop else "name"
    return [str(x.get("content", "")) for x in parser.meta if str(x.get(attr, "")).lower() == key.lower()]


def link_values(parser: AuditParser, rel: str) -> list[str]:
    result = []
    for item in parser.links:
        rels = str(item.get("rel", "")).lower().split()
        if rel in rels and item.get("href"):
            result.append(str(item["href"]))
    return result


def local_target(page: Path, value: str) -> Path | None:
    value = value.strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc != BASE_HOST or not parsed.path.startswith(BASE_PATH):
            return None
        raw = parsed.path[len(BASE_PATH):]
    elif parsed.scheme:
        return None
    elif parsed.path.startswith(BASE_PATH):
        raw = parsed.path[len(BASE_PATH):]
    elif parsed.path.startswith("/"):
        return None
    else:
        raw = (page.parent.relative_to(SITE) / unquote(parsed.path)).as_posix()
    raw = unquote(raw).lstrip("/")
    target = (SITE / raw).resolve()
    try:
        target.relative_to(SITE)
    except ValueError:
        return target
    if parsed.path.endswith("/") or target.is_dir() or (not target.suffix and not target.exists()):
        target = target / "index.html"
    return target



def legacy_alias_contract(page: Path, parser: AuditParser) -> tuple[bool, str | None, list[str]]:
    """Validate explicit noindex redirect aliases without treating them as indexable content."""
    marker = str(parser.html_attrs.get("data-legacy-path-alias") or "").strip()
    if not marker:
        return False, None, []

    rel = page.relative_to(SITE).as_posix()
    errors: list[str] = []
    robots = meta_value(parser, "robots")
    directives = {
        item.strip().lower()
        for value in robots
        for item in value.split(",")
        if item.strip()
    }
    if len(robots) != 1 or not {"noindex", "follow"}.issubset(directives):
        errors.append(f"Legacy alias robots contract failed in {rel}: {robots}")

    refresh = [
        item for item in parser.meta
        if str(item.get("http-equiv", "")).lower() == "refresh"
    ]
    destination = ""
    if len(refresh) != 1:
        errors.append(f"Legacy alias requires one meta refresh in {rel}, found {len(refresh)}")
    else:
        content = str(refresh[0].get("content", ""))
        match = re.match(r"^\s*0\s*;\s*url\s*=\s*(.+?)\s*$", content, re.I)
        if not match:
            errors.append(f"Legacy alias refresh must be immediate in {rel}: {content}")
        else:
            destination = match.group(1).strip("\"' ")

    canonical_values = link_values(parser, "canonical")
    if len(canonical_values) != 1:
        errors.append(f"Legacy alias requires one canonical in {rel}, found {len(canonical_values)}")

    refresh_target = local_target(page, destination) if destination else None
    canonical_target = local_target(page, canonical_values[0]) if len(canonical_values) == 1 else None
    if refresh_target is None:
        errors.append(f"Legacy alias refresh target is not an internal page in {rel}: {destination}")
    if canonical_target is None:
        errors.append(f"Legacy alias canonical target is not an internal page in {rel}: {canonical_values}")
    if refresh_target is not None and canonical_target is not None and refresh_target != canonical_target:
        errors.append(
            f"Legacy alias refresh/canonical mismatch in {rel}: {destination} != {canonical_values[0]}"
        )

    target = refresh_target or canonical_target
    target_rel: str | None = None
    if target is not None:
        try:
            target_rel = target.relative_to(SITE).as_posix()
        except ValueError:
            errors.append(f"Legacy alias target escapes site root in {rel}: {target}")
        else:
            if target == page.resolve():
                errors.append(f"Legacy alias redirects to itself in {rel}")
            if not target.is_file():
                errors.append(f"Legacy alias target is missing in {rel}: {target_rel}")
    return True, target_rel, errors

def content_minimum(rel: str) -> int:
    if rel.startswith("encyclopedia/concept-"):
        return 1800
    if rel.startswith("tips/") and rel != "tips/index.html":
        return 1800
    if rel.startswith("sectors/") and rel.count("/") >= 2:
        return 650
    if rel.startswith("articles/") or rel.startswith("library/"):
        return 500
    if rel.startswith("comparisons/") or rel.startswith("guided-assessment/"):
        return 450
    if rel.startswith("assessment-lab/") or rel.startswith("cognitive-lab/"):
        return 220
    return 100


def main() -> int:
    if not SITE.exists():
        raise SystemExit(f"Missing site directory: {SITE}")
    errors: list[str] = []
    warnings: list[str] = []
    html_files = sorted(SITE.rglob("*.html"))
    content_files = [p for p in html_files if p.name != VERIFY]
    parsed: dict[Path, AuditParser] = {}
    titles: dict[str, list[str]] = defaultdict(list)
    descriptions: dict[str, list[str]] = defaultdict(list)
    canonicals: dict[str, list[str]] = defaultdict(list)
    text_hashes: dict[str, list[str]] = defaultdict(list)
    jsonld_types: Counter[str] = Counter()
    internal_refs = 0
    external_refs = 0
    blocking_scripts = 0
    empty_links = 0
    unlabeled_inputs = 0
    images_without_alt = 0
    oversized_assets: list[str] = []
    section_counts: Counter[str] = Counter()
    legacy_aliases: dict[str, str] = {}

    for page in content_files:
        rel = page.relative_to(SITE).as_posix()
        section_counts[rel.split("/", 1)[0]] += 1
        try:
            parser = parse_page(page)
        except Exception as exc:
            errors.append(f"Unreadable HTML {rel}: {exc}")
            continue
        parsed[page] = parser
        title = " ".join(parser.title_parts).strip()
        descs = meta_value(parser, "description")
        canonical = link_values(parser, "canonical")
        is_legacy_alias, alias_target, alias_errors = legacy_alias_contract(page, parser)
        errors.extend(alias_errors)
        if is_legacy_alias:
            legacy_aliases[rel] = alias_target or ""
        else:
            titles[title].append(rel)
            if descs:
                descriptions[descs[0]].append(rel)
            if canonical:
                canonicals[canonical[0]].append(rel)

        if parser.html_attrs.get("lang") != "ar" or parser.html_attrs.get("dir") != "rtl":
            errors.append(f"Arabic document attributes missing in {rel}")
        if parser.tags["title"] != 1 or not title:
            errors.append(f"Invalid title in {rel}")
        if not is_legacy_alias:
            if len(descs) != 1 or not (50 <= len(descs[0]) <= 320):
                errors.append(f"Invalid meta description in {rel}: {len(descs[0]) if descs else 0}")
            if len(canonical) != 1:
                errors.append(f"Expected one canonical in {rel}, found {len(canonical)}")
            elif canonical[0] != BASE_URL + ("" if rel == "index.html" else rel.removesuffix("index.html")):
                errors.append(f"Canonical mismatch in {rel}: {canonical[0]}")
        if len(meta_value(parser, "viewport")) != 1:
            errors.append(f"Viewport missing or duplicated in {rel}")
        if len(meta_value(parser, "robots")) != 1:
            errors.append(f"Robots meta missing or duplicated in {rel}")
        if parser.tags["h1"] != 1:
            errors.append(f"Expected one h1 in {rel}, found {parser.tags['h1']}")
        duplicate_ids = [x for x, c in Counter(parser.ids).items() if c > 1]
        if duplicate_ids:
            errors.append(f"Duplicate IDs in {rel}: {duplicate_ids[:6]}")
        if is_legacy_alias:
            continue
        for previous, current in zip(parser.heading_levels, parser.heading_levels[1:]):
            if current > previous + 1:
                warnings.append(f"Heading jump h{previous}->h{current} in {rel}")
                break
        required_social = {
            "og:title": meta_value(parser, "og:title", prop=True),
            "og:description": meta_value(parser, "og:description", prop=True),
            "og:url": meta_value(parser, "og:url", prop=True),
            "og:type": meta_value(parser, "og:type", prop=True),
            "twitter:card": meta_value(parser, "twitter:card"),
        }
        for key, values in required_social.items():
            if not values:
                warnings.append(f"Missing {key} in {rel}")
        if not link_values(parser, "manifest"):
            warnings.append(f"Manifest link missing in {rel}")
        if not meta_value(parser, "theme-color"):
            warnings.append(f"theme-color missing in {rel}")
        if not parser.jsonld_blocks:
            warnings.append(f"JSON-LD missing in {rel}")
        for block in parser.jsonld_blocks:
            try:
                data = json.loads(block)
                nodes = data.get("@graph", []) if isinstance(data, dict) else []
                candidates = nodes or ([data] if isinstance(data, dict) else data if isinstance(data, list) else [])
                for node in candidates:
                    if isinstance(node, dict) and node.get("@type"):
                        types = node["@type"] if isinstance(node["@type"], list) else [node["@type"]]
                        jsonld_types.update(map(str, types))
            except Exception as exc:
                errors.append(f"Invalid JSON-LD in {rel}: {exc}")

        visible_text = " ".join(parser.text_parts)
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        minimum = content_minimum(rel)
        if len(visible_text) < minimum:
            errors.append(f"Thin content in {rel}: {len(visible_text)} < {minimum}")
        normalized = re.sub(r"\d+", "#", visible_text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if len(normalized) > 500:
            text_hashes[hashlib.sha256(normalized.encode()).hexdigest()].append(rel)

        for image in parser.images:
            if image.get("alt") is None:
                images_without_alt += 1
                errors.append(f"Image without alt in {rel}: {image.get('src')}")
            if image.get("width") and image.get("height"):
                pass
            elif image.get("src") and "logo" not in str(image.get("src")):
                warnings.append(f"Image dimensions missing in {rel}: {image.get('src')}")
        for item in parser.inputs:
            kind = str(item.get("type", "text")).lower()
            if kind in {"hidden", "submit", "button", "reset", "radio", "checkbox"}:
                continue
            ident = str(item.get("id", ""))
            if not item.get("aria-label") and not item.get("aria-labelledby") and (not ident or ident not in parser.labels_for):
                unlabeled_inputs += 1
                errors.append(f"Unlabeled input in {rel}: {ident or item.get('name')}")
        for text in parser.anchor_texts:
            if not text:
                empty_links += 1
                warnings.append(f"Empty link text in {rel}")
        for text, attrs in zip(parser.button_texts, parser.buttons):
            if not text and not attrs.get("aria-label") and not attrs.get("title"):
                errors.append(f"Unnamed button in {rel}")
        for script in parser.scripts:
            src = str(script.get("src", ""))
            if src and not script.get("defer") and not script.get("async") and str(script.get("type", "")).lower() != "module":
                blocking_scripts += 1
                warnings.append(f"Potential render-blocking script in {rel}: {src}")
        if any(re.search(r"(?:width|min-width)\s*:\s*(?:[7-9]\d{2}|\d{4,})px", style, re.I) for style in parser.inline_style_values):
            warnings.append(f"Potential fixed-width overflow in {rel}")

    for value, pages in titles.items():
        if value and len(pages) > 1:
            errors.append(f"Duplicate title across {len(pages)} pages: {value[:100]} -> {pages[:5]}")
    for value, pages in descriptions.items():
        if value and len(pages) > 1:
            errors.append(f"Duplicate description across {len(pages)} pages: {value[:100]} -> {pages[:5]}")
    for value, pages in canonicals.items():
        if value and len(pages) > 1:
            errors.append(f"Duplicate canonical across pages: {value} -> {pages[:5]}")
    for pages in text_hashes.values():
        if len(pages) > 1:
            errors.append(f"Exact duplicate substantial content across pages: {pages[:8]}")

    for page, parser in parsed.items():
        rel = page.relative_to(SITE).as_posix()
        for _, attr, value in parser.refs:
            target = local_target(page, value)
            parsed_url = urlparse(value)
            if target is None:
                if parsed_url.scheme in {"http", "https"}:
                    external_refs += 1
                    if parsed_url.scheme != "https":
                        warnings.append(f"Non-HTTPS external reference in {rel}: {value}")
                continue
            internal_refs += 1
            try:
                target.relative_to(SITE)
            except ValueError:
                errors.append(f"Reference escapes site root in {rel}: {value}")
                continue
            if not target.exists():
                errors.append(f"Broken internal {attr} in {rel}: {value}")

    for asset in SITE.rglob("*"):
        if not asset.is_file():
            continue
        size = asset.stat().st_size
        rel = asset.relative_to(SITE).as_posix()
        if size > 1_500_000:
            oversized_assets.append(f"{rel}:{size}")
            warnings.append(f"Large asset over 1.5MB: {rel} ({size})")
        if asset.suffix.lower() in {".json", ".webmanifest"}:
            try:
                json.loads(asset.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"Invalid JSON {rel}: {exc}")
        if asset.suffix.lower() == ".xml":
            try:
                ET.parse(asset)
            except Exception as exc:
                errors.append(f"Invalid XML {rel}: {exc}")

    robots = SITE / "robots.txt"
    if not robots.exists():
        errors.append("robots.txt missing")
    else:
        robot_text = robots.read_text(encoding="utf-8")
        if "Sitemap: " + BASE_URL + "sitemap.xml" not in robot_text:
            errors.append("robots.txt does not declare the canonical sitemap")
        if re.search(r"Disallow:\s*/\s*$", robot_text, re.M):
            errors.append("robots.txt blocks the entire site")

    manifest_path = SITE / "manifest.webmanifest"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("name", "short_name", "start_url", "scope", "display", "theme_color", "background_color"):
            if not manifest.get(key):
                errors.append(f"Manifest key missing: {key}")
        if not manifest.get("icons"):
            warnings.append("Manifest has no install icons")
    else:
        errors.append("manifest.webmanifest missing")

    sitemap_index = SITE / "sitemap.xml"
    sitemap_urls: list[str] = []
    sitemap_files: list[str] = []
    if not sitemap_index.exists():
        errors.append("sitemap.xml missing")
    else:
        try:
            root = ET.parse(sitemap_index).getroot()
            if not root.tag.endswith("sitemapindex"):
                errors.append("sitemap.xml is not a sitemap index")
            for loc in root.findall("{*}sitemap/{*}loc"):
                if not loc.text:
                    errors.append("Empty sitemap loc")
                    continue
                parsed_url = urlparse(loc.text)
                rel = unquote(parsed_url.path[len(BASE_PATH):]) if parsed_url.path.startswith(BASE_PATH) else ""
                child = SITE / rel
                sitemap_files.append(rel)
                if not child.exists():
                    errors.append(f"Missing child sitemap: {loc.text}")
                    continue
                child_root = ET.parse(child).getroot()
                for node in child_root.findall("{*}url/{*}loc"):
                    if node.text:
                        sitemap_urls.append(node.text)
        except Exception as exc:
            errors.append(f"Sitemap index error: {exc}")
    for alias_rel, target_rel in legacy_aliases.items():
        alias_url = BASE_URL + alias_rel.removesuffix("index.html")
        if alias_url in sitemap_urls:
            errors.append(f"Noindex legacy alias must not be in sitemaps: {alias_url}")
        if target_rel:
            target_url = BASE_URL + target_rel.removesuffix("index.html")
            if target_url not in sitemap_urls:
                errors.append(f"Legacy alias canonical target is missing from sitemaps: {target_url}")

    duplicate_urls = [url for url, count in Counter(sitemap_urls).items() if count > 1]
    if duplicate_urls:
        errors.append(f"Duplicate URLs across sitemaps: {duplicate_urls[:10]}")
    for url in sitemap_urls:
        parsed_url = urlparse(url)
        if parsed_url.netloc != BASE_HOST or not parsed_url.path.startswith(BASE_PATH):
            errors.append(f"Unexpected sitemap URL: {url}")
            continue
        rel = unquote(parsed_url.path[len(BASE_PATH):])
        target = SITE / rel
        if parsed_url.path.endswith("/") or target.is_dir() or not target.suffix:
            target = target / "index.html"
        if not target.exists():
            errors.append(f"Sitemap target missing: {url}")

    expected_counts = {"encyclopedia": 2003, "hubs": 201, "assessment-lab": 41, "cognitive-lab": 49, "tips": 21}
    for section, expected in expected_counts.items():
        actual = section_counts.get(section, 0)
        if actual != expected:
            errors.append(f"Unexpected HTML count for {section}: {actual} != {expected}")

    archive_path = SITE / "encyclopedia" / "all" / "index.html"
    archive_valid = False
    if not archive_path.is_file():
        errors.append("Encyclopedia detail archive is missing")
    else:
        archive_text = archive_path.read_text(encoding="utf-8")
        archive_valid = 'data-detail-archive-v2="true"' in archive_text
        if not archive_valid:
            errors.append("Encyclopedia detail archive marker is missing")

    report = {
        "version": 16,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "html_pages": len(html_files),
        "content_pages": len(content_files),
        "legacy_alias_count": len(legacy_aliases),
        "legacy_aliases": legacy_aliases,
        "legacy_alias_contract": "noindex-follow-immediate-internal-redirect-v333",
        "section_counts": dict(section_counts),
        "encyclopedia_detail_archive": archive_valid,
        "unique_titles": len([x for x in titles if x]),
        "unique_descriptions": len([x for x in descriptions if x]),
        "unique_canonicals": len([x for x in canonicals if x]),
        "jsonld_types": dict(jsonld_types),
        "internal_references": internal_refs,
        "external_references": external_refs,
        "sitemap_files": len(sitemap_files),
        "sitemap_urls": len(sitemap_urls),
        "blocking_scripts": blocking_scripts,
        "empty_links": empty_links,
        "unlabeled_inputs": unlabeled_inputs,
        "images_without_alt": images_without_alt,
        "oversized_assets": oversized_assets,
        "warning_count": len(warnings),
        "warnings": warnings[:1000],
        "error_count": len(errors),
        "errors": errors[:1000],
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "full-site-audit-v16.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("\n".join(errors[:100]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
