#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
VERIFY = "google644f1f7a8b7aaa2b.html"
BASE_URL = "https://healthrenewal.org/"
LEGACY_BASE_URLS = (
    "https://healthrenewal.org/",
    "https://healthrenewal.org/",
)
MANIFEST_HREF = "/manifest.webmanifest"
THEME_COLOR = "#0b6b66"

CANONICAL_TAG_RE = re.compile(
    r"\s*<link\b(?=[^>]*\brel\s*=\s*([\"'])[^\"']*\bcanonical\b[^\"']*\1)[^>]*>\s*",
    re.IGNORECASE,
)
OG_URL_TAG_RE = re.compile(
    r"\s*<meta\b(?=[^>]*\bproperty\s*=\s*([\"'])og:url\1)[^>]*>\s*",
    re.IGNORECASE,
)
MANIFEST_TAG_RE = re.compile(
    r"\s*<link\b(?=[^>]*\brel\s*=\s*([\"'])[^\"']*\bmanifest\b[^\"']*\1)[^>]*>\s*",
    re.IGNORECASE,
)
TWITTER_CARD_TAG_RE = re.compile(
    r"\s*<meta\b(?=[^>]*\bname\s*=\s*([\"'])twitter:card\1)[^>]*>\s*",
    re.IGNORECASE,
)
THEME_COLOR_TAG_RE = re.compile(
    r"\s*<meta\b(?=[^>]*\bname\s*=\s*([\"'])theme-color\1)[^>]*>\s*",
    re.IGNORECASE,
)


@dataclass
class MetadataState:
    manifest: bool = False
    twitter_card: bool = False
    theme_color: bool = False
    og_url: bool = False
    og_url_value: str = ""
    canonical: str = ""


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.state = MetadataState()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs}
        if tag.lower() == "link":
            rels = str(values.get("rel") or "").lower().split()
            href = str(values.get("href") or "").strip()
            if "manifest" in rels:
                self.state.manifest = True
            if "canonical" in rels and href:
                self.state.canonical = html.unescape(href)
        elif tag.lower() == "meta":
            name = str(values.get("name") or "").lower()
            prop = str(values.get("property") or "").lower()
            if name == "twitter:card":
                self.state.twitter_card = True
            if name == "theme-color":
                self.state.theme_color = True
            if prop == "og:url":
                self.state.og_url = True
                self.state.og_url_value = html.unescape(str(values.get("content") or "").strip())


def parse_metadata(text: str) -> MetadataState:
    parser = MetadataParser()
    parser.feed(text)
    return parser.state


def inject_before_head_close(text: str, payload: str) -> str:
    replacement = "\n" + payload.strip() + "\n</head>"
    updated, count = re.subn(r"\s*</head\s*>", replacement, text, count=1, flags=re.I)
    if count != 1:
        raise ValueError("head_close_missing")
    return updated


def canonical_url_for(page: Path) -> str:
    relative = page.relative_to(SITE).as_posix()
    if relative == "index.html":
        return BASE_URL
    if relative.endswith("/index.html"):
        return BASE_URL + relative[: -len("index.html")]
    return BASE_URL + relative


def normalize_legacy_references(text: str) -> str:
    for legacy in LEGACY_BASE_URLS:
        text = text.replace(legacy, BASE_URL)
    text = text.replace("https://healthrenewal.org/", BASE_URL.rstrip("/"))
    text = text.replace("https://healthrenewal.org/", BASE_URL.rstrip("/"))
    text = text.replace("/", "/")
    text = text.replace("\\/\\/", "\\/")
    text = text.replace("https://healthrenewal.org//", BASE_URL)
    return text


def enrich_page(text: str, canonical_url: str) -> tuple[str, dict[str, int]]:
    text = normalize_legacy_references(text)
    for pattern in (
        CANONICAL_TAG_RE,
        MANIFEST_TAG_RE,
        OG_URL_TAG_RE,
        TWITTER_CARD_TAG_RE,
        THEME_COLOR_TAG_RE,
    ):
        text = pattern.sub("", text)

    additions = [
        f'<link rel="canonical" href="{html.escape(canonical_url, quote=True)}">',
        f'<link rel="manifest" href="{MANIFEST_HREF}">',
        f'<meta property="og:url" content="{html.escape(canonical_url, quote=True)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="theme-color" content="{THEME_COLOR}">',
    ]
    counters = {
        "canonical_normalized": 1,
        "manifest_normalized": 1,
        "og_url_normalized": 1,
        "twitter_card": 1,
        "theme_color": 1,
    }
    text = inject_before_head_close(text, "\n".join(additions))
    return text, counters


def verify_contract() -> None:
    sample = (
        '<!doctype html><html><head><link href="https://healthrenewal.org/page/" rel="canonical">'
        '<meta property="og:url" content="https://healthrenewal.org/page/">'
        '<title>Sample</title></head><body><a href="/library/">Library</a></body></html>'
    )
    expected = "https://healthrenewal.org/page/"
    enriched, counts = enrich_page(sample, expected)
    state = parse_metadata(enriched)
    if not all((state.manifest, state.twitter_card, state.theme_color, state.og_url)):
        raise SystemExit(f"Metadata enrichment contract failed: {state}")
    if state.canonical != expected or state.og_url_value != expected:
        raise SystemExit(f"Custom-domain canonical contract failed: {state}")
    if "/" in enriched or "khaledaltheeb.github.io/" in enriched:
        raise SystemExit("Legacy production base survived metadata normalization")
    if counts != {
        "canonical_normalized": 1,
        "manifest_normalized": 1,
        "og_url_normalized": 1,
        "twitter_card": 1,
        "theme_color": 1,
    }:
        raise SystemExit(f"Metadata counters contract failed: {counts}")
    second, _ = enrich_page(enriched, expected)
    if second != enriched:
        raise SystemExit("Metadata enrichment is not idempotent")


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing generated site: {SITE}")
    verify_contract()

    stats = {
        "version": 27,
        "status": "passed",
        "base_url": BASE_URL,
        "pages_scanned": 0,
        "pages_changed": 0,
        "verification_files_skipped": 0,
        "canonical_normalized": 0,
        "manifest_normalized": 0,
        "og_url_normalized": 0,
        "twitter_card_added": 0,
        "theme_color_added": 0,
        "legacy_base_occurrences_remaining": 0,
        "remaining_missing": {
            "manifest": [],
            "twitter_card": [],
            "theme_color": [],
            "og_url": [],
            "canonical": [],
        },
        "contract": {
            "base_url": BASE_URL,
            "manifest_href": MANIFEST_HREF,
            "theme_color": THEME_COLOR,
            "og_url_source": "canonical",
            "legacy_base_removed": True,
            "idempotent": True,
        },
    }
    failures: list[str] = []

    for page in sorted(SITE.rglob("*.html")):
        if page.name == VERIFY:
            stats["verification_files_skipped"] += 1
            continue
        relative = page.relative_to(SITE).as_posix()
        original = page.read_text(encoding="utf-8")
        stats["pages_scanned"] += 1
        expected_canonical = canonical_url_for(page)
        try:
            updated, additions = enrich_page(original, expected_canonical)
        except ValueError as error:
            failures.append(f"{relative}: {error}")
            continue
        if updated != original:
            page.write_text(updated, encoding="utf-8")
            stats["pages_changed"] += 1
        stats["canonical_normalized"] += additions["canonical_normalized"]
        stats["manifest_normalized"] += additions["manifest_normalized"]
        stats["og_url_normalized"] += additions["og_url_normalized"]
        stats["twitter_card_added"] += additions["twitter_card"]
        stats["theme_color_added"] += additions["theme_color"]

        final = parse_metadata(updated)
        for key, present in {
            "manifest": final.manifest,
            "twitter_card": final.twitter_card,
            "theme_color": final.theme_color,
            "og_url": final.og_url and final.og_url_value == expected_canonical,
            "canonical": final.canonical == expected_canonical,
        }.items():
            if not present:
                stats["remaining_missing"][key].append(relative)
        if "/" in updated or "khaledaltheeb.github.io/" in updated:
            stats["legacy_base_occurrences_remaining"] += 1
            failures.append(f"{relative}: legacy_base_remaining")

    remaining_count = sum(len(items) for items in stats["remaining_missing"].values())
    stats["remaining_missing_count"] = remaining_count
    stats["failure_count"] = len(failures)
    stats["failures"] = failures[:100]
    if failures or remaining_count:
        stats["status"] = "failed"

    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    report_path = api / "global-metadata-v27.json"
    report_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if stats["status"] != "passed":
        raise SystemExit(json.dumps({"failures": failures[:20], "remaining": stats["remaining_missing"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
