#!/usr/bin/env python3
"""Non-destructive live search-discovery audit for HealthRenewal.

This script only reads public URLs and writes local report files. It does not
modify the website, DNS, sitemaps, robots.txt, Search Console, Bing, or hosting.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import gzip
import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

USER_AGENT = (
    "HealthRenewal-Live-Discovery-Audit/1.0 "
    "(+https://healthrenewal.org/trust/)"
)
HTML_LIMIT = 512 * 1024
SITEMAP_LIMIT = 50 * 1024 * 1024
DEFAULT_TIMEOUT = 20
MAX_SITEMAP_DEPTH = 4
SUPPORTED_HTML_TYPES = {"text/html", "application/xhtml+xml"}


@dataclasses.dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    elapsed_ms: int
    error: str = ""


@dataclasses.dataclass(frozen=True)
class PageSignals:
    canonical: str
    robots: tuple[str, ...]
    hreflang: tuple[tuple[str, str], ...]
    title: str

    @property
    def noindex(self) -> bool:
        return "noindex" in " ".join(self.robots).lower()


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.robots: list[str] = []
        self.hreflang: list[tuple[str, str]] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self._head_closed = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._head_closed:
            return
        values = {str(key).lower(): (value or "").strip() for key, value in attrs}
        tag = tag.lower()
        if tag == "link":
            rel = {part.lower() for part in values.get("rel", "").split()}
            href = values.get("href", "")
            if "canonical" in rel and href and not self.canonical:
                self.canonical = href
            language = values.get("hreflang", "").lower()
            if "alternate" in rel and language and href:
                self.hreflang.append((language, href))
        elif tag == "meta":
            name = values.get("name", "").lower()
            if name in {"robots", "googlebot", "bingbot"}:
                self.robots.append(values.get("content", ""))
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self._head_closed = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)

    def signals(self, base_url: str) -> PageSignals:
        canonical = urllib.parse.urljoin(base_url, self.canonical) if self.canonical else ""
        hreflang = tuple(
            (language, urllib.parse.urljoin(base_url, href))
            for language, href in self.hreflang
        )
        title = " ".join("".join(self.title_parts).split())
        return PageSignals(
            canonical=canonical,
            robots=tuple(self.robots),
            hreflang=hreflang,
            title=title,
        )


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host
    if port and not (
        (scheme == "https" and port == 443)
        or (scheme == "http" and port == 80)
    ):
        netloc = f"{host}:{port}"
    path = parsed.path or "/"
    return urllib.parse.urlunsplit((scheme, netloc, path, parsed.query, ""))


def same_origin(url: str, origin: str) -> bool:
    left = urllib.parse.urlsplit(url)
    right = urllib.parse.urlsplit(origin)
    return (
        left.scheme.lower(),
        (left.hostname or "").lower(),
        left.port or (443 if left.scheme.lower() == "https" else 80),
    ) == (
        right.scheme.lower(),
        (right.hostname or "").lower(),
        right.port or (443 if right.scheme.lower() == "https" else 80),
    )


def request_url(url: str, *, timeout: int, limit: int) -> FetchResult:
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml,"
                "text/xml;q=0.9,*/*;q=0.1"
            ),
            "Accept-Encoding": "gzip",
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=ssl.create_default_context(),
        ) as response:
            status = int(getattr(response, "status", response.getcode()))
            final_url = response.geturl()
            content_type = response.headers.get_content_type().lower()
            body = response.read(limit + 1)
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                body = gzip.decompress(body)
            if len(body) > limit:
                body = body[:limit]
            elapsed = int((time.monotonic() - started) * 1000)
            return FetchResult(
                requested_url=url,
                final_url=final_url,
                status=status,
                content_type=content_type,
                body=body,
                elapsed_ms=elapsed,
            )
    except urllib.error.HTTPError as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        return FetchResult(
            requested_url=url,
            final_url=exc.geturl() or url,
            status=int(exc.code),
            content_type=(
                exc.headers.get_content_type().lower() if exc.headers else ""
            ),
            body=b"",
            elapsed_ms=elapsed,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except (
        urllib.error.URLError,
        TimeoutError,
        socket.timeout,
        ssl.SSLError,
        OSError,
    ) as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        return FetchResult(
            requested_url=url,
            final_url=url,
            status=0,
            content_type="",
            body=b"",
            elapsed_ms=elapsed,
            error=f"{type(exc).__name__}: {exc}",
        )


def decode_body(result: FetchResult) -> str:
    if not result.body:
        return ""
    for encoding in ("utf-8-sig", "utf-8", "windows-1256", "iso-8859-1"):
        try:
            return result.body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return result.body.decode("utf-8", errors="replace")


def robots_sitemaps(text: str, base_url: str) -> list[str]:
    values: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        name, value = line.split(":", 1)
        if name.strip().lower() != "sitemap":
            continue
        candidate = normalize_url(urllib.parse.urljoin(base_url, value.strip()))
        if candidate not in values:
            values.append(candidate)
    return values


def parse_sitemap(xml_text: str, source_url: str) -> tuple[str, list[str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML at {source_url}: {exc}") from exc
    local_name = root.tag.rsplit("}", 1)[-1].lower()
    if local_name not in {"urlset", "sitemapindex"}:
        raise ValueError(
            f"Unsupported sitemap root {root.tag!r} at {source_url}"
        )
    values: list[str] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() != "loc":
            continue
        if node.text and node.text.strip():
            values.append(
                normalize_url(
                    urllib.parse.urljoin(source_url, node.text.strip())
                )
            )
    return local_name, values


def discover_sitemaps(
    seeds: Iterable[str],
    *,
    origin: str,
    timeout: int,
    max_depth: int,
) -> tuple[dict[str, dict[str, object]], list[str], list[str]]:
    queue: deque[tuple[str, int]] = deque(
        (normalize_url(seed), 0) for seed in seeds
    )
    visited: set[str] = set()
    sitemap_reports: dict[str, dict[str, object]] = {}
    page_urls: list[str] = []
    errors: list[str] = []

    while queue:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        if not same_origin(url, origin):
            errors.append(f"Cross-origin sitemap rejected: {url}")
            continue
        if depth > max_depth:
            errors.append(
                f"Sitemap nesting exceeds depth {max_depth}: {url}"
            )
            continue

        result = request_url(url, timeout=timeout, limit=SITEMAP_LIMIT)
        record: dict[str, object] = {
            "url": url,
            "finalUrl": result.final_url,
            "status": result.status,
            "contentType": result.content_type,
            "elapsedMs": result.elapsed_ms,
            "error": result.error,
            "depth": depth,
        }
        sitemap_reports[url] = record
        if result.status != 200:
            errors.append(f"Sitemap unavailable ({result.status}): {url}")
            continue
        try:
            kind, values = parse_sitemap(decode_body(result), url)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        record["kind"] = kind
        record["entryCount"] = len(values)
        if kind == "sitemapindex":
            for child in values:
                queue.append((child, depth + 1))
        else:
            page_urls.extend(values)

    return sitemap_reports, page_urls, errors


def parse_page_signals(result: FetchResult) -> PageSignals:
    parser = HeadParser()
    parser.feed(decode_body(result))
    return parser.signals(result.final_url or result.requested_url)


def audit_page(url: str, *, origin: str, timeout: int) -> dict[str, object]:
    result = request_url(url, timeout=timeout, limit=HTML_LIMIT)
    record: dict[str, object] = {
        "url": url,
        "finalUrl": result.final_url,
        "status": result.status,
        "contentType": result.content_type,
        "elapsedMs": result.elapsed_ms,
        "error": result.error,
        "sameOriginFinal": (
            same_origin(result.final_url, origin) if result.final_url else False
        ),
    }
    if result.status == 200 and result.content_type in SUPPORTED_HTML_TYPES:
        signals = parse_page_signals(result)
        record.update(
            {
                "title": signals.title,
                "canonical": signals.canonical,
                "canonicalMatches": (
                    normalize_url(signals.canonical) == normalize_url(url)
                    if signals.canonical
                    else False
                ),
                "noindex": signals.noindex,
                "robots": list(signals.robots),
                "hreflang": [
                    {"language": language, "url": href}
                    for language, href in signals.hreflang
                ],
            }
        )
    return record


def severity_summary(
    *,
    origin: str,
    robots_result: FetchResult,
    robots_maps: list[str],
    sitemap_reports: dict[str, dict[str, object]],
    sitemap_errors: list[str],
    duplicates: dict[str, int],
    pages: list[dict[str, object]],
    truncated: bool,
) -> tuple[list[str], list[str], list[str]]:
    critical: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    if robots_result.status != 200:
        critical.append(
            f"robots.txt returned {robots_result.status or 'network error'}"
        )
    if not robots_maps:
        critical.append("robots.txt does not declare a sitemap")
    if sitemap_errors:
        critical.extend(sitemap_errors)
    if not sitemap_reports:
        critical.append("No sitemap could be loaded")
    if duplicates:
        warnings.append(
            f"{len(duplicates)} duplicated URL values appear across sitemaps"
        )

    for page in pages:
        url = str(page["url"])
        status = int(page.get("status") or 0)
        content_type = str(page.get("contentType") or "")
        if status != 200:
            critical.append(
                f"Sitemap URL returned {status or 'network error'}: {url}"
            )
            continue
        if content_type not in SUPPORTED_HTML_TYPES:
            warnings.append(
                f"Sitemap URL is not HTML ({content_type or 'unknown'}): {url}"
            )
            continue
        if bool(page.get("noindex")):
            critical.append(f"Sitemap URL is noindex: {url}")
        canonical = str(page.get("canonical") or "")
        if not canonical:
            warnings.append(f"Missing canonical: {url}")
        elif not bool(page.get("canonicalMatches")):
            warnings.append(f"Canonical mismatch: {url} -> {canonical}")
        if not bool(page.get("sameOriginFinal")):
            critical.append(
                f"URL redirects outside canonical origin: {url}"
            )

    if truncated:
        warnings.append("URL audit was truncated by --max-urls")
    notes.append(f"Canonical origin: {origin}")
    return critical, warnings, notes


def markdown_report(report: dict[str, object]) -> str:
    summary = report["summary"]
    lines = [
        "# Live search-discovery audit",
        "",
        f"- Generated: `{report['generatedAt']}`",
        f"- Origin: `{report['origin']}`",
        f"- Status: **{summary['status']}**",
        f"- Sitemaps fetched: **{summary['sitemapsFetched']}**",
        (
            "- Unique sitemap URLs discovered: "
            f"**{summary['uniqueSitemapUrls']}**"
        ),
        f"- URLs audited: **{summary['urlsAudited']}**",
        f"- Critical findings: **{summary['criticalCount']}**",
        f"- Warnings: **{summary['warningCount']}**",
        "",
    ]
    for title, key in (
        ("Critical findings", "critical"),
        ("Warnings", "warnings"),
        ("Notes", "notes"),
    ):
        lines.extend((f"## {title}", ""))
        values = report["findings"][key]
        if values:
            lines.extend(f"- {value}" for value in values)
        else:
            lines.append("- None")
        lines.append("")
    lines.extend(
        (
            "## Safety",
            "",
            (
                "This audit is read-only. It does not modify DNS, hosting, "
                "robots.txt, sitemaps, pages, Search Console, Bing Webmaster "
                "Tools, or IndexNow."
            ),
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://healthrenewal.org/")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/live-search-discovery-v1.json"),
    )
    parser.add_argument(
        "--output-markdown",
        type=Path,
        default=Path("reports/live-search-discovery-v1.md"),
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--max-urls", type=int, default=5000)
    parser.add_argument(
        "--max-sitemap-depth",
        type=int,
        default=MAX_SITEMAP_DEPTH,
    )
    parser.add_argument("--strict-warnings", action="store_true")
    args = parser.parse_args()

    origin = normalize_url(args.base_url)
    robots_url = urllib.parse.urljoin(origin, "/robots.txt")
    robots_result = request_url(
        robots_url,
        timeout=args.timeout,
        limit=HTML_LIMIT,
    )
    robots_text = decode_body(robots_result)
    declared = robots_sitemaps(robots_text, origin)
    fallback = [
        urllib.parse.urljoin(origin, "/sitemap-index.xml"),
        urllib.parse.urljoin(origin, "/sitemap.xml"),
    ]
    seeds = declared or fallback

    sitemap_reports, discovered, sitemap_errors = discover_sitemaps(
        seeds,
        origin=origin,
        timeout=args.timeout,
        max_depth=args.max_sitemap_depth,
    )
    counts = Counter(discovered)
    duplicates = {
        url: count for url, count in counts.items() if count > 1
    }
    unique_urls = sorted(counts)
    truncated = len(unique_urls) > args.max_urls
    audit_urls = unique_urls[: args.max_urls]

    pages: list[dict[str, object]] = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, args.workers)
    ) as executor:
        futures = {
            executor.submit(
                audit_page,
                url,
                origin=origin,
                timeout=args.timeout,
            ): url
            for url in audit_urls
        }
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            try:
                pages.append(future.result())
            except Exception as exc:
                pages.append(
                    {
                        "url": url,
                        "finalUrl": url,
                        "status": 0,
                        "contentType": "",
                        "elapsedMs": 0,
                        "error": f"{type(exc).__name__}: {exc}",
                        "sameOriginFinal": False,
                    }
                )
    pages.sort(key=lambda item: str(item["url"]))

    critical, warnings, notes = severity_summary(
        origin=origin,
        robots_result=robots_result,
        robots_maps=declared,
        sitemap_reports=sitemap_reports,
        sitemap_errors=sitemap_errors,
        duplicates=duplicates,
        pages=pages,
        truncated=truncated,
    )
    status = (
        "failed"
        if critical or (args.strict_warnings and warnings)
        else "passed"
    )
    report: dict[str, object] = {
        "schemaVersion": 1,
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "origin": origin,
        "readOnly": True,
        "summary": {
            "status": status,
            "robotsStatus": robots_result.status,
            "robotsDeclaredSitemaps": len(declared),
            "sitemapsFetched": len(sitemap_reports),
            "rawSitemapUrlEntries": len(discovered),
            "uniqueSitemapUrls": len(unique_urls),
            "duplicateSitemapUrls": len(duplicates),
            "urlsAudited": len(pages),
            "truncated": truncated,
            "criticalCount": len(critical),
            "warningCount": len(warnings),
        },
        "robots": {
            "url": robots_url,
            "finalUrl": robots_result.final_url,
            "status": robots_result.status,
            "contentType": robots_result.content_type,
            "elapsedMs": robots_result.elapsed_ms,
            "error": robots_result.error,
            "declaredSitemaps": declared,
        },
        "sitemaps": sitemap_reports,
        "duplicates": duplicates,
        "pages": pages,
        "findings": {
            "critical": critical,
            "warnings": warnings,
            "notes": notes,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_markdown.write_text(
        markdown_report(report),
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
