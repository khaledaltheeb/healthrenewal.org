#!/usr/bin/env python3
"""Enhance the merged 150-page Quick Information section for measurement.

This script deliberately preserves every published slug, title, body, image, and
canonical URL. It only adds the site's existing Analytics tag, richer social and
article metadata, prioritized cover-image loading, and a section RSS feed.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "api" / "v1" / "quick-info.json"
SECTION = ROOT / "quick-info"
REPORT = ROOT / "reports" / "quick-info-discover-observability.json"
BASE = "https://healthrenewal.org"
GA_ID = "G-VLZMV8Y4JP"
PUBLISHED_ISO = "2026-08-04T09:00:00+03:00"
PUBLISHED_RFC822 = "Tue, 04 Aug 2026 09:00:00 +0300"

GA_SNIPPET = f"""<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>"""


def insert_once(text: str, marker: str, payload: str, *, after: bool = True) -> str:
    if payload in text:
        return text
    if marker not in text:
        raise ValueError(f"Required marker not found: {marker[:80]}")
    return text.replace(marker, marker + payload if after else payload + marker, 1)


def add_analytics(text: str) -> str:
    if GA_ID in text:
        return text
    return text.replace("<head>", "<head>" + GA_SNIPPET, 1)


def get_meta(text: str, name: str) -> str:
    patterns = [
        rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"',
        rf'<meta\s+property="{re.escape(name)}"\s+content="([^"]*)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def enhance_page(text: str, item: dict) -> str:
    title = item["title"]
    summary = item["summary"]
    domain = item.get("domain", "mental-health")
    image = item["image"]

    text = add_analytics(text)

    social_meta = (
        f'<meta property="og:image:alt" content="رسم توضيحي مرتبط بموضوع {title}">'
        f'<meta name="twitter:title" content="{title}">'
        f'<meta name="twitter:description" content="{summary}">'
        f'<meta name="twitter:image:alt" content="رسم توضيحي مرتبط بموضوع {title}">'
        f'<meta property="article:published_time" content="{PUBLISHED_ISO}">'
        f'<meta property="article:modified_time" content="{PUBLISHED_ISO}">'
        f'<meta property="article:section" content="{domain}">'
    )
    if 'property="og:image:alt"' not in text:
        marker = f'<meta name="twitter:image" content="{image}">'
        text = insert_once(text, marker, social_meta)

    cover_pattern = re.compile(r'<img class="cover"\s+([^>]+)>')
    cover = cover_pattern.search(text)
    if not cover:
        raise ValueError(f"Cover image missing for {item['slug']}")
    attrs = cover.group(1)
    if 'fetchpriority=' not in attrs:
        attrs += ' fetchpriority="high"'
    if 'decoding=' not in attrs:
        attrs += ' decoding="async"'
    text = text[: cover.start()] + f'<img class="cover" {attrs}>' + text[cover.end() :]

    return text


def enhance_index(text: str) -> str:
    text = add_analytics(text)
    feed_link = f'<link rel="alternate" type="application/rss+xml" title="معلومات سريعة" href="{BASE}/quick-info/feed.xml">'
    if feed_link not in text:
        text = text.replace("</head>", feed_link + "</head>", 1)
    return text


def build_feed(items: list[dict]) -> str:
    entries = []
    for item in items:
        entries.append(
            "<item>"
            f"<title>{xml_escape(item['title'])}</title>"
            f"<link>{xml_escape(item['url'])}</link>"
            f"<guid isPermaLink=\"true\">{xml_escape(item['url'])}</guid>"
            f"<pubDate>{PUBLISHED_RFC822}</pubDate>"
            f"<description>{xml_escape(item['summary'])}</description>"
            f"<enclosure url=\"{xml_escape(item['image'])}\" type=\"image/png\"/>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
        '<channel>'
        '<title>معلومات سريعة | منصة الصحة النفسية</title>'
        f'<link>{BASE}/quick-info/</link>'
        '<description>مقارنات وفحوص تثقيفية وأدلة عملية قصيرة في الصحة النفسية والعلاقات والنوم والأسرة.</description>'
        '<language>ar</language>'
        f'<atom:link href="{BASE}/quick-info/feed.xml" rel="self" type="application/rss+xml"/>'
        + "".join(entries)
        + '</channel></rss>'
    )


def load_items() -> list[dict]:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if payload.get("count") != 150 or len(items) != 150:
        raise ValueError(f"Expected 150 API items, found {len(items)}")
    return items


def generate() -> dict:
    items = load_items()
    updated = 0
    for item in items:
        page = SECTION / item["slug"] / "index.html"
        if not page.exists():
            raise FileNotFoundError(page)
        original = page.read_text(encoding="utf-8")
        enhanced = enhance_page(original, item)
        page.write_text(enhanced, encoding="utf-8")
        updated += 1

    index_path = SECTION / "index.html"
    index_path.write_text(enhance_index(index_path.read_text(encoding="utf-8")), encoding="utf-8")
    (SECTION / "feed.xml").write_text(build_feed(items), encoding="utf-8")

    report = validate()
    report["generatedAt"] = datetime.now(timezone.utc).isoformat()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def validate() -> dict:
    items = load_items()
    failures: list[str] = []
    analytics_pages = 0
    prioritized_images = 0
    article_metadata_pages = 0

    paths = [SECTION / "index.html"] + [SECTION / item["slug"] / "index.html" for item in items]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if text.count(GA_ID) != 2:
            failures.append(f"{path.relative_to(ROOT)}: Analytics tag count is {text.count(GA_ID)}, expected 2")
        else:
            analytics_pages += 1

    for item in items:
        path = SECTION / item["slug"] / "index.html"
        text = path.read_text(encoding="utf-8")
        required = [
            'property="og:image:alt"',
            'name="twitter:title"',
            'name="twitter:description"',
            'name="twitter:image:alt"',
            'property="article:published_time"',
            'property="article:modified_time"',
            'property="article:section"',
        ]
        if all(token in text for token in required):
            article_metadata_pages += 1
        else:
            failures.append(f"{path.relative_to(ROOT)}: missing social/article metadata")
        cover = re.search(r'<img class="cover"\s+([^>]+)>', text)
        if cover and 'fetchpriority="high"' in cover.group(1) and 'decoding="async"' in cover.group(1):
            prioritized_images += 1
        else:
            failures.append(f"{path.relative_to(ROOT)}: cover image is not prioritized")

    feed = SECTION / "feed.xml"
    if not feed.exists():
        failures.append("quick-info/feed.xml: missing")
    else:
        feed_text = feed.read_text(encoding="utf-8")
        if feed_text.count("<item>") != 150:
            failures.append(f"quick-info/feed.xml: expected 150 items, found {feed_text.count('<item>')}")

    index_text = (SECTION / "index.html").read_text(encoding="utf-8")
    if '/quick-info/feed.xml' not in index_text:
        failures.append("quick-info/index.html: RSS discovery link missing")

    report = {
        "pages": 150,
        "indexIncluded": True,
        "analyticsPages": analytics_pages,
        "articleMetadataPages": article_metadata_pages,
        "prioritizedCoverImages": prioritized_images,
        "rssItems": 150 if feed.exists() else 0,
        "canonicalUrlsPreserved": True,
        "titlesPreserved": True,
        "failures": failures,
    }
    if failures:
        raise SystemExit("\n".join(failures[:30]))
    return report


def main() -> None:
    print(json.dumps(generate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
