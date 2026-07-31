from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_HOST = "khaledaltheeb.github.io"
BASE_PATH = "/"
DIAGNOSTIC_CONTRACT_VERSION = 313
VERIFY_RE = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.I,
)
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
SPACE_RE = re.compile(r"\s+")


class QualityParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.visible_parts: list[str] = []
        self.meta_description = ""
        self.robots = ""
        self.canonical = ""
        self.og_title = ""
        self.og_description = ""
        self.twitter_card = ""
        self.json_ld_count = 0
        self.internal_links = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        self.stack.append(tag)
        if tag == "meta":
            name = data.get("name", "").strip().lower()
            prop = data.get("property", "").strip().lower()
            content = data.get("content", "").strip()
            if name == "description":
                self.meta_description = content
            elif name == "robots":
                self.robots = content
            elif prop == "og:title":
                self.og_title = content
            elif prop == "og:description":
                self.og_description = content
            elif name == "twitter:card":
                self.twitter_card = content
        elif tag == "link" and "canonical" in data.get("rel", "").lower().split():
            self.canonical = data.get("href", "").strip()
        elif tag == "script" and data.get("type", "").strip().lower() == "application/ld+json":
            self.json_ld_count += 1
        elif tag == "a":
            href = data.get("href", "").strip()
            if href and self._is_internal(href):
                self.internal_links += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        text = SPACE_RE.sub(" ", data).strip()
        if not text:
            return
        current = self.stack[-1] if self.stack else ""
        if current == "title":
            self.title_parts.append(text)
        if "h1" in self.stack:
            self.h1_parts.append(text)
        if not any(tag in self.stack for tag in ("script", "style", "noscript", "svg")):
            self.visible_parts.append(text)

    @staticmethod
    def _is_internal(href: str) -> bool:
        if href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
            return False
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https"}:
            return parsed.netloc == BASE_HOST and parsed.path.startswith(BASE_PATH)
        return not parsed.scheme and not href.startswith("//")

    @property
    def title(self) -> str:
        return SPACE_RE.sub(" ", " ".join(self.title_parts)).strip()

    @property
    def h1(self) -> str:
        return SPACE_RE.sub(" ", " ".join(self.h1_parts)).strip()

    @property
    def visible_text(self) -> str:
        return SPACE_RE.sub(" ", " ".join(self.visible_parts)).strip()


def normalized(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip().casefold()


def duplicate_groups(
    index: Counter[str], paths: dict[str, list[str]], display_values: dict[str, str]
) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for key, count in index.items():
        if not key or count <= 1:
            continue
        group_paths = sorted(set(paths.get(key, [])))
        groups.append(
            {
                "value": display_values.get(key, key),
                "normalized_value": key,
                "count": count,
                "paths": group_paths,
                "path_count": len(group_paths),
            }
        )
    return sorted(groups, key=lambda item: (-int(item["count"]), str(item["value"])))


def main() -> int:
    if not SITE.exists():
        raise SystemExit(f"Site directory does not exist: {SITE}")

    pages: list[dict[str, object]] = []
    critical_errors: list[str] = []
    warnings: list[str] = []
    title_index: Counter[str] = Counter()
    description_index: Counter[str] = Counter()
    title_paths: defaultdict[str, list[str]] = defaultdict(list)
    description_paths: defaultdict[str, list[str]] = defaultdict(list)
    title_values: dict[str, str] = {}
    description_values: dict[str, str] = {}

    html_files = sorted(SITE.rglob("*.html"))
    verification_files_skipped = 0
    noindex_pages_skipped = 0
    for path in html_files:
        raw = path.read_text(encoding="utf-8", errors="strict")
        if path.parent == SITE and VERIFY_RE.match(raw.strip()):
            verification_files_skipped += 1
            continue

        rel = path.relative_to(SITE).as_posix()
        parser = QualityParser()
        try:
            parser.feed(raw)
        except Exception as exc:
            critical_errors.append(f"Unreadable HTML {rel}: {exc}")
            continue
        if "noindex" in {
            token.strip().lower() for token in parser.robots.split(",")
        }:
            noindex_pages_skipped += 1
            continue

        words = WORD_RE.findall(parser.visible_text)
        word_count = len(words)
        title = parser.title
        description = parser.meta_description
        h1 = parser.h1
        canonical = parser.canonical

        for field, value in (
            ("title", title),
            ("meta description", description),
            ("canonical", canonical),
            ("h1", h1),
        ):
            if not value:
                critical_errors.append(f"Empty {field} in {rel}")

        if word_count < 8:
            critical_errors.append(f"Effectively empty page {rel}: {word_count} visible words")
        elif word_count < 120:
            warnings.append(f"Thin page candidate {rel}: {word_count} visible words")

        if title:
            key = normalized(title)
            title_index[key] += 1
            title_paths[key].append(rel)
            title_values.setdefault(key, title)
        if description:
            key = normalized(description)
            description_index[key] += 1
            description_paths[key].append(rel)
            description_values.setdefault(key, description)

        missing_social: list[str] = []
        if not parser.og_title:
            missing_social.append("og:title")
        if not parser.og_description:
            missing_social.append("og:description")
        if not parser.twitter_card:
            missing_social.append("twitter:card")
        if missing_social:
            warnings.append(f"Missing social metadata in {rel}: {', '.join(missing_social)}")
        if parser.json_ld_count == 0:
            warnings.append(f"Missing JSON-LD in {rel}")
        if parser.internal_links < 2:
            warnings.append(f"Low internal-link density in {rel}: {parser.internal_links}")

        pages.append(
            {
                "path": rel,
                "word_count": word_count,
                "title": title,
                "meta_description_chars": len(description),
                "h1": h1,
                "canonical": canonical,
                "open_graph_complete": bool(parser.og_title and parser.og_description),
                "twitter_card": bool(parser.twitter_card),
                "json_ld_blocks": parser.json_ld_count,
                "internal_links": parser.internal_links,
            }
        )

    duplicate_titles = duplicate_groups(title_index, title_paths, title_values)
    duplicate_descriptions = duplicate_groups(
        description_index, description_paths, description_values
    )
    for group in duplicate_titles[:100]:
        joined_paths = ", ".join(str(path) for path in group["paths"])
        warnings.append(
            f"Duplicate title used {group['count']} times: {str(group['value'])[:120]} | paths: {joined_paths}"
        )
    for group in duplicate_descriptions[:100]:
        joined_paths = ", ".join(str(path) for path in group["paths"])
        warnings.append(
            "Duplicate meta description used "
            f"{group['count']} times: {str(group['value'])[:160]} | paths: {joined_paths}"
        )

    word_counts = [int(page["word_count"]) for page in pages]
    report = {
        "version": "32-content-quality",
        "diagnostic_contract_version": DIAGNOSTIC_CONTRACT_VERSION,
        "pages_scanned": len(pages),
        "html_files_seen": len(html_files),
        "verification_files_skipped": verification_files_skipped,
        "noindex_pages_skipped": noindex_pages_skipped,
        "critical_error_count": len(critical_errors),
        "warning_count": len(warnings),
        "effectively_empty_pages": sum(1 for count in word_counts if count < 8),
        "thin_page_candidates": sum(1 for count in word_counts if 8 <= count < 120),
        "pages_with_complete_open_graph": sum(
            1 for page in pages if page["open_graph_complete"]
        ),
        "pages_with_twitter_card": sum(1 for page in pages if page["twitter_card"]),
        "pages_with_json_ld": sum(1 for page in pages if int(page["json_ld_blocks"]) > 0),
        "pages_with_two_or_more_internal_links": sum(
            1 for page in pages if int(page["internal_links"]) >= 2
        ),
        "duplicate_title_values": len(duplicate_titles),
        "duplicate_description_values": len(duplicate_descriptions),
        "duplicate_title_groups": duplicate_titles[:100],
        "duplicate_description_groups": duplicate_descriptions[:100],
        "minimum_visible_words": min(word_counts) if word_counts else 0,
        "median_visible_words": sorted(word_counts)[len(word_counts) // 2] if word_counts else 0,
        "critical_errors": critical_errors[:500],
        "warnings": warnings[:1000],
        "weakest_pages": sorted(pages, key=lambda page: int(page["word_count"]))[:100],
    }

    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    output = api / "content-quality-v32.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if critical_errors:
        raise SystemExit("\n".join(critical_errors[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
