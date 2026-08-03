#!/usr/bin/env python3
"""Enhance the published Quick Information section without changing its content.

Preserves all 150 slugs, titles, bodies, canonical URLs and images. Adds the
site's existing Analytics tag, richer social/article metadata, prioritized cover
loading, and a deterministic RSS feed generated from the section API.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
SECTION = ROOT / "quick-info"
API_PATH = ROOT / "api" / "v1" / "quick-info.json"
REPORT_PATH = ROOT / "reports" / "quick-info-discover-observability.json"
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


def load_payload() -> dict:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if payload.get("count") != 150 or len(items) != 150:
        raise ValueError(f"Expected 150 Quick Information entries, found {len(items)}")
    if len({item["slug"] for item in items}) != 150:
        raise ValueError("Quick Information slugs are not unique")
    return payload


def add_analytics(text: str) -> str:
    if GA_ID in text:
        return text
    if "<head>" not in text:
        raise ValueError("HTML head not found")
    return text.replace("<head>", "<head>" + GA_SNIPPET, 1)


def add_article_metadata(text: str, item: dict) -> str:
    if 'property="og:image:alt"' in text:
        return text
    marker = f'<meta name="twitter:image" content="{item["image"]}">'
    if marker not in text:
        raise ValueError(f"Twitter image marker missing for {item['slug']}")
    title = html.escape(item["title"], quote=True)
    summary = html.escape(item["summary"], quote=True)
    domain = html.escape(item.get("domain", "mental-health"), quote=True)
    metadata = (
        f'<meta property="og:image:alt" content="رسم توضيحي مرتبط بموضوع {title}">'
        f'<meta name="twitter:title" content="{title}">'
        f'<meta name="twitter:description" content="{summary}">'
        f'<meta name="twitter:image:alt" content="رسم توضيحي مرتبط بموضوع {title}">'
        f'<meta property="article:published_time" content="{PUBLISHED_ISO}">'
        f'<meta property="article:modified_time" content="{PUBLISHED_ISO}">'
        f'<meta property="article:section" content="{domain}">'
    )
    return text.replace(marker, marker + metadata, 1)


def prioritize_cover(text: str, slug: str) -> str:
    pattern = re.compile(r'<img class="cover"\s+([^>]+)>')
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Cover image missing for {slug}")
    attrs = match.group(1)
    if 'fetchpriority=' not in attrs:
        attrs += ' fetchpriority="high"'
    if 'decoding=' not in attrs:
        attrs += ' decoding="async"'
    return text[: match.start()] + f'<img class="cover" {attrs}>' + text[match.end() :]


def enhance_article(path: Path, item: dict) -> None:
    text = path.read_text(encoding="utf-8")
    text = add_analytics(text)
    text = add_article_metadata(text, item)
    text = prioritize_cover(text, item["slug"])
    path.write_text(text, encoding="utf-8")


def enhance_index() -> None:
    path = SECTION / "index.html"
    text = add_analytics(path.read_text(encoding="utf-8"))
    feed_link = f'<link rel="alternate" type="application/rss+xml" title="معلومات سريعة" href="{BASE}/quick-info/feed.xml">'
    if feed_link not in text:
        text = text.replace("</head>", feed_link + "</head>", 1)
    path.write_text(text, encoding="utf-8")


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
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        '<title>معلومات سريعة | منصة الصحة النفسية</title>'
        f'<link>{BASE}/quick-info/</link>'
        '<description>مقارنات وفحوص تثقيفية وأدلة عملية قصيرة في الصحة النفسية والعلاقات والنوم والأسرة.</description>'
        '<language>ar</language>'
        f'<atom:link href="{BASE}/quick-info/feed.xml" rel="self" type="application/rss+xml"/>'
        + "".join(entries)
        + "</channel></rss>"
    )


def validate(items: list[dict]) -> dict:
    failures: list[str] = []
    analytics_pages = 0
    article_metadata_pages = 0
    prioritized_images = 0

    all_pages = [SECTION / "index.html"] + [SECTION / item["slug"] / "index.html" for item in items]
    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        if text.count(GA_ID) == 2:
            analytics_pages += 1
        else:
            failures.append(f"{page.relative_to(ROOT)}: Analytics count is {text.count(GA_ID)}")

    for item in items:
        page = SECTION / item["slug"] / "index.html"
        text = page.read_text(encoding="utf-8")
        metadata = (
            'property="og:image:alt"',
            'name="twitter:title"',
            'name="twitter:description"',
            'name="twitter:image:alt"',
            'property="article:published_time"',
            'property="article:modified_time"',
            'property="article:section"',
        )
        if all(token in text for token in metadata):
            article_metadata_pages += 1
        else:
            failures.append(f"{page.relative_to(ROOT)}: article/social metadata incomplete")
        cover = re.search(r'<img class="cover"\s+([^>]+)>', text)
        if cover and 'fetchpriority="high"' in cover.group(1) and 'decoding="async"' in cover.group(1):
            prioritized_images += 1
        else:
            failures.append(f"{page.relative_to(ROOT)}: cover priority attributes missing")

        expected_canonical = f'<link rel="canonical" href="{item["url"]}">'
        expected_title = f'<meta property="og:title" content="{html.escape(item["title"], quote=True)}">'
        if expected_canonical not in text:
            failures.append(f"{page.relative_to(ROOT)}: canonical changed")
        if expected_title not in text:
            failures.append(f"{page.relative_to(ROOT)}: published title changed")

    feed_path = SECTION / "feed.xml"
    feed_items = 0
    if feed_path.exists():
        feed_items = feed_path.read_text(encoding="utf-8").count("<item>")
    if feed_items != 150:
        failures.append(f"quick-info/feed.xml: expected 150 items, found {feed_items}")
    if "/quick-info/feed.xml" not in (SECTION / "index.html").read_text(encoding="utf-8"):
        failures.append("quick-info/index.html: RSS discovery link missing")

    report = {
        "generatedAt": PUBLISHED_ISO,
        "pages": 150,
        "analyticsPages": analytics_pages,
        "articleMetadataPages": article_metadata_pages,
        "prioritizedCoverImages": prioritized_images,
        "rssItems": feed_items,
        "canonicalUrlsPreserved": not any("canonical changed" in item for item in failures),
        "titlesPreserved": not any("published title changed" in item for item in failures),
        "failures": failures,
    }
    if failures:
        raise SystemExit("\n".join(failures[:30]))
    return report


def main() -> None:
    payload = load_payload()
    items = payload["items"]
    for item in items:
        page = SECTION / item["slug"] / "index.html"
        if not page.exists():
            raise FileNotFoundError(page)
        enhance_article(page, item)
    enhance_index()
    (SECTION / "feed.xml").write_text(build_feed(items), encoding="utf-8")
    report = validate(items)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
