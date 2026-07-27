#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from generate_sitemap_index_v304 import (
    BASE_URL,
    EXCLUDED_PARTS,
    FAMILY_PREFIX,
    INDEX_FILENAME,
    family_for,
    is_verification_artifact,
    normalized_url,
)

REPORT_FILENAME = "indexing-coverage-audit-v303.json"


class PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.robots: list[str] = []
        self.descriptions: list[str] = []
        self.canonicals: list[str] = []
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        values = {str(key).lower(): value or "" for key, value in attrs}
        if name == "title":
            self.in_title = True
        elif name == "h1":
            self.h1_count += 1
        elif name == "meta":
            meta_name = values.get("name", "").lower()
            if meta_name in {"robots", "googlebot"}:
                self.robots.append(values.get("content", ""))
            if meta_name == "description":
                self.descriptions.append(values.get("content", "").strip())
        elif name == "link":
            rel_tokens = {token.lower() for token in values.get("rel", "").split()}
            if "canonical" in rel_tokens:
                self.canonicals.append(values.get("href", "").strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()

    @property
    def noindex(self) -> bool:
        return "noindex" in " ".join(self.robots).lower()


def parse_page(path: Path) -> PageMetadataParser:
    parser = PageMetadataParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    return parser


def local_sitemap_path(root: Path, loc: str, base_url: str) -> Path | None:
    parsed = urlparse(loc)
    base = urlparse(base_url)
    prefix = base.path
    if parsed.scheme != base.scheme or parsed.netloc != base.netloc:
        return None
    if parsed.query or parsed.fragment or not parsed.path.startswith(prefix):
        return None
    relative = parsed.path.removeprefix(prefix)
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def parse_sitemap_index(
    root: Path, base_url: str
) -> tuple[set[str], list[str], list[str], list[str], dict[str, int]]:
    index_path = root / INDEX_FILENAME
    urls: set[str] = set()
    errors: list[str] = []
    referenced_files: list[str] = []
    duplicate_urls: list[str] = []
    family_counts: Counter[str] = Counter()

    if not index_path.exists():
        return urls, [f"{INDEX_FILENAME}: missing"], referenced_files, duplicate_urls, {}

    try:
        index_tree = ET.parse(index_path)
    except ET.ParseError as exc:
        return urls, [f"{INDEX_FILENAME}: invalid XML: {exc}"], referenced_files, duplicate_urls, {}

    if not index_tree.getroot().tag.endswith("sitemapindex"):
        errors.append(f"{INDEX_FILENAME}: root must be sitemapindex")

    seen_sitemap_urls: set[str] = set()
    for loc in index_tree.findall(".//{*}loc"):
        if not loc.text:
            continue
        sitemap_url = loc.text.strip()
        if sitemap_url in seen_sitemap_urls:
            errors.append(f"{INDEX_FILENAME}: duplicate sitemap reference: {sitemap_url}")
            continue
        seen_sitemap_urls.add(sitemap_url)
        sitemap_path = local_sitemap_path(root, sitemap_url, base_url)
        if sitemap_path is None:
            errors.append(f"{INDEX_FILENAME}: external or invalid sitemap URL: {sitemap_url}")
            continue
        if not sitemap_path.name.startswith(FAMILY_PREFIX):
            errors.append(f"{INDEX_FILENAME}: non-family sitemap referenced: {sitemap_path.name}")
        referenced_files.append(sitemap_path.name)
        if not sitemap_path.exists():
            errors.append(f"{sitemap_path.name}: referenced but missing")
            continue
        try:
            tree = ET.parse(sitemap_path)
        except ET.ParseError as exc:
            errors.append(f"{sitemap_path.name}: invalid XML: {exc}")
            continue
        if not tree.getroot().tag.endswith("urlset"):
            errors.append(f"{sitemap_path.name}: root must be urlset")
        family = sitemap_path.stem.removeprefix(FAMILY_PREFIX)
        for page_loc in tree.findall(".//{*}loc"):
            if not page_loc.text:
                continue
            page_url = page_loc.text.strip()
            parsed = urlparse(page_url)
            base = urlparse(base_url)
            if (
                parsed.scheme != base.scheme
                or parsed.netloc != base.netloc
                or parsed.query
                or parsed.fragment
                or not parsed.path.startswith(base.path)
            ):
                errors.append(f"{sitemap_path.name}: invalid page URL: {page_url}")
                continue
            if page_url in urls:
                duplicate_urls.append(page_url)
            urls.add(page_url)
            family_counts[family] += 1

    return (
        urls,
        errors,
        sorted(set(referenced_files)),
        sorted(set(duplicate_urls)),
        dict(sorted(family_counts.items())),
    )


def audit(
    root: Path,
    base_url: str = BASE_URL,
    *,
    enforce_metadata: bool = True,
) -> tuple[dict[str, object], bool]:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Site root not found: {root}")

    expected: set[str] = set()
    noindex: set[str] = set()
    canonical_missing: list[str] = []
    canonical_multiple: list[dict[str, object]] = []
    canonical_mismatch: list[dict[str, str]] = []
    title_missing: list[str] = []
    description_missing: list[str] = []
    h1_missing: list[str] = []
    h1_multiple: list[dict[str, object]] = []
    titles: Counter[str] = Counter()
    descriptions: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    skipped_verification = 0

    for page in sorted(root.rglob("*.html")):
        if any(part in EXCLUDED_PARTS for part in page.relative_to(root).parts):
            continue
        if is_verification_artifact(page, root):
            skipped_verification += 1
            continue
        parsed = parse_page(page)
        url = normalized_url(page, root, base_url)
        if parsed.noindex:
            noindex.add(url)
            continue
        expected.add(url)
        family_counts[family_for(url)] += 1

        canonicals = [value for value in parsed.canonicals if value]
        if not canonicals:
            canonical_missing.append(url)
        elif len(canonicals) != 1:
            canonical_multiple.append({"url": url, "canonicals": canonicals})
        elif canonicals[0].rstrip("/") != url.rstrip("/"):
            canonical_mismatch.append({"url": url, "canonical": canonicals[0]})

        if not parsed.title:
            title_missing.append(url)
        else:
            titles[parsed.title] += 1
        descriptions_found = [value for value in parsed.descriptions if value]
        if not descriptions_found:
            description_missing.append(url)
        else:
            descriptions[re.sub(r"\s+", " ", descriptions_found[0])] += 1
        if parsed.h1_count == 0:
            h1_missing.append(url)
        elif parsed.h1_count > 1:
            h1_multiple.append({"url": url, "count": parsed.h1_count})

    (
        sitemap_urls,
        sitemap_errors,
        referenced_sitemaps,
        duplicate_sitemap_urls,
        sitemap_family_counts,
    ) = parse_sitemap_index(root, base_url)
    missing_from_sitemaps = sorted(expected - sitemap_urls)
    stale_sitemap_urls = sorted(sitemap_urls - expected)

    robots_path = root / "robots.txt"
    directive = f"Sitemap: {base_url}{INDEX_FILENAME}"
    robots_text = robots_path.read_text(encoding="utf-8") if robots_path.is_file() else ""
    robots_index_registration_count = robots_text.count(directive)
    robots_errors = [] if robots_index_registration_count == 1 else [
        f"robots.txt must register {INDEX_FILENAME} exactly once; found={robots_index_registration_count}"
    ]

    duplicate_metadata = {
        "titles": sorted(
            ({"value": value, "count": count} for value, count in titles.items() if count > 1),
            key=lambda item: (-int(item["count"]), str(item["value"])),
        ),
        "descriptions": sorted(
            ({"value": value, "count": count} for value, count in descriptions.items() if count > 1),
            key=lambda item: (-int(item["count"]), str(item["value"])),
        ),
    }

    route_failures = (
        sitemap_errors
        or robots_errors
        or duplicate_sitemap_urls
        or missing_from_sitemaps
        or stale_sitemap_urls
    )
    metadata_failures = (
        canonical_missing
        or canonical_multiple
        or canonical_mismatch
        or title_missing
        or description_missing
        or h1_missing
    )
    critical_items = route_failures or (metadata_failures if enforce_metadata else [])
    status = "passed" if not critical_items else "failed"
    coverage = round(len(expected & sitemap_urls) / len(expected), 6) if expected else 1.0
    report: dict[str, object] = {
        "version": 305,
        "status": status,
        "mode": "full" if enforce_metadata else "routes-only",
        "metadata_gate_enforced": enforce_metadata,
        "base_url": base_url,
        "expected_indexable_pages": len(expected),
        "noindex_pages": len(noindex),
        "skipped_verification_files": skipped_verification,
        "sitemap_urls": len(sitemap_urls),
        "sitemap_coverage_ratio": coverage,
        "local_route_contract": "passed" if not route_failures else "failed",
        "metadata_contract": "passed" if not metadata_failures else "failed",
        "family_counts": dict(sorted(family_counts.items())),
        "sitemap_family_counts": sitemap_family_counts,
        "referenced_sitemaps": referenced_sitemaps,
        "missing_from_sitemaps": missing_from_sitemaps,
        "stale_or_noncanonical_sitemap_urls": stale_sitemap_urls,
        "duplicate_sitemap_urls": duplicate_sitemap_urls,
        "canonical_missing": canonical_missing,
        "canonical_multiple": canonical_multiple,
        "canonical_mismatch": canonical_mismatch,
        "title_missing": title_missing,
        "description_missing": description_missing,
        "h1_missing": h1_missing,
        "h1_multiple": h1_multiple,
        "duplicate_metadata": duplicate_metadata,
        "robots_index_registration_count": robots_index_registration_count,
        "robots_errors": robots_errors,
        "sitemap_errors": sitemap_errors,
    }

    out = root / "api" / REPORT_FILENAME
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, bool(critical_items)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument(
        "--routes-only",
        action="store_true",
        help="Enforce exact sitemap/local-route parity after discovery publishing without re-running the metadata gate.",
    )
    args = parser.parse_args()
    report, critical = audit(
        args.root,
        args.base_url.rstrip("/") + "/",
        enforce_metadata=not args.routes_only,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
