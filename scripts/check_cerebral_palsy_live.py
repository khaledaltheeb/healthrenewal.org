#!/usr/bin/env python3
"""Verify the published cerebral palsy archive without rebuilding other archives."""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

BASE_URL = "https://healthrenewal.org"
ARCHIVE_PATH = "/special-needs/conditions/cerebral-palsy/"
PAGE_PATHS = (
    ARCHIVE_PATH,
    ARCHIVE_PATH + "detection-diagnosis/",
    ARCHIVE_PATH + "movement-rehabilitation/",
    ARCHIVE_PATH + "health-lifespan/",
    ARCHIVE_PATH + "communication-education/",
    ARCHIVE_PATH + "family-adulthood/",
)
SITEMAP_PATH = "/sitemap-cerebral-palsy.xml"
SITEMAP_INDEX_PATH = "/sitemap-index.xml"
USER_AGENT = "Rawafid-Cerebral-Palsy-Live-Gate/1.0 (+https://healthrenewal.org/)"
PLACEHOLDER_PATTERNS = (
    r"\bTODO\b",
    r"lorem\s+ipsum",
    r"صفحة\s+قيد\s+الإنشاء",
)


@dataclass(frozen=True)
class Response:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    body: bytes


def canonical_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def normalized_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    if not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path += "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def fetch(url: str, timeout: float) -> Response:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xml,text/xml;q=0.9,*/*;q=0.8",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as result:
        return Response(
            requested_url=url,
            final_url=result.geturl(),
            status=result.status,
            content_type=result.headers.get("Content-Type", ""),
            body=result.read(),
        )


def xml_locations(payload: bytes, container: str) -> set[str]:
    root = ET.fromstring(payload)
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {
        node.text.strip()
        for node in root.findall(f"s:{container}/s:loc", namespace)
        if node.text and node.text.strip()
    }


def validate_html(response: Response, expected_url: str, minimum_length: int) -> list[str]:
    errors: list[str] = []
    text = response.body.decode("utf-8", errors="replace")

    if response.status != 200:
        errors.append(f"{expected_url}: HTTP {response.status}")
    if normalized_url(response.final_url) != normalized_url(expected_url):
        errors.append(f"{expected_url}: redirected to {response.final_url}")
    if "text/html" not in response.content_type.lower():
        errors.append(f"{expected_url}: unexpected content type {response.content_type!r}")
    if len(text) < minimum_length:
        errors.append(f"{expected_url}: body too short ({len(text)} chars)")
    if not re.search(r"<html\b[^>]*\blang=[\"']ar[\"']", text, re.IGNORECASE):
        errors.append(f"{expected_url}: missing Arabic document language")
    if not re.search(r"<html\b[^>]*\bdir=[\"']rtl[\"']", text, re.IGNORECASE):
        errors.append(f"{expected_url}: missing RTL direction")
    if len(re.findall(r"<h1\b", text, re.IGNORECASE)) != 1:
        errors.append(f"{expected_url}: expected exactly one H1")
    if "الشلل الدماغي" not in text:
        errors.append(f"{expected_url}: archive subject marker missing")
    canonical = f'<link rel="canonical" href="{expected_url}">'
    if canonical not in text:
        errors.append(f"{expected_url}: canonical URL mismatch")
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            errors.append(f"{expected_url}: placeholder content matched {pattern!r}")
    return errors


def validate_once(base_url: str, timeout: float) -> list[str]:
    errors: list[str] = []
    expected_pages = {canonical_url(base_url, path) for path in PAGE_PATHS}

    for index, path in enumerate(PAGE_PATHS):
        expected_url = canonical_url(base_url, path)
        minimum_length = 9000 if index == 0 else 6500
        try:
            response = fetch(expected_url, timeout)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(f"{expected_url}: fetch failed: {exc}")
            continue
        errors.extend(validate_html(response, expected_url, minimum_length))

    sitemap_url = canonical_url(base_url, SITEMAP_PATH)
    try:
        sitemap = fetch(sitemap_url, timeout)
        if sitemap.status != 200:
            errors.append(f"{sitemap_url}: HTTP {sitemap.status}")
        locations = xml_locations(sitemap.body, "url")
        if locations != expected_pages:
            missing = sorted(expected_pages - locations)
            extra = sorted(locations - expected_pages)
            errors.append(f"{sitemap_url}: URL mismatch; missing={missing}, extra={extra}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
        errors.append(f"{sitemap_url}: validation failed: {exc}")

    sitemap_index_url = canonical_url(base_url, SITEMAP_INDEX_PATH)
    try:
        sitemap_index = fetch(sitemap_index_url, timeout)
        if sitemap_index.status != 200:
            errors.append(f"{sitemap_index_url}: HTTP {sitemap_index.status}")
        indexed_sitemaps = xml_locations(sitemap_index.body, "sitemap")
        if sitemap_url not in indexed_sitemaps:
            errors.append(f"{sitemap_index_url}: missing {sitemap_url}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
        errors.append(f"{sitemap_index_url}: validation failed: {exc}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.attempts < 1:
        raise SystemExit("--attempts must be at least 1")
    if args.delay < 0 or args.timeout <= 0:
        raise SystemExit("--delay must be non-negative and --timeout must be positive")

    last_errors: list[str] = []
    for attempt in range(1, args.attempts + 1):
        last_errors = validate_once(args.base_url, args.timeout)
        if not last_errors:
            print(
                "Cerebral palsy archive is live: six pages, archive sitemap, "
                "and sitemap index all passed."
            )
            return 0

        print(f"Attempt {attempt}/{args.attempts} failed:", file=sys.stderr)
        for error in last_errors:
            print(f"- {error}", file=sys.stderr)
        if attempt < args.attempts and args.delay:
            time.sleep(args.delay)

    print(f"Live archive gate failed with {len(last_errors)} issue(s).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
