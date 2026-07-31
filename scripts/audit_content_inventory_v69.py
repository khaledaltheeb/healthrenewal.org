from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://healthrenewal.org/"
BASE_HOST = "khaledaltheeb.github.io"
BASE_PATH = "/"
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
SPACE_RE = re.compile(r"\s+")
DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
SOCIAL_HOSTS = {
    "youtube.com", "www.youtube.com", "youtu.be", "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com", "x.com", "twitter.com", "www.twitter.com",
    "linkedin.com", "www.linkedin.com", "t.me", "telegram.me",
}
UTILITY_PREFIXES = ("404", "search", "offline", "privacy", "terms", "contact")


def normalize_text(value: str) -> str:
    value = DIACRITICS_RE.sub("", value).replace("ـ", "")
    return SPACE_RE.sub(" ", value).strip().casefold()


def tokenize(value: str) -> list[str]:
    return [normalize_text(token) for token in WORD_RE.findall(value) if normalize_text(token)]


def site_path(url: str, current_path: str | None = None) -> str | None:
    if not url:
        return None
    base = BASE_URL
    if current_path:
        page_url = urljoin(BASE_URL, current_path)
        base = page_url[:-len("index.html")] if current_path.endswith("index.html") else page_url
    parsed = urlparse(urljoin(base, url))
    if parsed.scheme not in {"http", "https"} or parsed.netloc != BASE_HOST:
        return None
    if not parsed.path.startswith(BASE_PATH):
        return None
    path = parsed.path[len(BASE_PATH):]
    if not path or path.endswith("/"):
        return f"{path}index.html"
    if path.endswith(".html"):
        return path
    return f"{path.rstrip('/')}/index.html"


def external_host(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    host = parsed.netloc.casefold()
    return None if host == BASE_HOST else host


def shingles(tokens: list[str], size: int = 5) -> set[str]:
    if len(tokens) < size:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left and right else 0.0


@dataclass
class Page:
    path: str
    title: str = ""
    description: str = ""
    canonical: str = ""
    robots: str = ""
    headings: dict[str, list[str]] = field(default_factory=lambda: {"h1": [], "h2": [], "h3": []})
    visible_text: str = ""
    json_ld_count: int = 0
    internal_targets: set[str] = field(default_factory=set)
    external_hosts: set[str] = field(default_factory=set)
    inbound_links: int = 0
    exact_duplicate_group: str | None = None
    exact_duplicate_of: str | None = None
    near_duplicate_of: str | None = None
    near_duplicate_score: float | None = None
    decision: str = "KEEP"
    reasons: list[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(tokenize(self.visible_text))

    @property
    def content_shingles(self) -> set[str]:
        return shingles(tokenize(self.visible_text))

    @property
    def text_hash(self) -> str:
        return hashlib.sha256(normalize_text(self.visible_text).encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "decision": self.decision,
            "reasons": self.reasons,
            "word_count": self.word_count,
            "title": self.title,
            "meta_description_chars": len(self.description),
            "h1_count": len(self.headings["h1"]),
            "h2_count": len(self.headings["h2"]),
            "h3_count": len(self.headings["h3"]),
            "canonical": self.canonical,
            "robots": self.robots,
            "json_ld_blocks": self.json_ld_count,
            "internal_links_out": len(self.internal_targets),
            "internal_links_in": self.inbound_links,
            "source_count": len(self.external_hosts),
            "source_hosts": sorted(self.external_hosts),
            "exact_duplicate_group": self.exact_duplicate_group,
            "exact_duplicate_of": self.exact_duplicate_of,
            "near_duplicate_of": self.near_duplicate_of,
            "near_duplicate_score": self.near_duplicate_score,
        }


class Parser(HTMLParser):
    def __init__(self, path: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page(path=path)
        self.stack: list[str] = []
        self.visible_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        data = {key.casefold(): (value or "") for key, value in attrs}
        self.stack.append(tag)
        if tag == "meta":
            name = data.get("name", "").strip().casefold()
            content = data.get("content", "").strip()
            if name == "description":
                self.page.description = content
            elif name == "robots":
                self.page.robots = content.casefold()
        elif tag == "link" and "canonical" in data.get("rel", "").casefold().split():
            self.page.canonical = data.get("href", "").strip()
        elif tag == "script" and data.get("type", "").strip().casefold() == "application/ld+json":
            self.page.json_ld_count += 1
        elif tag == "a":
            href = data.get("href", "").strip()
            target = site_path(href, self.page.path)
            if target:
                self.page.internal_targets.add(target)
            else:
                host = external_host(href)
                if host and host not in SOCIAL_HOSTS:
                    self.page.external_hosts.add(host)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        text = SPACE_RE.sub(" ", data).strip()
        if not text:
            return
        if "title" in self.stack:
            self.page.title = SPACE_RE.sub(" ", f"{self.page.title} {text}").strip()
        for heading in ("h1", "h2", "h3"):
            if heading in self.stack:
                self.page.headings[heading].append(text)
        if not any(tag in self.stack for tag in ("script", "style", "noscript", "svg")):
            self.visible_parts.append(text)

    def finish(self) -> Page:
        self.page.visible_text = SPACE_RE.sub(" ", " ".join(self.visible_parts)).strip()
        return self.page


def parse_page(path: Path, site: Path) -> Page:
    parser = Parser(path.relative_to(site).as_posix())
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    parser.close()
    return parser.finish()


def mark_duplicates(pages: list[Page]) -> None:
    exact: defaultdict[str, list[Page]] = defaultdict(list)
    for page in pages:
        if page.word_count >= 30:
            exact[page.text_hash].append(page)
    for digest, members in exact.items():
        if len(members) > 1:
            group = f"exact-{digest[:12]}"
            primary = sorted(
                members,
                key=lambda page: (-page.word_count, -len(page.external_hosts), -page.inbound_links, page.path),
            )[0]
            for member in members:
                member.exact_duplicate_group = group
                if member.path != primary.path:
                    member.exact_duplicate_of = primary.path

    eligible = [page for page in pages if page.word_count >= 80 and not page.exact_duplicate_group]
    title_buckets: defaultdict[str, list[Page]] = defaultdict(list)
    for page in eligible:
        tokens = tokenize(page.title)
        for token in set(tokens[:4]):
            title_buckets[token].append(page)
    candidates: set[tuple[str, str]] = set()
    by_path = {page.path: page for page in eligible}
    for members in title_buckets.values():
        if len(members) > 50:
            continue
        paths = sorted({page.path for page in members})
        for index, left in enumerate(paths):
            for right in paths[index + 1:]:
                candidates.add((left, right))
    shingle_cache = {page.path: page.content_shingles for page in eligible}
    for left_path, right_path in candidates:
        score = jaccard(shingle_cache[left_path], shingle_cache[right_path])
        if score < 0.82:
            continue
        left, right = by_path[left_path], by_path[right_path]
        primary, duplicate = sorted(
            (left, right),
            key=lambda page: (-page.word_count, -len(page.external_hosts), -page.inbound_links, page.path),
        )
        if duplicate.near_duplicate_score is None or score > duplicate.near_duplicate_score:
            duplicate.near_duplicate_of = primary.path
            duplicate.near_duplicate_score = round(score, 4)


def classify(page: Page) -> None:
    reasons: list[str] = []
    utility = page.path.startswith(UTILITY_PREFIXES) or "/search/" in page.path
    if not page.title:
        reasons.append("missing_title")
    if not page.headings["h1"]:
        reasons.append("missing_h1")
    if len(page.headings["h1"]) > 1:
        reasons.append("multiple_h1")
    if not page.description:
        reasons.append("missing_meta_description")
    if not page.canonical:
        reasons.append("missing_canonical")
    if page.json_ld_count == 0:
        reasons.append("missing_json_ld")
    if page.inbound_links == 0 and page.path != "index.html":
        reasons.append("orphan_page")
    if len(page.internal_targets) < 2 and not utility:
        reasons.append("low_internal_links")
    if not page.external_hosts and page.word_count >= 180 and not utility:
        reasons.append("no_external_sources")
    if page.word_count < 8:
        reasons.append("effectively_empty")
    elif page.word_count < 120 and not utility:
        reasons.append("thin_content")
    if page.exact_duplicate_of:
        reasons.append("exact_duplicate")
    if page.near_duplicate_of:
        reasons.append("near_duplicate")
    if page.canonical and site_path(page.canonical) != page.path:
        reasons.append("canonical_points_elsewhere")
    if "noindex" in page.robots:
        reasons.append("already_noindex")

    if "effectively_empty" in reasons and page.inbound_links == 0 and page.path != "index.html":
        page.decision = "DELETE"
    elif page.exact_duplicate_of or page.near_duplicate_of:
        page.decision = "MERGE"
    elif "already_noindex" in reasons or (utility and page.word_count < 120):
        page.decision = "NOINDEX"
    elif reasons:
        page.decision = "IMPROVE"
    else:
        page.decision = "KEEP"
    page.reasons = reasons


def build_report(site: Path) -> tuple[dict[str, object], list[Page]]:
    pages = [parse_page(path, site) for path in sorted(site.rglob("*.html"))]
    known = {page.path for page in pages}
    inbound: Counter[str] = Counter()
    for page in pages:
        page.internal_targets = {target for target in page.internal_targets if target in known}
        inbound.update(page.internal_targets)
    for page in pages:
        page.inbound_links = inbound[page.path]
    mark_duplicates(pages)
    for page in pages:
        classify(page)

    decisions = Counter(page.decision for page in pages)
    reasons = Counter(reason for page in pages for reason in page.reasons)
    ordered = sorted(
        pages,
        key=lambda page: ({"DELETE": 0, "MERGE": 1, "NOINDEX": 2, "IMPROVE": 3, "KEEP": 4}[page.decision], page.word_count, page.path),
    )
    report = {
        "version": "69-content-inventory",
        "pages_scanned": len(pages),
        "decision_counts": dict(sorted(decisions.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "orphan_pages": reasons["orphan_page"],
        "thin_pages": reasons["thin_content"],
        "exact_duplicate_pages": reasons["exact_duplicate"],
        "near_duplicate_pages": reasons["near_duplicate"],
        "pages_without_sources": reasons["no_external_sources"],
        "policy": {
            "advisory_only": True,
            "automatic_delete_or_noindex": False,
            "required_human_review_for": ["DELETE", "MERGE", "NOINDEX"],
        },
        "pages": [page.as_dict() for page in ordered],
    }
    return report, pages


def write_outputs(site: Path, report: dict[str, object], pages: list[Page]) -> None:
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "content-inventory-v69.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fields = [
        "path", "decision", "reasons", "word_count", "title", "meta_description_chars",
        "h1_count", "h2_count", "h3_count", "canonical", "robots", "json_ld_blocks",
        "internal_links_out", "internal_links_in", "source_count", "source_hosts",
        "exact_duplicate_group", "exact_duplicate_of", "near_duplicate_of", "near_duplicate_score",
    ]
    with (api / "content-inventory-v69.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for page in sorted(pages, key=lambda item: item.path):
            row = page.as_dict()
            row["reasons"] = "|".join(page.reasons)
            row["source_hosts"] = "|".join(sorted(page.external_hosts))
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> int:
    if not SITE.is_dir():
        raise SystemExit(f"Site directory does not exist: {SITE}")
    report, pages = build_report(SITE)
    if not pages:
        raise SystemExit("No HTML pages found")
    write_outputs(SITE, report, pages)
    print(json.dumps({key: value for key, value in report.items() if key != "pages"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
