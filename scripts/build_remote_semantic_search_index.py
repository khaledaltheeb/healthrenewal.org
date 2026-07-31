#!/usr/bin/env python3
"""Build the semantic index from the fully published static website.

The repository generates many public pages during its release pipeline. This
wrapper discovers every HTML URL exposed through the sitemap index, downloads
those pages into a temporary mirror, and delegates chunking/embedding/sharding
to build_semantic_search_index.py. It therefore indexes the deployed site rather
than only HTML files committed directly to git.
"""

from __future__ import annotations

import argparse
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import build_semantic_search_index as local_builder

DEFAULT_SITEMAP = "https://khaledaltheeb.github.io/pterminology-site/sitemap-index.xml"
DEFAULT_BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
USER_AGENT = "PterminologySemanticIndexer/1.0 (+https://khaledaltheeb.github.io/pterminology-site/ai-search/)"
XML_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
SKIPPED_SUFFIXES = {
    ".xml", ".json", ".csv", ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".svg", ".ico", ".mp3", ".mp4", ".webm", ".css", ".js", ".txt", ".webmanifest",
}


def fetch_bytes(url: str, timeout: int, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.6",
                "Accept-Encoding": "identity",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise RuntimeError(f"HTTP {status} for {url}")
                return response.read()
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(min(5, attempt * 1.5))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_sitemap(data: bytes) -> tuple[str, list[str]]:
    root = ET.fromstring(data)
    root_type = local_name(root.tag)
    locations = [
        (node.text or "").strip()
        for node in root.findall(".//sm:loc", XML_NAMESPACE)
        if (node.text or "").strip()
    ]
    if not locations:
        locations = [
            (node.text or "").strip()
            for node in root.iter()
            if local_name(node.tag) == "loc" and (node.text or "").strip()
        ]
    return root_type, locations


def same_site(url: str, base_url: str) -> bool:
    candidate = urlparse(url)
    base = urlparse(base_url)
    return (
        candidate.scheme in {"http", "https"}
        and candidate.netloc == base.netloc
        and candidate.path.startswith(base.path)
    )


def is_indexable_page_url(url: str, base_url: str) -> bool:
    if not same_site(url, base_url):
        return False
    parsed = urlparse(url)
    if parsed.query or parsed.fragment:
        return False
    suffix = PurePosixPath(parsed.path).suffix.lower()
    return suffix not in SKIPPED_SUFFIXES


def discover_page_urls(sitemap_url: str, base_url: str, timeout: int, max_pages: int) -> list[str]:
    queue = [sitemap_url]
    seen_sitemaps: set[str] = set()
    pages: list[str] = []
    seen_pages: set[str] = set()

    while queue:
        current = queue.pop(0)
        if current in seen_sitemaps:
            continue
        seen_sitemaps.add(current)
        print(f"Reading sitemap: {current}", flush=True)
        root_type, locations = parse_sitemap(fetch_bytes(current, timeout=timeout))

        if root_type == "sitemapindex":
            for location in locations:
                if same_site(location, base_url) and location not in seen_sitemaps:
                    queue.append(location)
            continue

        if root_type != "urlset":
            raise RuntimeError(f"Unsupported sitemap root {root_type!r} at {current}")

        for location in locations:
            if not is_indexable_page_url(location, base_url) or location in seen_pages:
                continue
            seen_pages.add(location)
            pages.append(location)
            if len(pages) >= max_pages:
                print(f"Reached page safety limit: {max_pages:,}", flush=True)
                return pages

    return pages


def destination_for_url(root: Path, url: str, base_url: str) -> Path:
    parsed = urlparse(url)
    base_path = urlparse(base_url).path
    relative = unquote(parsed.path[len(base_path):]).lstrip("/")
    pure = PurePosixPath(relative)
    safe_parts = [part for part in pure.parts if part not in {"", ".", ".."}]

    if not safe_parts:
        safe_parts = ["index.html"]
    elif PurePosixPath(*safe_parts).suffix.lower() not in {".html", ".htm"}:
        safe_parts.append("index.html")

    return root.joinpath(*safe_parts)


def download_page(url: str, destination: Path, timeout: int) -> tuple[str, bool, str]:
    try:
        data = fetch_bytes(url, timeout=timeout)
        prefix = data[:500].lower()
        if b"<html" not in prefix and b"<!doctype html" not in prefix:
            return url, False, "response is not HTML"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return url, True, ""
    except Exception as exc:  # isolated page failures must not abort the whole index
        return url, False, str(exc)


def mirror_pages(
    urls: list[str],
    root: Path,
    base_url: str,
    timeout: int,
    workers: int,
    minimum_success_ratio: float,
) -> tuple[int, list[tuple[str, str]]]:
    failures: list[tuple[str, str]] = []
    successes = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                download_page,
                url,
                destination_for_url(root, url, base_url),
                timeout,
            ): url
            for url in urls
        }
        total = len(futures)
        for completed, future in enumerate(as_completed(futures), start=1):
            url, ok, error = future.result()
            if ok:
                successes += 1
            else:
                failures.append((url, error))
            if completed % 100 == 0 or completed == total:
                print(f"Downloaded {completed:,}/{total:,} pages ({successes:,} successful)", flush=True)

    ratio = successes / max(1, len(urls))
    if ratio < minimum_success_ratio:
        examples = "; ".join(f"{url}: {error}" for url, error in failures[:5])
        raise RuntimeError(
            f"Only {successes:,}/{len(urls):,} sitemap pages downloaded "
            f"({ratio:.1%}); examples: {examples}"
        )
    return successes, failures


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sitemap-url", default=DEFAULT_SITEMAP)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", type=Path, default=Path("ai-search/data"))
    parser.add_argument("--max-pages", type=int, default=6000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--minimum-success-ratio", type=float, default=0.90)
    parser.add_argument("--chunk-chars", type=int, default=local_builder.DEFAULT_CHUNK_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=local_builder.DEFAULT_OVERLAP_CHARS)
    parser.add_argument("--shard-size", type=int, default=local_builder.DEFAULT_SHARD_SIZE)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args(argv)

    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    if not 1 <= args.max_pages <= 10000:
        parser.error("--max-pages must be between 1 and 10000")
    if not 0.5 <= args.minimum_success_ratio <= 1:
        parser.error("--minimum-success-ratio must be between 0.5 and 1")
    if not same_site(args.sitemap_url, args.base_url):
        parser.error("--sitemap-url must be under --base-url host and path")
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        urls = discover_page_urls(
            sitemap_url=args.sitemap_url,
            base_url=args.base_url,
            timeout=args.timeout,
            max_pages=args.max_pages,
        )
        if not urls:
            raise RuntimeError("No indexable page URLs were discovered from the sitemap")
        print(f"Discovered {len(urls):,} public page URLs", flush=True)

        with TemporaryDirectory(prefix="pterminology-semantic-mirror-") as temp_directory:
            mirror_root = Path(temp_directory)
            successes, failures = mirror_pages(
                urls=urls,
                root=mirror_root,
                base_url=args.base_url,
                timeout=args.timeout,
                workers=args.workers,
                minimum_success_ratio=args.minimum_success_ratio,
            )
            if failures:
                report_path = args.output.resolve() / "crawl-failures.txt"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    "\n".join(f"{url}\t{error}" for url, error in failures),
                    encoding="utf-8",
                )
            print(f"Mirrored {successes:,} pages; building multilingual E5 index", flush=True)
            manifest = local_builder.build_index(
                SimpleNamespace(
                    root=mirror_root,
                    output=args.output,
                    chunk_chars=args.chunk_chars,
                    overlap_chars=args.overlap_chars,
                    shard_size=args.shard_size,
                    batch_size=args.batch_size,
                )
            )

        print(
            f"Remote semantic index complete: {manifest['documentCount']:,} pages, "
            f"{manifest['chunkCount']:,} chunks, {len(manifest['shards'])} shards",
            flush=True,
        )
        return 0
    except Exception as exc:
        print(f"remote semantic-index build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
