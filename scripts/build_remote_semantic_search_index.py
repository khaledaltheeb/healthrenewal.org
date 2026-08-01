#!/usr/bin/env python3
"""Build and verify the semantic index from the fully published static website.

The wrapper discovers every HTML URL exposed through the sitemap index,
downloads those pages plus approved structured-data sidecars used by
JavaScript-rendered condition pages, delegates chunking/embedding/sharding to
build_semantic_search_index.py, and fails closed unless the published corpus is
fully represented.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

import build_semantic_search_index as local_builder

DEFAULT_SITEMAP = "https://healthrenewal.org/sitemap-index.xml"
DEFAULT_BASE_URL = "https://healthrenewal.org/"
LEGACY_BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
USER_AGENT = "HealthRenewalSemanticIndexer/4.0 (+https://healthrenewal.org/ai-search/)"
XML_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
SKIPPED_SUFFIXES = {
    ".xml", ".json", ".csv", ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".svg", ".ico", ".mp3", ".mp4", ".webm", ".css", ".js", ".txt", ".webmanifest",
}


def fetch_bytes(url: str, timeout: int, attempts: int = 5) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/javascript,application/xml;q=0.9,*/*;q=0.6",
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
                time.sleep(min(8, attempt * 1.5))
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


def normalize_site_url(url: str, base_url: str) -> str:
    candidate = urlparse(url)
    base = urlparse(base_url)
    legacy = urlparse(LEGACY_BASE_URL)

    if candidate.netloc == legacy.netloc and candidate.path.startswith(legacy.path):
        suffix = candidate.path[len(legacy.path):]
        target_path = f"{base.path.rstrip('/')}/{suffix.lstrip('/')}"
        candidate = candidate._replace(
            scheme=base.scheme,
            netloc=base.netloc,
            path=target_path,
            query="",
            fragment="",
        )
    elif candidate.netloc == "www.healthrenewal.org":
        candidate = candidate._replace(
            scheme="https",
            netloc="healthrenewal.org",
            query="",
            fragment="",
        )
    else:
        candidate = candidate._replace(fragment="")
    return candidate.geturl()


def normalized_asset_url(url: str, base_url: str) -> str:
    parsed = urlparse(normalize_site_url(url, base_url))
    return parsed._replace(query="", fragment="").geturl()


def same_site(url: str, base_url: str) -> bool:
    candidate = urlparse(normalize_site_url(url, base_url))
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


def is_index_data_asset(url: str, base_url: str) -> bool:
    if not same_site(url, base_url):
        return False
    basename = PurePosixPath(urlparse(url).path).name.lower()
    return basename == "data.js" or basename.startswith("conditions-data")


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
            for raw_location in locations:
                location = normalize_site_url(raw_location, base_url)
                if same_site(location, base_url) and location not in seen_sitemaps:
                    queue.append(location)
            continue

        if root_type != "urlset":
            raise RuntimeError(f"Unsupported sitemap root {root_type!r} at {current}")

        for raw_location in locations:
            location = normalize_site_url(raw_location, base_url)
            if not is_indexable_page_url(location, base_url) or location in seen_pages:
                continue
            seen_pages.add(location)
            pages.append(location)
            if len(pages) >= max_pages:
                print(f"Reached page safety limit: {max_pages:,}", flush=True)
                return pages

    return pages


def destination_for_url(root: Path, url: str, base_url: str) -> Path:
    parsed = urlparse(normalize_site_url(url, base_url))
    base_path = urlparse(base_url).path
    relative = unquote(parsed.path[len(base_path):]).lstrip("/")
    pure = PurePosixPath(relative)
    safe_parts = [part for part in pure.parts if part not in {"", ".", ".."}]

    if not safe_parts:
        safe_parts = ["index.html"]
    elif PurePosixPath(*safe_parts).suffix.lower() not in {".html", ".htm"}:
        safe_parts.append("index.html")

    return root.joinpath(*safe_parts)


def destination_for_asset(root: Path, url: str, base_url: str) -> Path:
    parsed = urlparse(normalized_asset_url(url, base_url))
    base_path = urlparse(base_url).path
    relative = unquote(parsed.path[len(base_path):]).lstrip("/")
    pure = PurePosixPath(relative)
    safe_parts = [part for part in pure.parts if part not in {"", ".", ".."}]
    if not safe_parts or not PurePosixPath(*safe_parts).suffix:
        raise ValueError(f"Data asset has no safe filename: {url}")
    return root.joinpath(*safe_parts)


def download_page(url: str, destination: Path, timeout: int) -> tuple[str, bool, str]:
    try:
        data = fetch_bytes(url, timeout=timeout)
        prefix = data[:1000].lower()
        if b"<html" not in prefix and b"<!doctype html" not in prefix:
            return url, False, "response is not HTML"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return url, True, ""
    except Exception as exc:
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


def discover_index_data_assets(
    page_urls: list[str],
    root: Path,
    base_url: str,
) -> list[str]:
    assets: set[str] = set()
    for page_url in page_urls:
        page_path = destination_for_url(root, page_url, base_url)
        if not page_path.is_file():
            continue
        soup = BeautifulSoup(page_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        for script in soup.find_all("script", src=True):
            src = str(script.get("src") or "").strip()
            if not src:
                continue
            asset_url = normalized_asset_url(urljoin(page_url, src), base_url)
            if is_index_data_asset(asset_url, base_url):
                assets.add(asset_url)
    return sorted(assets)


def download_data_asset(
    url: str,
    destination: Path,
    timeout: int,
) -> tuple[str, bool, str]:
    try:
        data = fetch_bytes(url, timeout=timeout)
        if not data.strip():
            return url, False, "empty data asset"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return url, True, ""
    except Exception as exc:
        return url, False, str(exc)


def mirror_index_data_assets(
    asset_urls: list[str],
    root: Path,
    base_url: str,
    timeout: int,
    workers: int,
) -> tuple[int, list[tuple[str, str]]]:
    failures: list[tuple[str, str]] = []
    successes = 0
    if not asset_urls:
        return successes, failures

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                download_data_asset,
                url,
                destination_for_asset(root, url, base_url),
                timeout,
            ): url
            for url in asset_urls
        }
        total = len(futures)
        for completed, future in enumerate(as_completed(futures), start=1):
            url, ok, error = future.result()
            if ok:
                successes += 1
            else:
                failures.append((url, error))
            if completed % 50 == 0 or completed == total:
                print(
                    f"Downloaded {completed:,}/{total:,} structured data assets "
                    f"({successes:,} successful)",
                    flush=True,
                )
    return successes, failures


def indexed_source_paths(output: Path, manifest: dict[str, object]) -> set[str]:
    paths: set[str] = set()
    shards = manifest.get("shards")
    if not isinstance(shards, list):
        raise RuntimeError("Generated manifest has no shard list")
    for shard in shards:
        if not isinstance(shard, dict) or not shard.get("metadata"):
            raise RuntimeError("Generated manifest contains an invalid shard")
        payload = json.loads((output / str(shard["metadata"])).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise RuntimeError(f"Invalid metadata payload: {shard['metadata']}")
        for chunk in payload:
            if isinstance(chunk, dict) and chunk.get("sourcePath"):
                paths.add(str(chunk["sourcePath"]))
    return paths


def write_coverage_report(
    args: argparse.Namespace,
    urls: list[str],
    mirror_root: Path,
    successes: int,
    failures: list[tuple[str, str]],
    data_asset_urls: list[str],
    data_asset_successes: int,
    data_asset_failures: list[tuple[str, str]],
    manifest: dict[str, object],
) -> dict[str, object]:
    output = args.output.resolve()
    expected_paths: dict[str, list[str]] = {}
    for url in urls:
        path = destination_for_url(mirror_root, url, args.base_url).relative_to(mirror_root).as_posix()
        expected_paths.setdefault(path, []).append(url)

    collisions = {path: values for path, values in expected_paths.items() if len(values) > 1}
    indexed_paths = indexed_source_paths(output, manifest)
    failed_urls = {url for url, _ in failures}
    indexed_urls = [
        url
        for path, path_urls in expected_paths.items()
        if path in indexed_paths
        for url in path_urls
    ]
    unindexed_urls = [
        url
        for path, path_urls in expected_paths.items()
        if path not in indexed_paths
        for url in path_urls
    ]
    unexpected_paths = sorted(indexed_paths.difference(expected_paths))
    discovered_count = len(urls)
    download_ratio = successes / max(1, discovered_count)
    index_ratio = len(indexed_urls) / max(1, discovered_count)
    passed = (
        download_ratio >= args.minimum_success_ratio
        and index_ratio >= args.minimum_indexed_ratio
        and not data_asset_failures
        and not collisions
        and not unexpected_paths
    )

    report: dict[str, object] = {
        "version": 2,
        "passed": passed,
        "generatedAt": manifest["generatedAt"],
        "model": manifest["model"],
        "modelRevision": manifest["modelRevision"],
        "sitemapUrl": args.sitemap_url,
        "baseUrl": args.base_url,
        "discoveredUrlCount": discovered_count,
        "downloadedPageCount": successes,
        "failedDownloadCount": len(failures),
        "dataAssetCount": len(data_asset_urls),
        "downloadedDataAssetCount": data_asset_successes,
        "failedDataAssetCount": len(data_asset_failures),
        "indexedUrlCount": len(indexed_urls),
        "indexedDocumentCount": manifest["documentCount"],
        "chunkCount": manifest["chunkCount"],
        "downloadSuccessRatio": download_ratio,
        "indexCoverageRatio": index_ratio,
        "requiredDownloadSuccessRatio": args.minimum_success_ratio,
        "requiredIndexCoverageRatio": args.minimum_indexed_ratio,
        "failedDownloads": [{"url": url, "error": error} for url, error in failures],
        "failedDataAssets": [{"url": url, "error": error} for url, error in data_asset_failures],
        "unindexedUrls": unindexed_urls,
        "destinationCollisions": collisions,
        "unexpectedIndexedPaths": unexpected_paths,
        "failedUrlsIndexedUnexpectedly": sorted(failed_urls.intersection(indexed_urls)),
    }
    local_builder.write_json(output / "coverage.json", report)

    manifest["coverage"] = {
        "passed": passed,
        "report": "coverage.json",
        "discoveredUrlCount": discovered_count,
        "downloadedPageCount": successes,
        "dataAssetCount": len(data_asset_urls),
        "downloadedDataAssetCount": data_asset_successes,
        "indexedUrlCount": len(indexed_urls),
        "downloadSuccessRatio": download_ratio,
        "indexCoverageRatio": index_ratio,
    }
    local_builder.write_json(output / "manifest.json", manifest)
    return report


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sitemap-url", default=DEFAULT_SITEMAP)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", type=Path, default=Path("ai-search/data"))
    parser.add_argument("--max-pages", type=int, default=6000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--minimum-success-ratio", type=float, default=0.90)
    parser.add_argument("--minimum-indexed-ratio", type=float, default=0.90)
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
    if not 0.5 <= args.minimum_indexed_ratio <= 1:
        parser.error("--minimum-indexed-ratio must be between 0.5 and 1")
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

        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        for stale_name in ("crawl-failures.txt", "data-asset-failures.txt", "coverage.json"):
            stale = output / stale_name
            if stale.exists():
                stale.unlink()

        with TemporaryDirectory(prefix="healthrenewal-semantic-mirror-") as temp_directory:
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
                (output / "crawl-failures.txt").write_text(
                    "\n".join(f"{url}\t{error}" for url, error in failures),
                    encoding="utf-8",
                )

            data_asset_urls = discover_index_data_assets(urls, mirror_root, args.base_url)
            data_asset_successes, data_asset_failures = mirror_index_data_assets(
                asset_urls=data_asset_urls,
                root=mirror_root,
                base_url=args.base_url,
                timeout=args.timeout,
                workers=args.workers,
            )
            if data_asset_failures:
                (output / "data-asset-failures.txt").write_text(
                    "\n".join(f"{url}\t{error}" for url, error in data_asset_failures),
                    encoding="utf-8",
                )

            print(
                f"Mirrored {successes:,} pages and {data_asset_successes:,} structured data assets; "
                "building multilingual E5 index",
                flush=True,
            )
            manifest = local_builder.build_index(
                SimpleNamespace(
                    root=mirror_root,
                    output=output,
                    chunk_chars=args.chunk_chars,
                    overlap_chars=args.overlap_chars,
                    shard_size=args.shard_size,
                    batch_size=args.batch_size,
                )
            )
            coverage = write_coverage_report(
                args=args,
                urls=urls,
                mirror_root=mirror_root,
                successes=successes,
                failures=failures,
                data_asset_urls=data_asset_urls,
                data_asset_successes=data_asset_successes,
                data_asset_failures=data_asset_failures,
                manifest=manifest,
            )

        if not coverage["passed"]:
            examples = ", ".join(coverage["unindexedUrls"][:5])
            raise RuntimeError(
                "Semantic index coverage gate failed: "
                f"download={coverage['downloadSuccessRatio']:.2%}, "
                f"data-assets={coverage['downloadedDataAssetCount']}/{coverage['dataAssetCount']}, "
                f"indexed={coverage['indexCoverageRatio']:.2%}, "
                f"unindexed examples={examples or 'none'}"
            )

        print(
            f"Remote semantic index complete: {manifest['documentCount']:,} pages, "
            f"{manifest['chunkCount']:,} chunks, {len(manifest['shards'])} shards, "
            f"data-assets={coverage['downloadedDataAssetCount']:,}, "
            f"coverage={coverage['indexCoverageRatio']:.2%}",
            flush=True,
        )
        return 0
    except Exception as exc:
        print(f"remote semantic-index build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())