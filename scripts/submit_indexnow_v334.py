#!/usr/bin/env python3
"""Prepare IndexNow ownership proof and submit canonical production URLs.

The implementation is deterministic, standard-library only, recursively reads the
same sitemaps registered by robots.txt, filters URLs to the configured GitHub
Pages path, de-duplicates them, and submits batches of at most 10,000 URLs.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence
from urllib.parse import unquote, urlparse, urlunparse
from xml.etree import ElementTree as ET

VERSION = 334
DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")
MAX_URLS_PER_BATCH = 10_000


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {value!r}")
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if not path.endswith("/"):
        path += "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def canonical_url(value: str) -> str:
    parsed = urlparse(value.strip())
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def chunks(values: Sequence[str], size: int = MAX_URLS_PER_BATCH) -> Iterable[list[str]]:
    if size < 1 or size > MAX_URLS_PER_BATCH:
        raise ValueError(f"Batch size must be between 1 and {MAX_URLS_PER_BATCH}")
    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def robots_sitemaps(path: Path) -> list[str]:
    if not path.exists():
        return []
    result: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        name, value = (part.strip() for part in line.split(":", 1))
        if name.lower() == "sitemap" and value:
            result.append(value)
    return result


def local_path_for_url(site_root: Path, base_url: str, value: str) -> Path | None:
    parsed = urlparse(value)
    base = urlparse(base_url)
    if parsed.scheme and (parsed.scheme.lower() != base.scheme or parsed.netloc.lower() != base.netloc):
        return None
    path = parsed.path
    if parsed.scheme:
        if not path.startswith(base.path):
            return None
        path = path[len(base.path) :]
    candidate = (site_root / unquote(path.lstrip("/"))).resolve()
    try:
        candidate.relative_to(site_root.resolve())
    except ValueError:
        return None
    return candidate


def discover_urls(site_root: Path, base_url: str) -> tuple[list[str], list[str]]:
    """Return canonical URLs and non-fatal sitemap discovery warnings."""
    root = site_root.resolve()
    base_url = normalize_base_url(base_url)
    base = urlparse(base_url)
    warnings: list[str] = []
    entries = robots_sitemaps(root / "robots.txt")
    if not entries:
        preferred = root / "sitemap-index.xml"
        fallback = root / "sitemap.xml"
        if preferred.exists():
            entries = [base_url + preferred.name]
        elif fallback.exists():
            entries = [base_url + fallback.name]
        else:
            raise FileNotFoundError("No sitemap is registered in robots.txt and no sitemap file exists")

    visited: set[Path] = set()
    discovered: set[str] = set()

    def parse_sitemap(path: Path) -> None:
        if path in visited:
            return
        visited.add(path)
        if not path.exists():
            warnings.append(f"Missing sitemap: {path.relative_to(root) if path.is_relative_to(root) else path}")
            return
        try:
            xml_root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise ValueError(f"Invalid sitemap XML in {path}: {exc}") from exc
        kind = xml_root.tag.rsplit("}", 1)[-1]
        if kind == "sitemapindex":
            for loc in xml_root.findall(".//{*}loc"):
                if not loc.text:
                    continue
                child = local_path_for_url(root, base_url, loc.text.strip())
                if child is None:
                    warnings.append(f"Ignored external sitemap: {loc.text.strip()}")
                    continue
                parse_sitemap(child)
            return
        if kind != "urlset":
            raise ValueError(f"Unexpected sitemap root {kind!r} in {path}")
        for loc in xml_root.findall(".//{*}loc"):
            if not loc.text:
                continue
            value = canonical_url(loc.text.strip())
            parsed = urlparse(value)
            if parsed.scheme != base.scheme or parsed.netloc != base.netloc:
                warnings.append(f"Ignored external URL: {value}")
                continue
            if not parsed.path.startswith(base.path):
                warnings.append(f"Ignored URL outside base path: {value}")
                continue
            discovered.add(value)

    for entry in entries:
        local = local_path_for_url(root, base_url, entry)
        if local is None:
            warnings.append(f"Ignored external sitemap registration: {entry}")
            continue
        parse_sitemap(local)

    urls = sorted(discovered)
    if not urls:
        raise ValueError("Sitemap discovery returned zero submit-eligible URLs")
    return urls, warnings


@dataclass(slots=True)
class Submission:
    batch: int
    url_count: int
    status: int | None
    accepted: bool
    error: str = ""


@dataclass(slots=True)
class Report:
    version: int
    generated_at: str
    base_url: str
    endpoint: str
    key_location: str
    discovered_urls: int
    submitted_urls: int
    status: str
    warnings: list[str] = field(default_factory=list)
    submissions: list[Submission] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"


def prepare_key(site_root: Path, base_url: str, key: str) -> tuple[Path, str]:
    if not KEY_RE.fullmatch(key):
        raise ValueError("IndexNow key must contain 8-128 letters, numbers, or dashes")
    base_url = normalize_base_url(base_url)
    path = site_root / f"{key}.txt"
    path.write_text(key, encoding="utf-8")
    return path, base_url + path.name


def default_sender(endpoint: str, payload: bytes, timeout: int) -> int:
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "pterminology-indexnow-v334/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status)


def submit_urls(
    urls: Sequence[str],
    *,
    base_url: str,
    key: str,
    key_location: str,
    endpoint: str = DEFAULT_ENDPOINT,
    batch_size: int = MAX_URLS_PER_BATCH,
    timeout: int = 30,
    retries: int = 3,
    sender: Callable[[str, bytes, int], int] = default_sender,
) -> list[Submission]:
    base = urlparse(normalize_base_url(base_url))
    results: list[Submission] = []
    for batch_number, batch in enumerate(chunks(list(urls), batch_size), start=1):
        payload = json.dumps(
            {
                "host": base.netloc,
                "key": key,
                "keyLocation": key_location,
                "urlList": batch,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        last_error = ""
        last_status: int | None = None
        for attempt in range(1, retries + 1):
            try:
                status = sender(endpoint, payload, timeout)
                last_status = status
                if status in {200, 202}:
                    results.append(Submission(batch_number, len(batch), status, True))
                    break
                last_error = f"HTTP {status}"
                if status not in {429, 500, 502, 503, 504}:
                    break
            except urllib.error.HTTPError as exc:
                last_status = exc.code
                last_error = f"HTTP {exc.code}: {exc.reason}"
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
            if attempt < retries:
                time.sleep(min(2 ** (attempt - 1), 8))
        else:
            attempt = retries
        if not results or results[-1].batch != batch_number:
            results.append(Submission(batch_number, len(batch), last_status, False, last_error or "submission failed"))
    return results


def write_report(path: Path, report: Report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_json(), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_root", nargs="?", default="_site")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--batch-size", type=int, default=MAX_URLS_PER_BATCH)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--report", default="indexnow-submission-v334.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    site_root = Path(args.site_root).resolve()
    if not site_root.is_dir():
        raise SystemExit(f"Site root is not a directory: {site_root}")
    base_url = normalize_base_url(args.base_url)
    _, key_location = prepare_key(site_root, base_url, args.key)
    urls, warnings = discover_urls(site_root, base_url)
    submissions: list[Submission] = []
    if args.submit and not args.prepare_only:
        submissions = submit_urls(
            urls,
            base_url=base_url,
            key=args.key,
            key_location=key_location,
            endpoint=args.endpoint,
            batch_size=args.batch_size,
            timeout=args.timeout,
            retries=args.retries,
        )
    failed = [item for item in submissions if not item.accepted]
    report = Report(
        version=VERSION,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        base_url=base_url,
        endpoint=args.endpoint,
        key_location=key_location,
        discovered_urls=len(urls),
        submitted_urls=sum(item.url_count for item in submissions if item.accepted),
        status="failed" if failed else "prepared" if not submissions else "accepted",
        warnings=warnings,
        submissions=submissions,
    )
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = site_root / report_path
    write_report(report_path, report)
    print(report.to_json(), end="")
    return 0 if not failed or args.continue_on_error else 1


if __name__ == "__main__":
    raise SystemExit(main())
