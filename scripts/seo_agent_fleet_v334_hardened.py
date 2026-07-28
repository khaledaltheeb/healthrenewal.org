#!/usr/bin/env python3
"""Hardened production adapter for the v334 eight-agent SEO audit.

This module keeps the reviewed v334 engine stable while correcting four
production-edge cases discovered against the generated site:

* project-path robots.txt files are not treated as origin-authoritative;
* resource URLs in sitemaps are not mislabeled as stale HTML pages;
* existing CSV/TSV/files and explicit index.html links are not broken links;
* small Arabic navigation fragments do not relabel English/Spanish pages.

The adapter intentionally reuses the complete v334 parser, report model and CLI.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import seo_agent_fleet_v334 as core

ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
LATIN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")


def _dominant_arabic(page: core.Page) -> bool:
    declared = (page.lang or "").strip().lower()
    if declared.startswith("ar"):
        return True
    sample = page.visible_text[:5000]
    arabic = len(ARABIC_RE.findall(sample))
    latin = len(LATIN_RE.findall(sample))
    if declared and not declared.startswith("ar"):
        return arabic >= 80 and arabic > latin * 1.5
    return arabic >= 40 and arabic > latin * 1.25


core.Page.is_arabic = property(_dominant_arabic)  # type: ignore[assignment]


def _local_public_path(site: core.SiteContext, url: str) -> Path | None:
    parsed = urlparse(url)
    base = urlparse(site.base_url)
    if parsed.scheme and (
        parsed.scheme.lower() != base.scheme.lower()
        or parsed.netloc.lower() != base.netloc.lower()
    ):
        return None
    path = parsed.path
    if parsed.scheme:
        if not path.startswith(base.path):
            return None
        path = path[len(base.path) :]
    candidate = (site.root / unquote(path.lstrip("/"))).resolve()
    try:
        candidate.relative_to(site.root.resolve())
    except ValueError:
        return None
    return candidate


def _published_resource_exists(site: core.SiteContext, url: str) -> bool:
    candidate = _local_public_path(site, url)
    if candidate is None:
        return False
    if candidate.is_file():
        return True
    if candidate.is_dir() and (candidate / "index.html").is_file():
        return True
    if not candidate.suffix and (candidate / "index.html").is_file():
        return True
    return False


class SitemapCoverageAgent(core.SitemapCoverageAgent):
    """Keep HTML coverage checks while accepting real non-HTML resources."""

    def run(self, site: core.SiteContext) -> list[core.Finding]:
        out: list[core.Finding] = []
        if not site.robots.sitemaps:
            out.append(
                core.Finding(
                    self.name,
                    "SITEMAP_NOT_REGISTERED",
                    "critical",
                    "robots.txt contains no Sitemap directive.",
                    "robots.txt",
                )
            )
            return out
        sitemap_urls: set[str] = set()
        visited: set[Path] = set()
        for sitemap_url in site.robots.sitemaps:
            path = self._local_path(site, sitemap_url)
            if path is None:
                out.append(
                    core.Finding(
                        self.name,
                        "SITEMAP_HOST_MISMATCH",
                        "critical",
                        "Sitemap URL does not belong to the configured public site.",
                        "robots.txt",
                        sitemap_url,
                    )
                )
                continue
            sitemap_urls.update(self._read_sitemap(site, path, visited, out))
        expected = {
            core.canonicalize_url(page.expected_url)
            for page in site.pages
            if page.indexable
        }
        for url in sorted(expected - sitemap_urls):
            page = site.page_by_url.get(url)
            out.append(
                core.Finding(
                    self.name,
                    "SITEMAP_PAGE_MISSING",
                    "warning",
                    "Indexable page is not present in registered sitemaps.",
                    page.relative_path if page else "",
                    url,
                )
            )
        for url in sorted(sitemap_urls - expected):
            if _published_resource_exists(site, url):
                continue
            out.append(
                core.Finding(
                    self.name,
                    "SITEMAP_STALE_URL",
                    "error",
                    "Sitemap URL has no matching published resource in the deployment tree.",
                    evidence=url,
                )
            )
        return out


class InternalLinkingAgent(core.InternalLinkingAgent):
    """Resolve route aliases and verify every local published resource."""

    @staticmethod
    def _resolve(page: core.Page, href: str, base_url: str) -> str | None:
        value = href.strip()
        if not value or value.startswith(
            ("#", "mailto:", "tel:", "javascript:", "data:")
        ):
            return None
        resolved = urljoin(page.expected_url, value)
        parsed = urlparse(resolved)
        base = urlparse(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.netloc.lower() != base.netloc.lower()
        ):
            return None
        path = parsed.path
        if path.endswith("/index.html"):
            path = path[: -len("index.html")]
        elif path == "/index.html":
            path = "/"
        normalized = urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
        return core.canonicalize_url(normalized)

    def run(self, site: core.SiteContext) -> list[core.Finding]:
        out: list[core.Finding] = []
        inbound: Counter[str] = Counter()
        existing_urls = set(site.page_by_url)
        for page in site.pages:
            seen_targets: set[str] = set()
            for link in page.links:
                target = self._resolve(page, link.href, site.base_url)
                if target is None or target in seen_targets:
                    continue
                seen_targets.add(target)
                if target in existing_urls:
                    if "nofollow" not in link.rel:
                        inbound[target] += 1
                elif not _published_resource_exists(site, target):
                    out.append(
                        core.Finding(
                            self.name,
                            "BROKEN_INTERNAL_LINK",
                            "error",
                            "Internal link has no matching published page or resource.",
                            page.relative_path,
                            link.href,
                        )
                    )
                if (
                    link.text
                    and len(link.text) <= 2
                    and not re.search(r"[\w\u0600-\u06ff]", link.text)
                ):
                    out.append(
                        core.Finding(
                            self.name,
                            "EMPTY_LINK_TEXT",
                            "warning",
                            "Internal link has non-descriptive anchor text.",
                            page.relative_path,
                            link.href,
                        )
                    )
        home = core.canonicalize_url(site.base_url)
        for page in site.pages:
            url = core.canonicalize_url(page.expected_url)
            if page.indexable and url != home and inbound[url] == 0:
                out.append(
                    core.Finding(
                        self.name,
                        "ORPHAN_PAGE",
                        "warning",
                        "Indexable page has no crawlable inbound internal link.",
                        page.relative_path,
                        url,
                    )
                )
        return out


class AiDiscoveryAgent(core.AiDiscoveryAgent):
    """Distinguish page-level discovery from origin-root robots authority."""

    def run(self, site: core.SiteContext) -> list[core.Finding]:
        out: list[core.Finding] = []
        base = urlparse(site.base_url)
        origin_root = urlunparse((base.scheme, base.netloc, "/", "", "", ""))
        robots_is_authoritative = base.path in {"", "/"}

        if site.robots_text and robots_is_authoritative:
            for bot in core.SEARCH_AND_ANSWER_BOTS:
                if not site.robots.root_allowed(bot):
                    out.append(
                        core.Finding(
                            self.name,
                            "AI_SEARCH_BLOCKED",
                            "critical",
                            f"{bot} is blocked from the public root.",
                            "robots.txt",
                        )
                    )
            for bot in core.TRAINING_OR_MODEL_BOTS:
                if not site.robots.root_allowed(bot):
                    out.append(
                        core.Finding(
                            self.name,
                            "AI_TRAINING_BLOCKED",
                            "info",
                            f"{bot} is not permitted at the public root. This affects model-use policy, not ordinary search eligibility.",
                            "robots.txt",
                        )
                    )
        elif site.robots_text:
            out.append(
                core.Finding(
                    self.name,
                    "ROBOTS_SUBPATH_NON_AUTHORITATIVE",
                    "info",
                    "This project-path robots.txt is useful as a sitemap manifest but cannot control the whole GitHub Pages host. Crawler policy is authoritative only at the origin root.",
                    "robots.txt",
                    origin_root + "robots.txt",
                    "Publish an origin-root robots.txt through a custom domain or the user-site repository, while keeping page-level index/follow directives intact.",
                )
            )

        if not site.llms_text:
            out.append(
                core.Finding(
                    self.name,
                    "LLMS_TXT_MISSING",
                    "warning",
                    "llms.txt is absent. It is optional and not required by Google, but can help compatible AI tools discover authoritative sections.",
                )
            )
        else:
            if not site.llms_text.lstrip().startswith("#"):
                out.append(
                    core.Finding(
                        self.name,
                        "LLMS_TXT_TITLE",
                        "warning",
                        "llms.txt should start with a clear H1 title.",
                        "llms.txt",
                    )
                )
            if site.base_url not in site.llms_text:
                out.append(
                    core.Finding(
                        self.name,
                        "LLMS_TXT_BASE_URL",
                        "warning",
                        "llms.txt does not mention the canonical public base URL.",
                        "llms.txt",
                    )
                )
            if "sitemap" not in site.llms_text.lower():
                out.append(
                    core.Finding(
                        self.name,
                        "LLMS_TXT_SITEMAP",
                        "warning",
                        "llms.txt does not identify the sitemap entry point.",
                        "llms.txt",
                    )
                )

        homepage = site.page_by_path.get("index.html")
        if homepage:
            directives = core.TechnicalIndexabilityAgent._directives(
                homepage.robots + homepage.googlebot
            )
            if "nosnippet" in directives or "max-snippet:0" in directives:
                out.append(
                    core.Finding(
                        self.name,
                        "AI_SNIPPET_BLOCKED",
                        "critical",
                        "Homepage snippet controls prevent use as a supporting result in search AI features.",
                        "index.html",
                    )
                )
        return out


core.SitemapCoverageAgent = SitemapCoverageAgent
core.InternalLinkingAgent = InternalLinkingAgent
core.AiDiscoveryAgent = AiDiscoveryAgent
core.AGENT_TYPES = (
    core.TechnicalIndexabilityAgent,
    SitemapCoverageAgent,
    core.StructuredDataAgent,
    core.ContentSemanticsAgent,
    InternalLinkingAgent,
    core.InternationalSeoAgent,
    core.MediaAndPreviewAgent,
    AiDiscoveryAgent,
)

Finding = core.Finding
Page = core.Page
SiteContext = core.SiteContext
TechnicalIndexabilityAgent = core.TechnicalIndexabilityAgent
run_fleet = core.run_fleet
canonicalize_url = core.canonicalize_url
parse_robots = core.parse_robots


def main() -> int:
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
