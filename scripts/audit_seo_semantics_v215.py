from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
TAXONOMY_PATH = ROOT / "content" / "seo" / "keyword-taxonomy-v215.json"
REPORT_PATH = ROOT / ".build" / "reports" / "seo-semantic-audit-v215.json"
WORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
SPACE_RE = re.compile(r"\s+")


class SeoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.visible_parts: list[str] = []
        self.headings: Counter[str] = Counter()
        self.description = ""
        self.canonical = ""
        self.lang = ""
        self.direction = ""
        self.og_title = ""
        self.og_description = ""
        self.twitter_card = ""
        self.json_ld = 0
        self.internal_links = 0
        self.meta_keywords = ""
        self._stack: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        self._stack.append(tag)
        if tag in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1
        if tag == "html":
            self.lang = attributes.get("lang", "")
            self.direction = attributes.get("dir", "")
        elif tag == "meta":
            name = attributes.get("name", "").lower()
            prop = attributes.get("property", "").lower()
            content = attributes.get("content", "").strip()
            if name == "description":
                self.description = content
            elif name == "twitter:card":
                self.twitter_card = content
            elif name == "keywords":
                self.meta_keywords = content
            elif prop == "og:title":
                self.og_title = content
            elif prop == "og:description":
                self.og_description = content
        elif tag == "link" and attributes.get("rel", "").lower() == "canonical":
            self.canonical = attributes.get("href", "").strip()
        elif (
            tag == "script"
            and attributes.get("type", "").lower() == "application/ld+json"
        ):
            self.json_ld += 1
        elif tag == "a":
            href = attributes.get("href", "").strip()
            if href and not href.startswith(
                ("http://", "https://", "mailto:", "tel:", "#", "javascript:")
            ):
                self.internal_links += 1
        if tag in {"h1", "h2", "h3"}:
            self.headings[tag] += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        text = SPACE_RE.sub(" ", data).strip()
        if not text:
            return
        if self._stack and self._stack[-1] == "title":
            self.title_parts.append(text)
        if self._hidden_depth == 0:
            self.visible_parts.append(text)

    @property
    def title(self) -> str:
        return SPACE_RE.sub(" ", " ".join(self.title_parts)).strip()

    @property
    def visible_text(self) -> str:
        return SPACE_RE.sub(" ", " ".join(self.visible_parts)).strip()


def load_taxonomy(path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 215:
        raise ValueError("SEO taxonomy schema mismatch")
    return data


def infer_clusters(text: str, taxonomy: dict[str, Any]) -> list[str]:
    normalized = text.casefold()
    matches: list[tuple[int, str]] = []
    for cluster in taxonomy.get("clusters") or []:
        primary = list(cluster.get("primary_terms") or [])
        terms = primary + list(cluster.get("synonyms") or [])
        score = sum(
            2 if term in primary else 1
            for term in terms
            if str(term).casefold() in normalized
        )
        if score:
            matches.append((score, str(cluster.get("id"))))
    return [
        cluster_id
        for _, cluster_id in sorted(matches, key=lambda item: (-item[0], item[1]))[:3]
    ]


def audit_page(
    path: Path,
    site: Path,
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    parser = SeoParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    visible = parser.visible_text
    words = WORD_RE.findall(visible)
    relative = path.relative_to(site).as_posix()
    policy = taxonomy["policy"]
    title_min, title_max = policy["preferred_title_characters"]
    description_min, description_max = policy["preferred_description_characters"]

    warnings: list[str] = []
    if not (title_min <= len(parser.title) <= title_max):
        warnings.append("title_length")
    if not (description_min <= len(parser.description) <= description_max):
        warnings.append("description_length")
    if parser.headings["h1"] != 1:
        warnings.append("h1_count")
    if not parser.canonical:
        warnings.append("missing_canonical")
    if parser.lang != "ar" or parser.direction != "rtl":
        warnings.append("language_direction")
    if not parser.og_title or not parser.og_description:
        warnings.append("open_graph")
    if not parser.twitter_card:
        warnings.append("twitter_card")
    if parser.json_ld < 1:
        warnings.append("json_ld")
    if len(words) < policy["minimum_visible_words"]:
        warnings.append("thin_visible_content")
    if parser.internal_links < policy["minimum_internal_links"]:
        warnings.append("few_internal_links")

    keyword_count = len(
        [part for part in parser.meta_keywords.split(",") if part.strip()]
    )
    if keyword_count > int(policy.get("maximum_meta_keywords", 15)):
        warnings.append("meta_keywords_stuffing")

    critical: list[str] = []
    if relative in {"index.html", "developers/index.html"}:
        for phrase in taxonomy.get("forbidden_public_phrases") or []:
            if phrase in visible:
                critical.append(f"public_internal_language:{phrase}")
        required = [
            parser.title,
            parser.description,
            parser.canonical,
            parser.og_title,
            parser.og_description,
        ]
        if policy.get("meta_keywords_required_on_core_pages") and not parser.meta_keywords:
            critical.append("missing_controlled_meta_keywords")
        if keyword_count > int(policy.get("maximum_meta_keywords", 15)):
            critical.append("meta_keywords_limit_exceeded")
        if not all(required) or parser.headings["h1"] != 1 or parser.json_ld < 1:
            critical.append("critical_metadata_contract")

    return {
        "path": relative,
        "title": parser.title,
        "description": parser.description,
        "word_count": len(words),
        "internal_links": parser.internal_links,
        "h1": parser.headings["h1"],
        "h2": parser.headings["h2"],
        "h3": parser.headings["h3"],
        "clusters": infer_clusters(
            " ".join([parser.title, parser.description, visible[:12000]]),
            taxonomy,
        ),
        "warnings": warnings,
        "critical": critical,
    }


def audit_site(
    site: Path = SITE,
    report_path: Path = REPORT_PATH,
    taxonomy_path: Path = TAXONOMY_PATH,
) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")
    taxonomy = load_taxonomy(taxonomy_path)
    pages = [
        audit_page(path, site, taxonomy)
        for path in sorted(site.rglob("*.html"))
    ]
    if not pages:
        raise SystemExit("No HTML pages found")

    title_paths: defaultdict[str, list[str]] = defaultdict(list)
    description_paths: defaultdict[str, list[str]] = defaultdict(list)
    for page in pages:
        if page["title"]:
            title_paths[page["title"]].append(page["path"])
        if page["description"]:
            description_paths[page["description"]].append(page["path"])

    warning_counts = Counter(
        warning
        for page in pages
        for warning in page["warnings"]
    )
    critical = [
        {"path": page["path"], "errors": page["critical"]}
        for page in pages
        if page["critical"]
    ]
    cluster_counts = Counter(
        cluster
        for page in pages
        for cluster in page["clusters"]
    )
    report = {
        "schema_version": 215,
        "pages": len(pages),
        "critical_error_count": len(critical),
        "critical_errors": critical,
        "warning_counts": dict(sorted(warning_counts.items())),
        "duplicate_title_groups": sum(
            1 for value in title_paths.values() if len(value) > 1
        ),
        "duplicate_description_groups": sum(
            1 for value in description_paths.values() if len(value) > 1
        ),
        "cluster_coverage": dict(sorted(cluster_counts.items())),
        "meta_keywords_policy": (
            "controlled-compatibility-tag-semantic-seo-primary"
        ),
        "pages_without_clusters": sum(
            1 for page in pages if not page["clusters"]
        ),
        "sample_warnings": [page for page in pages if page["warnings"]][:100],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    report = audit_site()
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "pages",
                    "critical_error_count",
                    "warning_counts",
                    "cluster_coverage",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if report["critical_error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
