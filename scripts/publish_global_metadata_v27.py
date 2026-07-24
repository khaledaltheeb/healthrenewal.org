#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from publish_authorized_courses_v201 import publish as publish_authorized_courses
from publish_content_discovery_v201 import publish as publish_content_discovery


SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
VERIFY = "google644f1f7a8b7aaa2b.html"
MANIFEST_HREF = "/pterminology-site/manifest.webmanifest"
THEME_COLOR = "#0b6b66"


@dataclass
class MetadataState:
    manifest: bool = False
    twitter_card: bool = False
    theme_color: bool = False
    og_url: bool = False
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


def parse_metadata(text: str) -> MetadataState:
    parser = MetadataParser()
    parser.feed(text)
    return parser.state


def inject_before_head_close(text: str, payload: str) -> str:
    updated, count = re.subn(r"</head\s*>", payload + "</head>", text, count=1, flags=re.I)
    if count != 1:
        raise ValueError("head_close_missing")
    return updated


def enrich_page(text: str) -> tuple[str, dict[str, int]]:
    state = parse_metadata(text)
    additions: list[str] = []
    counters = {"manifest": 0, "twitter_card": 0, "theme_color": 0, "og_url": 0}

    if not state.manifest:
        additions.append(f'<link rel="manifest" href="{MANIFEST_HREF}">')
        counters["manifest"] = 1
    if not state.twitter_card:
        additions.append('<meta name="twitter:card" content="summary_large_image">')
        counters["twitter_card"] = 1
    if not state.theme_color:
        additions.append(f'<meta name="theme-color" content="{THEME_COLOR}">')
        counters["theme_color"] = 1
    if not state.og_url:
        if not state.canonical:
            raise ValueError("canonical_missing_for_og_url")
        additions.append(f'<meta property="og:url" content="{html.escape(state.canonical, quote=True)}">')
        counters["og_url"] = 1

    if additions:
        text = inject_before_head_close(text, "".join(additions))
    return text, counters


def verify_contract() -> None:
    sample = (
        '<!doctype html><html><head><link href="https://example.test/page/" rel="canonical">'
        '<title>Sample</title></head><body></body></html>'
    )
    enriched, counts = enrich_page(sample)
    state = parse_metadata(enriched)
    if not all((state.manifest, state.twitter_card, state.theme_color, state.og_url)):
        raise SystemExit(f"Metadata enrichment contract failed: {state}")
    if state.canonical != "https://example.test/page/":
        raise SystemExit(f"Canonical preservation failed: {state.canonical}")
    if counts != {"manifest": 1, "twitter_card": 1, "theme_color": 1, "og_url": 1}:
        raise SystemExit(f"Metadata counters contract failed: {counts}")
    second, second_counts = enrich_page(enriched)
    if second != enriched or any(second_counts.values()):
        raise SystemExit("Metadata enrichment is not idempotent")


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing generated site: {SITE}")
    verify_contract()

    stats = {
        "version": 27,
        "status": "passed",
        "pages_scanned": 0,
        "pages_changed": 0,
        "verification_files_skipped": 0,
        "manifest_added": 0,
        "twitter_card_added": 0,
        "theme_color_added": 0,
        "og_url_added": 0,
        "remaining_missing": {"manifest": [], "twitter_card": [], "theme_color": [], "og_url": []},
        "contract": {
            "manifest_href": MANIFEST_HREF,
            "theme_color": THEME_COLOR,
            "og_url_source": "canonical",
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
        try:
            updated, additions = enrich_page(original)
        except ValueError as error:
            failures.append(f"{relative}: {error}")
            continue
        if updated != original:
            page.write_text(updated, encoding="utf-8")
            stats["pages_changed"] += 1
        stats["manifest_added"] += additions["manifest"]
        stats["twitter_card_added"] += additions["twitter_card"]
        stats["theme_color_added"] += additions["theme_color"]
        stats["og_url_added"] += additions["og_url"]

        final = parse_metadata(updated)
        for key, present in {
            "manifest": final.manifest,
            "twitter_card": final.twitter_card,
            "theme_color": final.theme_color,
            "og_url": final.og_url,
        }.items():
            if not present:
                stats["remaining_missing"][key].append(relative)

    try:
        stats["content_discovery"] = publish_content_discovery(SITE)
        stats["authorized_courses"] = publish_authorized_courses(SITE)
    except ValueError as error:
        failures.append(f"institutional_seo_api_v201: {error}")

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
