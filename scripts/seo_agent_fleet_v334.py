#!/usr/bin/env python3
"""Deterministic eight-agent SEO and AI-discovery audit for a static website.

The scanner uses only Python's standard library so it can run in GitHub Actions,
local development, and deployment pipelines without downloading dependencies.
It never changes content unless --write-discovery-files is explicitly supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence
from urllib.parse import unquote, urljoin, urlparse, urlunparse
from xml.etree import ElementTree as ET

VERSION = 334
DEFAULT_BASE_URL = "https://healthrenewal.org/"
REPORT_JSON = f"seo-agent-report-v{VERSION}.json"
REPORT_MD = f"seo-agent-report-v{VERSION}.md"

EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "scripts",
    "tests",
    "test-fixtures",
    "indexing-fixture",
    "seo-audit",
}
EXCLUDED_FILES = {"404.html"}
VERIFICATION_RE = re.compile(r"^(google|bing|yandex|baidu)[a-z0-9_-]*\.html$", re.I)
WHITESPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")

SEARCH_AND_ANSWER_BOTS = (
    "Googlebot",
    "Bingbot",
    "Applebot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "Perplexity-User",
    "Claude-SearchBot",
    "Claude-User",
    "DuckDuckBot",
)
TRAINING_OR_MODEL_BOTS = (
    "GPTBot",
    "Google-Extended",
    "Applebot-Extended",
    "ClaudeBot",
    "CCBot",
    "Bytespider",
    "Meta-ExternalAgent",
    "Amazonbot",
)

SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2, "critical": 3}


def compact_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value or "").strip()


def strip_fragment_query(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {value!r}")
    path = parsed.path or "/"
    if not path.endswith("/"):
        path += "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def canonicalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunparse((scheme, host, path, "", "", ""))


def og_locale(locale: str) -> str:
    """Convert BCP-47 language tag to OpenGraph locale without uppercasing language."""
    parts = locale.replace("_", "-").split("-")
    if len(parts) == 1:
        return parts[0].lower()
    return f"{parts[0].lower()}_{parts[1].upper()}"


def safe_json_for_html(value: Any) -> str:
    """Serialize JSON-LD safely for embedding in a script element."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


@dataclass(slots=True)
class Finding:
    agent: str
    code: str
    severity: str
    message: str
    path: str = ""
    evidence: str = ""
    remediation: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_RANK:
            raise ValueError(f"Unsupported severity: {self.severity}")


@dataclass(slots=True)
class LinkRef:
    href: str
    rel: tuple[str, ...] = ()
    text: str = ""


@dataclass(slots=True)
class ImageRef:
    src: str
    alt: str | None
    width: str | None
    height: str | None
    loading: str | None


@dataclass(slots=True)
class Page:
    path: Path
    relative_path: str
    expected_url: str
    lang: str = ""
    direction: str = ""
    title: str = ""
    descriptions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    robots: list[str] = field(default_factory=list)
    googlebot: list[str] = field(default_factory=list)
    canonicals: list[str] = field(default_factory=list)
    hreflangs: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    h1_texts: list[str] = field(default_factory=list)
    links: list[LinkRef] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    json_ld: list[Any] = field(default_factory=list)
    json_ld_errors: list[str] = field(default_factory=list)
    og: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    twitter: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    visible_text: str = ""

    @property
    def combined_robots(self) -> str:
        return ",".join(self.robots + self.googlebot).lower()

    @property
    def noindex(self) -> bool:
        return bool(re.search(r"(?:^|[,\s])noindex(?:$|[,\s])", self.combined_robots))

    @property
    def indexable(self) -> bool:
        return not self.noindex

    @property
    def word_count(self) -> int:
        return len(WORD_RE.findall(self.visible_text))

    @property
    def is_arabic(self) -> bool:
        return self.lang.lower().startswith("ar") or bool(ARABIC_RE.search(self.visible_text[:1000]))


class PageParser(HTMLParser):
    SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.direction = ""
        self.title_parts: list[str] = []
        self._in_title = False
        self._h1_depth = 0
        self._h1_parts: list[str] = []
        self.h1_texts: list[str] = []
        self._anchor_depth = 0
        self._anchor_text: list[str] = []
        self._current_anchor: LinkRef | None = None
        self._skip_depth = 0
        self._json_ld_depth = 0
        self._json_ld_parts: list[str] = []
        self.descriptions: list[str] = []
        self.keywords: list[str] = []
        self.robots: list[str] = []
        self.googlebot: list[str] = []
        self.canonicals: list[str] = []
        self.hreflangs: dict[str, list[str]] = defaultdict(list)
        self.links: list[LinkRef] = []
        self.images: list[ImageRef] = []
        self.json_ld: list[Any] = []
        self.json_ld_errors: list[str] = []
        self.og: dict[str, list[str]] = defaultdict(list)
        self.twitter: dict[str, list[str]] = defaultdict(list)
        self.text_parts: list[str] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {str(k).lower(): (v or "") for k, v in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        values = self._attrs(attrs)
        if name == "html":
            self.lang = values.get("lang", "").strip()
            self.direction = values.get("dir", "").strip().lower()
        elif name == "title":
            self._in_title = True
        elif name == "h1":
            self._h1_depth += 1
            if self._h1_depth == 1:
                self._h1_parts = []
        elif name == "meta":
            meta_name = values.get("name", "").lower()
            prop = values.get("property", "").lower()
            content = values.get("content", "").strip()
            if meta_name == "description":
                self.descriptions.append(content)
            elif meta_name == "keywords":
                self.keywords.append(content)
            elif meta_name == "robots":
                self.robots.append(content)
            elif meta_name == "googlebot":
                self.googlebot.append(content)
            elif meta_name.startswith("twitter:"):
                self.twitter[meta_name].append(content)
            if prop.startswith("og:"):
                self.og[prop].append(content)
        elif name == "link":
            rel = tuple(token.lower() for token in values.get("rel", "").split() if token)
            href = values.get("href", "").strip()
            if "canonical" in rel:
                self.canonicals.append(href)
            if "alternate" in rel and values.get("hreflang"):
                self.hreflangs[values["hreflang"].strip().lower()].append(href)
        elif name == "a":
            rel = tuple(token.lower() for token in values.get("rel", "").split() if token)
            self._current_anchor = LinkRef(values.get("href", "").strip(), rel, "")
            self._anchor_depth += 1
            self._anchor_text = []
        elif name == "img":
            self.images.append(
                ImageRef(
                    src=values.get("src", "").strip(),
                    alt=values.get("alt") if "alt" in values else None,
                    width=values.get("width") or None,
                    height=values.get("height") or None,
                    loading=values.get("loading") or None,
                )
            )
        elif name == "script" and values.get("type", "").lower() == "application/ld+json":
            self._json_ld_depth += 1
            self._json_ld_parts = []

        if name in self.SKIP_TEXT_TAGS:
            self._skip_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() in self.SKIP_TEXT_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name == "title":
            self._in_title = False
        elif name == "h1" and self._h1_depth:
            self._h1_depth -= 1
            if self._h1_depth == 0:
                self.h1_texts.append(compact_text(" ".join(self._h1_parts)))
        elif name == "a" and self._anchor_depth:
            self._anchor_depth -= 1
            if self._anchor_depth == 0 and self._current_anchor is not None:
                self._current_anchor.text = compact_text(" ".join(self._anchor_text))
                self.links.append(self._current_anchor)
                self._current_anchor = None
                self._anchor_text = []
        elif name == "script" and self._json_ld_depth:
            raw = "".join(self._json_ld_parts).strip()
            self._json_ld_depth -= 1
            if raw:
                try:
                    self.json_ld.append(json.loads(raw))
                except json.JSONDecodeError as exc:
                    self.json_ld_errors.append(f"line {exc.lineno}, column {exc.colno}: {exc.msg}")
            self._json_ld_parts = []

        if name in self.SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._json_ld_depth:
            self._json_ld_parts.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._h1_depth:
            self._h1_parts.append(data)
        if self._anchor_depth:
            self._anchor_text.append(data)
        if self._skip_depth == 0:
            cleaned = compact_text(data)
            if cleaned:
                self.text_parts.append(cleaned)

    @property
    def title(self) -> str:
        return compact_text(" ".join(self.title_parts))

    @property
    def visible_text(self) -> str:
        return compact_text(" ".join(self.text_parts))


@dataclass(slots=True)
class RobotsGroup:
    agents: list[str] = field(default_factory=list)
    rules: list[tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class RobotsPolicy:
    groups: list[RobotsGroup] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def groups_for(self, user_agent: str) -> list[RobotsGroup]:
        needle = user_agent.lower()
        exact = [g for g in self.groups if any(a.lower() == needle for a in g.agents)]
        if exact:
            return exact
        return [g for g in self.groups if any(a == "*" for a in g.agents)]

    def root_allowed(self, user_agent: str) -> bool:
        groups = self.groups_for(user_agent)
        if not groups:
            return True
        matched: list[tuple[int, bool]] = []
        for group in groups:
            for directive, value in group.rules:
                if value in {"", "/"}:
                    if value == "/":
                        matched.append((1, directive == "allow"))
                    elif directive == "allow":
                        matched.append((0, True))
        if not matched:
            return True
        max_len = max(length for length, _ in matched)
        decisions = [allowed for length, allowed in matched if length == max_len]
        return any(decisions)


def parse_robots(text: str) -> RobotsPolicy:
    policy = RobotsPolicy()
    current: RobotsGroup | None = None
    saw_rule = False
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            policy.errors.append(f"line {line_no}: missing ':'")
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if current is None or saw_rule:
                current = RobotsGroup()
                policy.groups.append(current)
                saw_rule = False
            if not value:
                policy.errors.append(f"line {line_no}: empty user-agent")
            else:
                current.agents.append(value)
        elif key in {"allow", "disallow"}:
            if current is None or not current.agents:
                policy.errors.append(f"line {line_no}: {key} before user-agent")
                continue
            current.rules.append((key, value))
            saw_rule = True
        elif key == "sitemap":
            policy.sitemaps.append(value)
    return policy


def is_publishable_html(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_DIRS or part.startswith(".") for part in relative.parts[:-1]):
        return False
    if path.name in EXCLUDED_FILES or VERIFICATION_RE.match(path.name):
        return False
    return True


def expected_url_for(relative_path: str, base_url: str) -> str:
    posix = PurePosixPath(relative_path)
    if posix.name == "index.html":
        parent = str(posix.parent)
        suffix = "" if parent == "." else parent.rstrip("/") + "/"
    else:
        suffix = str(posix)
    return canonicalize_url(urljoin(base_url, suffix))


def parse_page(path: Path, root: Path, base_url: str) -> Page:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    relative = path.relative_to(root).as_posix()
    return Page(
        path=path,
        relative_path=relative,
        expected_url=expected_url_for(relative, base_url),
        lang=parser.lang,
        direction=parser.direction,
        title=parser.title,
        descriptions=parser.descriptions,
        keywords=parser.keywords,
        robots=parser.robots,
        googlebot=parser.googlebot,
        canonicals=parser.canonicals,
        hreflangs=parser.hreflangs,
        h1_texts=parser.h1_texts,
        links=parser.links,
        images=parser.images,
        json_ld=parser.json_ld,
        json_ld_errors=parser.json_ld_errors,
        og=parser.og,
        twitter=parser.twitter,
        visible_text=parser.visible_text,
    )


@dataclass(slots=True)
class SiteContext:
    root: Path
    base_url: str
    pages: list[Page]
    page_by_url: dict[str, Page]
    page_by_path: dict[str, Page]
    robots_text: str
    robots: RobotsPolicy
    llms_text: str

    @classmethod
    def load(cls, root: Path, base_url: str) -> "SiteContext":
        root = root.resolve()
        base_url = normalize_base_url(base_url)
        pages = [
            parse_page(path, root, base_url)
            for path in sorted(root.rglob("*.html"))
            if is_publishable_html(path, root)
        ]
        page_by_url = {canonicalize_url(page.expected_url): page for page in pages}
        page_by_path = {page.relative_path: page for page in pages}
        robots_path = root / "robots.txt"
        robots_text = robots_path.read_text(encoding="utf-8") if robots_path.exists() else ""
        llms_path = root / "llms.txt"
        llms_text = llms_path.read_text(encoding="utf-8") if llms_path.exists() else ""
        return cls(
            root=root,
            base_url=base_url,
            pages=pages,
            page_by_url=page_by_url,
            page_by_path=page_by_path,
            robots_text=robots_text,
            robots=parse_robots(robots_text) if robots_text else RobotsPolicy(),
            llms_text=llms_text,
        )


class Agent:
    name = "Agent"

    def run(self, site: SiteContext) -> list[Finding]:
        raise NotImplementedError


class TechnicalIndexabilityAgent(Agent):
    name = "TechnicalIndexabilityAgent"

    @staticmethod
    def _directives(values: Sequence[str]) -> set[str]:
        tokens: set[str] = set()
        for value in values:
            tokens.update(token.strip().lower() for token in value.split(",") if token.strip())
        return tokens

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        if not site.robots_text:
            out.append(Finding(self.name, "ROBOTS_MISSING", "critical", "robots.txt is missing."))
        for error in site.robots.errors:
            out.append(Finding(self.name, "ROBOTS_SYNTAX", "error", error, "robots.txt"))
        canonical_owner: dict[str, list[str]] = defaultdict(list)
        for page in site.pages:
            path = page.relative_path
            if not page.title and page.indexable:
                out.append(Finding(self.name, "TITLE_MISSING", "error", "Indexable page has no title.", path))
            elif len(page.title) > 75:
                out.append(Finding(self.name, "TITLE_LONG", "warning", f"Title is {len(page.title)} characters.", path))
            if page.indexable:
                if len(page.descriptions) != 1:
                    out.append(Finding(self.name, "DESCRIPTION_COUNT", "error", f"Expected one meta description; found {len(page.descriptions)}.", path))
                elif not 60 <= len(page.descriptions[0]) <= 190:
                    out.append(Finding(self.name, "DESCRIPTION_LENGTH", "warning", f"Description is {len(page.descriptions[0])} characters.", path))
                if len(page.canonicals) != 1:
                    out.append(Finding(self.name, "CANONICAL_COUNT", "error", f"Expected one canonical; found {len(page.canonicals)}.", path))
                else:
                    actual = canonicalize_url(urljoin(site.base_url, page.canonicals[0]))
                    canonical_owner[actual].append(path)
                    if actual != canonicalize_url(page.expected_url):
                        out.append(Finding(self.name, "CANONICAL_MISMATCH", "error", "Canonical does not match the public route.", path, actual, page.expected_url))
                    if urlparse(actual).netloc != urlparse(site.base_url).netloc:
                        out.append(Finding(self.name, "CANONICAL_HOST", "critical", "Canonical points to a different host.", path, actual))
            robots = self._directives(page.robots)
            googlebot = self._directives(page.googlebot)
            combined = robots | googlebot
            if "index" in combined and "noindex" in combined:
                out.append(Finding(self.name, "ROBOTS_CONFLICT_INDEX", "critical", "Page declares both index and noindex.", path, page.combined_robots))
            if "follow" in combined and "nofollow" in combined:
                out.append(Finding(self.name, "ROBOTS_CONFLICT_FOLLOW", "critical", "Page declares both follow and nofollow.", path, page.combined_robots))
            preview_values = [token for token in combined if token.startswith("max-image-preview:")]
            if len(set(preview_values)) > 1:
                out.append(Finding(self.name, "ROBOTS_CONFLICT_PREVIEW", "error", "Conflicting image preview directives.", path, ", ".join(sorted(preview_values))))
        for canonical, owners in canonical_owner.items():
            if len(owners) > 1:
                out.append(Finding(self.name, "CANONICAL_DUPLICATE", "critical", "Multiple indexable pages claim the same canonical URL.", ", ".join(owners), canonical))
        return out


class SitemapCoverageAgent(Agent):
    name = "SitemapCoverageAgent"

    def _local_path(self, site: SiteContext, url: str) -> Path | None:
        parsed = urlparse(url)
        base = urlparse(site.base_url)
        if parsed.scheme and (parsed.scheme != base.scheme or parsed.netloc != base.netloc):
            return None
        path = parsed.path
        if parsed.scheme:
            base_path = base.path
            if not path.startswith(base_path):
                return None
            path = path[len(base_path):]
        candidate = (site.root / unquote(path.lstrip("/"))).resolve()
        try:
            candidate.relative_to(site.root)
        except ValueError:
            return None
        return candidate

    def _read_sitemap(self, site: SiteContext, path: Path, visited: set[Path], findings: list[Finding]) -> set[str]:
        urls: set[str] = set()
        if path in visited:
            return urls
        visited.add(path)
        if not path.exists():
            location = path.relative_to(site.root).as_posix() if path.is_relative_to(site.root) else str(path)
            findings.append(Finding(self.name, "SITEMAP_MISSING", "error", "Referenced sitemap does not exist in the deployment tree.", location))
            return urls
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            findings.append(Finding(self.name, "SITEMAP_XML_INVALID", "critical", f"Invalid sitemap XML: {exc}", path.relative_to(site.root).as_posix()))
            return urls
        local_name = root.tag.rsplit("}", 1)[-1]
        if local_name == "sitemapindex":
            for loc in root.findall(".//{*}loc"):
                if not loc.text:
                    continue
                child = self._local_path(site, loc.text.strip())
                if child is None:
                    findings.append(Finding(self.name, "SITEMAP_EXTERNAL", "error", "Sitemap index references an unexpected host or path.", path.relative_to(site.root).as_posix(), loc.text.strip()))
                    continue
                urls.update(self._read_sitemap(site, child, visited, findings))
        elif local_name == "urlset":
            seen: Counter[str] = Counter()
            for loc in root.findall(".//{*}loc"):
                if loc.text:
                    value = canonicalize_url(loc.text.strip())
                    urls.add(value)
                    seen[value] += 1
            for duplicate, count in seen.items():
                if count > 1:
                    findings.append(Finding(self.name, "SITEMAP_DUPLICATE_URL", "error", f"URL occurs {count} times in one sitemap.", path.relative_to(site.root).as_posix(), duplicate))
        else:
            findings.append(Finding(self.name, "SITEMAP_ROOT_INVALID", "critical", f"Unexpected sitemap root: {local_name}", path.relative_to(site.root).as_posix()))
        return urls

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        if not site.robots.sitemaps:
            out.append(Finding(self.name, "SITEMAP_NOT_REGISTERED", "critical", "robots.txt contains no Sitemap directive.", "robots.txt"))
            return out
        sitemap_urls: set[str] = set()
        visited: set[Path] = set()
        for sitemap_url in site.robots.sitemaps:
            path = self._local_path(site, sitemap_url)
            if path is None:
                out.append(Finding(self.name, "SITEMAP_HOST_MISMATCH", "critical", "Sitemap URL does not belong to the configured public site.", "robots.txt", sitemap_url))
                continue
            sitemap_urls.update(self._read_sitemap(site, path, visited, out))
        expected = {canonicalize_url(page.expected_url) for page in site.pages if page.indexable}
        for url in sorted(expected - sitemap_urls):
            page = site.page_by_url.get(url)
            out.append(Finding(self.name, "SITEMAP_PAGE_MISSING", "warning", "Indexable page is not present in registered sitemaps.", page.relative_path if page else "", url))
        for url in sorted(sitemap_urls - expected):
            out.append(Finding(self.name, "SITEMAP_STALE_URL", "error", "Sitemap URL has no matching indexable HTML page in the deployment tree.", evidence=url))
        return out


class StructuredDataAgent(Agent):
    name = "StructuredDataAgent"

    @staticmethod
    def _walk(value: Any) -> Iterable[dict[str, Any]]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from StructuredDataAgent._walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from StructuredDataAgent._walk(child)

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        for page in site.pages:
            for error in page.json_ld_errors:
                out.append(Finding(self.name, "JSONLD_INVALID", "critical", f"Invalid JSON-LD: {error}", page.relative_path))
            types: set[str] = set()
            for document in page.json_ld:
                for node in self._walk(document):
                    context = node.get("@context")
                    if context and context not in {"https://schema.org", "http://schema.org"}:
                        out.append(Finding(self.name, "JSONLD_CONTEXT", "warning", "JSON-LD uses an unexpected @context.", page.relative_path, str(context)))
                    node_type = node.get("@type")
                    if isinstance(node_type, str):
                        types.add(node_type)
                    elif isinstance(node_type, list):
                        types.update(str(item) for item in node_type)
                    for key in ("url", "@id", "image", "logo"):
                        value = node.get(key)
                        candidates: list[str] = []
                        if isinstance(value, str):
                            candidates = [value]
                        elif isinstance(value, dict) and isinstance(value.get("url"), str):
                            candidates = [value["url"]]
                        for candidate in candidates:
                            if candidate.startswith("/"):
                                out.append(Finding(self.name, "JSONLD_RELATIVE_URL", "error", "Structured data URL should be absolute.", page.relative_path, candidate))
            if page.relative_path == "index.html":
                missing = {"Organization", "WebSite"} - types
                if missing:
                    out.append(Finding(self.name, "HOME_SCHEMA_MISSING", "error", "Homepage is missing core organization/site schema.", page.relative_path, ", ".join(sorted(missing))))
            elif page.indexable and page.relative_path.count("/") <= 1 and not page.json_ld:
                out.append(Finding(self.name, "SECTION_SCHEMA_MISSING", "warning", "Top-level indexable section has no JSON-LD.", page.relative_path))
        return out


class ContentSemanticsAgent(Agent):
    name = "ContentSemanticsAgent"

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        title_owner: dict[str, list[str]] = defaultdict(list)
        description_owner: dict[str, list[str]] = defaultdict(list)
        content_hash_owner: dict[str, list[str]] = defaultdict(list)
        for page in site.pages:
            if not page.indexable:
                continue
            normalized_title = compact_text(page.title).casefold()
            if normalized_title:
                title_owner[normalized_title].append(page.relative_path)
            if len(page.descriptions) == 1:
                normalized_desc = compact_text(page.descriptions[0]).casefold()
                if normalized_desc:
                    description_owner[normalized_desc].append(page.relative_path)
            if len(page.h1_texts) != 1:
                out.append(Finding(self.name, "H1_COUNT", "error", f"Expected one visible H1; found {len(page.h1_texts)}.", page.relative_path))
            if page.word_count < 90 and page.relative_path != "index.html":
                out.append(Finding(self.name, "THIN_PAGE", "warning", f"Only {page.word_count} visible words were found.", page.relative_path))
            if page.word_count >= 90:
                digest = hashlib.sha256(page.visible_text.casefold().encode("utf-8")).hexdigest()
                content_hash_owner[digest].append(page.relative_path)
            for keyword_value in page.keywords:
                keyword_count = len([item for item in keyword_value.split(",") if item.strip()])
                if keyword_count > 30:
                    out.append(Finding(self.name, "META_KEYWORDS_EXCESS", "warning", f"Meta keywords contains {keyword_count} entries. This tag is not a ranking lever and should not be stuffed.", page.relative_path))
            if page.is_arabic and page.lang and not page.lang.lower().startswith("ar"):
                out.append(Finding(self.name, "LANG_CONTENT_MISMATCH", "error", "Arabic-dominant text has a non-Arabic html lang value.", page.relative_path, page.lang))
        for value, owners in title_owner.items():
            if len(owners) > 1:
                out.append(Finding(self.name, "DUPLICATE_TITLE", "error", "Duplicate page title across indexable pages.", ", ".join(owners), value[:160]))
        for value, owners in description_owner.items():
            if len(owners) > 1:
                out.append(Finding(self.name, "DUPLICATE_DESCRIPTION", "warning", "Duplicate meta description across indexable pages.", ", ".join(owners), value[:160]))
        for owners in content_hash_owner.values():
            if len(owners) > 1:
                out.append(Finding(self.name, "DUPLICATE_CONTENT", "error", "Pages have identical visible content.", ", ".join(owners)))
        return out


class InternalLinkingAgent(Agent):
    name = "InternalLinkingAgent"

    @staticmethod
    def _resolve(page: Page, href: str, base_url: str) -> str | None:
        value = href.strip()
        if not value or value.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            return None
        resolved = urljoin(page.expected_url, value)
        parsed = urlparse(resolved)
        base = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != base.netloc.lower():
            return None
        return canonicalize_url(strip_fragment_query(resolved))

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        inbound: Counter[str] = Counter()
        existing_urls = set(site.page_by_url)
        for page in site.pages:
            seen_targets: set[str] = set()
            for link in page.links:
                target = self._resolve(page, link.href, site.base_url)
                if target is None:
                    continue
                if target in seen_targets:
                    continue
                seen_targets.add(target)
                if target in existing_urls:
                    if "nofollow" not in link.rel:
                        inbound[target] += 1
                else:
                    path = urlparse(target).path
                    if path.endswith((".xml", ".json", ".txt", ".rss", ".atom", ".webmanifest", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".pdf")):
                        continue
                    out.append(Finding(self.name, "BROKEN_INTERNAL_LINK", "error", "Internal HTML link has no matching published page.", page.relative_path, link.href))
                if link.text and len(link.text) <= 2 and not re.search(r"[\w\u0600-\u06ff]", link.text):
                    out.append(Finding(self.name, "EMPTY_LINK_TEXT", "warning", "Internal link has non-descriptive anchor text.", page.relative_path, link.href))
        home = canonicalize_url(site.base_url)
        for page in site.pages:
            url = canonicalize_url(page.expected_url)
            if page.indexable and url != home and inbound[url] == 0:
                out.append(Finding(self.name, "ORPHAN_PAGE", "warning", "Indexable page has no crawlable inbound internal link.", page.relative_path, url))
        return out


class InternationalSeoAgent(Agent):
    name = "InternationalSeoAgent"
    HREFLANG_RE = re.compile(r"^(x-default|[a-z]{2,3}(?:-[a-z]{2}|-[A-Z]{2})?)$")

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        for page in site.pages:
            if page.indexable and not page.lang:
                out.append(Finding(self.name, "HTML_LANG_MISSING", "error", "Indexable page has no html lang attribute.", page.relative_path))
            if page.is_arabic and page.direction != "rtl":
                out.append(Finding(self.name, "RTL_MISSING", "error", "Arabic page should declare dir=rtl on the html element.", page.relative_path, page.direction or "missing"))
            for code, values in page.hreflangs.items():
                if not self.HREFLANG_RE.match(code):
                    out.append(Finding(self.name, "HREFLANG_INVALID", "error", "Invalid hreflang code.", page.relative_path, code))
                if len(values) > 1:
                    out.append(Finding(self.name, "HREFLANG_DUPLICATE", "error", "Duplicate hreflang value on a page.", page.relative_path, code))
                for value in values:
                    absolute = canonicalize_url(urljoin(site.base_url, value))
                    if urlparse(absolute).netloc != urlparse(site.base_url).netloc:
                        out.append(Finding(self.name, "HREFLANG_HOST", "error", "hreflang points to a different host.", page.relative_path, absolute))
            if page.hreflangs:
                language_code = (page.lang or "").lower().split("-", 1)[0]
                self_values = page.hreflangs.get(language_code, []) + page.hreflangs.get(page.lang.lower(), [])
                if not any(canonicalize_url(urljoin(site.base_url, value)) == canonicalize_url(page.expected_url) for value in self_values):
                    out.append(Finding(self.name, "HREFLANG_SELF_MISSING", "warning", "hreflang cluster lacks a self-referencing language URL.", page.relative_path))
                if "x-default" not in page.hreflangs:
                    out.append(Finding(self.name, "HREFLANG_DEFAULT_MISSING", "warning", "hreflang cluster has no x-default URL.", page.relative_path))
            locales = page.og.get("og:locale", [])
            for locale in locales:
                if not re.match(r"^[a-z]{2,3}_[A-Z]{2}$", locale):
                    out.append(Finding(self.name, "OG_LOCALE_INVALID", "error", "OpenGraph locale should look like ar_JO, not an uppercased BCP-47 tag.", page.relative_path, locale))
        return out


class MediaAndPreviewAgent(Agent):
    name = "MediaAndPreviewAgent"

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        for page in site.pages:
            if not page.indexable:
                continue
            for image in page.images:
                if image.alt is None:
                    out.append(Finding(self.name, "IMAGE_ALT_MISSING", "error", "Image is missing an alt attribute.", page.relative_path, image.src))
                if image.src and not image.width and not image.height:
                    out.append(Finding(self.name, "IMAGE_DIMENSIONS_MISSING", "warning", "Image has no intrinsic width or height; this can increase layout shift.", page.relative_path, image.src))
            og_images = page.og.get("og:image", [])
            twitter_images = page.twitter.get("twitter:image", [])
            if page.relative_path == "index.html" or page.relative_path.count("/") <= 1:
                if not og_images:
                    out.append(Finding(self.name, "OG_IMAGE_MISSING", "warning", "Important page has no OpenGraph image.", page.relative_path))
                if not twitter_images:
                    out.append(Finding(self.name, "TWITTER_IMAGE_MISSING", "warning", "Important page has no Twitter/X image.", page.relative_path))
            for value in og_images + twitter_images:
                absolute = urljoin(site.base_url, value)
                parsed = urlparse(absolute)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    out.append(Finding(self.name, "SOCIAL_IMAGE_NOT_ABSOLUTE", "error", "Social preview image URL is not absolute.", page.relative_path, value))
                if parsed.path.lower().endswith(".svg"):
                    out.append(Finding(self.name, "SOCIAL_IMAGE_SVG", "warning", "Use a 1200×630 PNG/JPEG/WebP social image; SVG support is inconsistent across consumers.", page.relative_path, absolute))
        return out


class AiDiscoveryAgent(Agent):
    name = "AiDiscoveryAgent"

    def run(self, site: SiteContext) -> list[Finding]:
        out: list[Finding] = []
        if not site.robots_text:
            return out
        for bot in SEARCH_AND_ANSWER_BOTS:
            if not site.robots.root_allowed(bot):
                out.append(Finding(self.name, "AI_SEARCH_BLOCKED", "critical", f"{bot} is blocked from the public root.", "robots.txt"))
        for bot in TRAINING_OR_MODEL_BOTS:
            if not site.robots.root_allowed(bot):
                out.append(Finding(self.name, "AI_TRAINING_BLOCKED", "info", f"{bot} is not permitted at the public root. This affects model-use policy, not ordinary search eligibility.", "robots.txt"))
        if not site.llms_text:
            out.append(Finding(self.name, "LLMS_TXT_MISSING", "warning", "llms.txt is absent. It is optional and not required by Google, but can help compatible AI tools discover authoritative sections."))
        else:
            if not site.llms_text.lstrip().startswith("#"):
                out.append(Finding(self.name, "LLMS_TXT_TITLE", "warning", "llms.txt should start with a clear H1 title.", "llms.txt"))
            if site.base_url not in site.llms_text:
                out.append(Finding(self.name, "LLMS_TXT_BASE_URL", "warning", "llms.txt does not mention the canonical public base URL.", "llms.txt"))
            if "sitemap" not in site.llms_text.lower():
                out.append(Finding(self.name, "LLMS_TXT_SITEMAP", "warning", "llms.txt does not identify the sitemap entry point.", "llms.txt"))
        homepage = site.page_by_path.get("index.html")
        if homepage:
            directives = TechnicalIndexabilityAgent._directives(homepage.robots + homepage.googlebot)
            if "nosnippet" in directives or "max-snippet:0" in directives:
                out.append(Finding(self.name, "AI_SNIPPET_BLOCKED", "critical", "Homepage snippet controls prevent use as a supporting result in search AI features.", "index.html"))
        return out


AGENT_TYPES: tuple[type[Agent], ...] = (
    TechnicalIndexabilityAgent,
    SitemapCoverageAgent,
    StructuredDataAgent,
    ContentSemanticsAgent,
    InternalLinkingAgent,
    InternationalSeoAgent,
    MediaAndPreviewAgent,
    AiDiscoveryAgent,
)


@dataclass(slots=True)
class AuditReport:
    version: int
    generated_at: str
    root: str
    base_url: str
    agents: list[str]
    page_count: int
    indexable_page_count: int
    counts: dict[str, int]
    status: str
    findings: list[Finding]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"

    def to_markdown(self) -> str:
        lines = [
            f"# SEO Agent Fleet Report v{self.version}",
            "",
            f"- Status: **{self.status}**",
            f"- Generated: `{self.generated_at}`",
            f"- Base URL: `{self.base_url}`",
            f"- Pages scanned: **{self.page_count}**",
            f"- Indexable pages: **{self.indexable_page_count}**",
            f"- Agents: **{len(self.agents)}**",
            "",
            "## Severity counts",
            "",
        ]
        for severity in ("critical", "error", "warning", "info"):
            lines.append(f"- {severity}: **{self.counts.get(severity, 0)}**")
        lines.extend(["", "## Findings", ""])
        if not self.findings:
            lines.append("No findings.")
        else:
            for finding in self.findings:
                location = f" — `{finding.path}`" if finding.path else ""
                lines.append(f"### [{finding.severity.upper()}] {finding.code}{location}")
                lines.append("")
                lines.append(finding.message)
                if finding.evidence:
                    lines.extend(["", f"Evidence: `{finding.evidence}`"])
                if finding.remediation:
                    lines.extend(["", f"Remediation: {finding.remediation}"])
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def run_fleet(site: SiteContext) -> AuditReport:
    findings: list[Finding] = []
    agents: list[str] = []
    for agent_type in AGENT_TYPES:
        agent = agent_type()
        agents.append(agent.name)
        findings.extend(agent.run(site))
    findings.sort(key=lambda f: (-SEVERITY_RANK[f.severity], f.agent, f.code, f.path, f.message))
    counts = {severity: sum(1 for finding in findings if finding.severity == severity) for severity in SEVERITY_RANK}
    status = "failed" if counts["critical"] else "passed_with_findings" if findings else "passed"
    return AuditReport(
        version=VERSION,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        root=str(site.root),
        base_url=site.base_url,
        agents=agents,
        page_count=len(site.pages),
        indexable_page_count=sum(1 for page in site.pages if page.indexable),
        counts=counts,
        status=status,
        findings=findings,
    )


def discovery_robots(base_url: str, *, allow_training: bool = True) -> str:
    lines = [
        "# Public search and AI-discovery policy",
        "# Search, answer engines, user-triggered assistants, and public model crawlers",
        "# may access all public content. Operational source paths are excluded.",
        "User-agent: *",
        "Allow: /",
        "Disallow: /.git/",
        "Disallow: /.github/",
        "Disallow: /scripts/",
        "Disallow: /tests/",
        "Disallow: /node_modules/",
        "Disallow: /api/private/",
        "",
    ]
    if not allow_training:
        for bot in TRAINING_OR_MODEL_BOTS:
            lines.extend([f"User-agent: {bot}", "Disallow: /", ""])
    sitemap_names = (
        "sitemap.xml",
        "sitemap-care-guides.xml",
        "sitemap-outside-the-box-evidence.xml",
        "sitemap-specialists-partners.xml",
        "sitemap-index.xml",
    )
    lines.extend(f"Sitemap: {urljoin(base_url, name)}" for name in sitemap_names)
    return "\n".join(lines).rstrip() + "\n"


def discovery_llms(base_url: str) -> str:
    sections = [
        ("الموسوعة النفسية", "encyclopedia/"),
        ("ذوو الاحتياجات الخاصة", "special-needs/"),
        ("المكتبة والأبحاث", "library/"),
        ("أدلة الرعاية", "care-guides/"),
        ("الأدوات النفسية", "daily-tools/"),
        ("المقارنات النفسية", "comparisons/"),
        ("مسارات التعلم", "learning-paths/"),
        ("واجهة البيانات العامة", "api/"),
    ]
    lines = [
        "# منصة الصحة النفسية وذوي الاحتياجات الخاصة",
        "",
        "> بوابة عربية مؤسسية للصحة النفسية وعلم النفس وموارد الأشخاص ذوي الاحتياجات الخاصة، مع أدلة ومراجع ومصادر ظاهرة داخل الصفحات.",
        "",
        f"Canonical site: {base_url}",
        "Primary language: Arabic (ar), right-to-left",
        "Content policy: educational and professional reference; not a substitute for diagnosis or emergency care",
        "",
        "## Primary sections",
        "",
    ]
    lines.extend(f"- [{name}]({urljoin(base_url, path)})" for name, path in sections)
    lines.extend(
        [
            "",
            "## Discovery and machine-readable resources",
            "",
            f"- [Sitemap index]({urljoin(base_url, 'sitemap-index.xml')})",
            f"- [Primary sitemap]({urljoin(base_url, 'sitemap.xml')})",
            f"- [OpenSearch description]({urljoin(base_url, 'opensearch.xml')})",
            f"- [Public API directory]({urljoin(base_url, 'api/')})",
            f"- [Research RSS]({urljoin(base_url, 'research.xml')})",
            "",
            "## Trust and citation guidance",
            "",
            "Prefer canonical URLs. Cite the page title, visible author/reviewer when present, publication or update date, and the original references listed on each page. Do not infer a diagnosis or treatment plan from educational pages.",
            "",
            "This file is a supplementary discovery aid. Search engines may ignore it; robots.txt, sitemaps, indexable text, internal links, and page-level metadata remain authoritative.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def discovery_policy_json(base_url: str, *, allow_training: bool = True) -> str:
    payload = {
        "version": VERSION,
        "updated_at": datetime.now(timezone.utc).date().isoformat(),
        "canonical_site": base_url,
        "public_content_access": "allowed",
        "search_and_answer_access": "allowed",
        "training_and_model_improvement_access": "allowed" if allow_training else "disallowed",
        "search_and_answer_user_agents": list(SEARCH_AND_ANSWER_BOTS),
        "training_or_model_user_agents": list(TRAINING_OR_MODEL_BOTS),
        "authoritative_controls": ["robots.txt", "page-level robots meta", "HTTP X-Robots-Tag"],
        "supplementary_discovery": ["llms.txt", "sitemap-index.xml", "opensearch.xml", "api/"],
        "notes": [
            "robots.txt is advisory and respected only by compliant crawlers.",
            "Allowing a crawler does not guarantee indexing, ranking, citation, or inclusion in an AI answer.",
            "Search access and model-training access are separate policy decisions even when both are allowed.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_discovery_files(root: Path, base_url: str, allow_training: bool) -> None:
    (root / "robots.txt").write_text(discovery_robots(base_url, allow_training=allow_training), encoding="utf-8")
    (root / "llms.txt").write_text(discovery_llms(base_url), encoding="utf-8")
    policy_path = root / "api" / "ai-crawler-policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(discovery_policy_json(base_url, allow_training=allow_training), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Published static site root")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--report-dir", default="seo-audit")
    parser.add_argument("--write-discovery-files", action="store_true")
    parser.add_argument("--disallow-training", action="store_true", help="When generating robots.txt, block model-training crawlers while leaving search/answer access open")
    parser.add_argument("--fail-on", choices=tuple(SEVERITY_RANK), default="critical")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"Site root is not a directory: {root}", file=sys.stderr)
        return 2
    base_url = normalize_base_url(args.base_url)
    if args.write_discovery_files:
        write_discovery_files(root, base_url, allow_training=not args.disallow_training)
    site = SiteContext.load(root, base_url)
    report = run_fleet(site)
    report_dir = Path(args.report_dir)
    if not report_dir.is_absolute():
        report_dir = root / report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / REPORT_JSON).write_text(report.to_json(), encoding="utf-8")
    (report_dir / REPORT_MD).write_text(report.to_markdown(), encoding="utf-8")
    print(report.to_json(), end="")
    threshold = SEVERITY_RANK[args.fail_on]
    return 1 if any(SEVERITY_RANK[f.severity] >= threshold for f in report.findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
