#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from publish_daily_tools_v24 import (
    BASE,
    DESIGN_CONTRACT,
    FOUNDING_NAME,
    LOGO,
    MANIFEST,
    SEARCH,
    SEO_CONTRACT,
    SITE_NAME,
    SOCIAL_IMAGE,
    STYLE,
    topic_keywords,
)

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
TARGET = SITE / "daily-tools" / "sleep-wind-down-plan" / "index.html"

SLEEP_EXTENSION = r"""
header,section{box-shadow:var(--shadow-mint)}
.notice{border-right:7px solid #c74776;background:var(--rose);border-color:var(--rose-line);box-shadow:var(--shadow-rose)}
.privacy{border-right:7px solid #078179;background:var(--mint);border-color:var(--mint-line);box-shadow:var(--shadow-mint)}
.actions,.legend{display:flex;gap:10px;flex-wrap:wrap}
button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:9px 15px;border:2px solid var(--mint-line);border-radius:15px;background:linear-gradient(145deg,#fff,var(--mint));color:var(--ink);font:inherit;font-weight:900;box-shadow:0 6px 0 #d6eee9,0 11px 22px rgba(102,190,171,.13);cursor:pointer}
button:nth-of-type(2n){background:linear-gradient(145deg,#fff,var(--rose));border-color:var(--rose-line);box-shadow:0 6px 0 #f5dce6,0 11px 22px rgba(205,129,160,.12)}
input[aria-invalid="true"],textarea[aria-invalid="true"]{border:3px solid #9b1c31;background:#fff7f8}
.field-error{display:block;color:#811329;font-weight:800;margin-top:4px}
.summary{font-weight:800}
table{width:100%;border-collapse:collapse;background:#fff}
th,td{border:1px solid #b9d8d4;padding:8px;text-align:right}
th{background:var(--lilac);color:#4a315f}
.chart-wrap{overflow:auto;border:2px solid var(--lilac-line);border-radius:18px;padding:12px;background:linear-gradient(145deg,#fff,var(--lilac));box-shadow:var(--shadow-lilac)}
.chart-wrap svg{display:block;width:100%;min-width:620px;height:auto}
.chart-wrap text{font:12px Tahoma,Arial,sans-serif;fill:var(--ink)}
.axis{stroke:var(--ink);stroke-width:1.5}.grid-line{stroke:#d6e7e4;stroke-width:1}
.series{fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.series-hours{stroke:#006f68}.series-quality{stroke:#6a42b8;stroke-dasharray:9 5}.series-energy{stroke:#a13c62;stroke-dasharray:2 5}
.legend span{display:inline-flex;align-items:center;gap:7px;padding:4px 10px;border-radius:999px;background:#fff;border:1px solid var(--mint-line)}
.legend i{display:inline-block;width:34px;border-top:3px solid}.legend .hours i{border-color:#006f68}.legend .quality i{border-color:#6a42b8;border-top-style:dashed}.legend .energy i{border-color:#a13c62;border-top-style:dotted}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:640px){nav,.actions{display:grid}table{font-size:.9rem}}
@media print{nav,.actions,form button,.privacy{display:none!important}body{background:#fff}header,section{box-shadow:none;border:1px solid #777}.chart-wrap{overflow:visible}.chart-wrap svg{min-width:0}}
"""


def first_group(text: str, pattern: str, label: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    if not match:
        raise SystemExit(f"Missing {label} in generated sleep-log page")
    return html.unescape(match.group(1)).strip()


def add_head_once(text: str, tag: str) -> str:
    if "</head>" not in text:
        raise SystemExit("Sleep-log head is not closed")
    return text.replace("</head>", tag + "</head>", 1)


def upsert_head_tag(text: str, identity: str, tag: str) -> str:
    pattern = re.compile(rf'<(?:meta|link)\b(?=[^>]*{re.escape(identity)})[^>]*>', re.I)
    matches = list(pattern.finditer(text))
    if len(matches) > 1:
        raise SystemExit(f"Duplicate sleep-log metadata before normalization: {identity}")
    if matches:
        match = matches[0]
        return text[: match.start()] + tag + text[match.end() :]
    return add_head_once(text, tag)


def normalize_title(text: str, raw_title: str) -> tuple[str, str, str]:
    base_title = re.sub(
        rf"\s*\|\s*(?:{re.escape(FOUNDING_NAME)}|{re.escape(SITE_NAME)})\s*$",
        "",
        raw_title,
        flags=re.I,
    ).strip()
    if not base_title:
        raise SystemExit("Sleep-log base title is empty")
    institutional_title = f"{base_title} | {SITE_NAME}"
    replacement = f"<title>{html.escape(institutional_title)}</title>"
    text, count = re.subn(
        r"<title\b[^>]*>.*?</title>",
        replacement,
        text,
        count=1,
        flags=re.I | re.S,
    )
    if count != 1:
        raise SystemExit("Sleep-log title normalization failed")
    return text, base_title, institutional_title


def normalize_html_contract(text: str) -> str:
    match = re.search(r'<html\b[^>]*\blang="ar"[^>]*\bdir="rtl"[^>]*>', text, re.I)
    if not match:
        raise SystemExit("Sleep-log HTML language and direction contract is missing")
    tag = match.group(0)
    additions: list[str] = []
    if f'data-design="marshmallow-v{DESIGN_CONTRACT}"' not in tag:
        additions.append(f'data-design="marshmallow-v{DESIGN_CONTRACT}"')
    if f'data-seo="institutional-v{SEO_CONTRACT}"' not in tag:
        additions.append(f'data-seo="institutional-v{SEO_CONTRACT}"')
    if additions:
        tag = tag[:-1] + " " + " ".join(additions) + ">"
        text = text[: match.start()] + tag + text[match.end() :]
    return text


def enrich_metadata(text: str) -> str:
    raw_title = first_group(text, r"<title\b[^>]*>(.*?)</title>", "title")
    description = first_group(
        text,
        r'<meta\b[^>]*\bname="description"[^>]*\bcontent="([^"]*)"[^>]*>',
        "description",
    )
    canonical = first_group(
        text,
        r'<link\b[^>]*\brel="canonical"[^>]*\bhref="([^"]+)"[^>]*>',
        "canonical",
    )
    text, base_title, title = normalize_title(text, raw_title)
    image_alt = f"هوية {SITE_NAME} — سجل النوم المحلي"
    keyword_items = topic_keywords(base_title, description, canonical)
    if not 4 <= len(keyword_items) <= 8 or len(keyword_items) != len(set(keyword_items)):
        raise SystemExit(f"Invalid sleep-log topic keyword set: {keyword_items}")
    keywords = ",".join(keyword_items)

    tags = (
        ('rel="canonical"', f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">'),
        ('name="keywords"', f'<meta name="keywords" content="{html.escape(keywords, quote=True)}">'),
        ('name="author"', f'<meta name="author" content="{html.escape(SITE_NAME, quote=True)}">'),
        ('name="application-name"', f'<meta name="application-name" content="{html.escape(SITE_NAME, quote=True)}">'),
        ('name="subject"', '<meta name="subject" content="الصحة النفسية والنوم والأدوات النفسية التفاعلية">'),
        ('name="audience"', '<meta name="audience" content="البالغون والأسر ومقدمو الرعاية">'),
        ('name="robots"', '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">'),
        ('name="theme-color"', '<meta name="theme-color" content="#e5faf5">'),
        ('name="color-scheme"', '<meta name="color-scheme" content="light">'),
        ('rel="manifest"', f'<link rel="manifest" href="{MANIFEST}">'),
        ('rel="icon"', f'<link rel="icon" href="{LOGO}" type="image/svg+xml">'),
        ('rel="apple-touch-icon"', f'<link rel="apple-touch-icon" href="{LOGO}">'),
        ('rel="search"', f'<link rel="search" type="application/opensearchdescription+xml" title="البحث في المنصة" href="{SEARCH}">'),
        ('rel="sitemap"', f'<link rel="sitemap" type="application/xml" href="{BASE}sitemap.xml">'),
        ('property="og:type"', '<meta property="og:type" content="website">'),
        ('property="og:locale"', '<meta property="og:locale" content="ar_AR">'),
        ('property="og:site_name"', f'<meta property="og:site_name" content="{html.escape(SITE_NAME, quote=True)}">'),
        ('property="og:title"', f'<meta property="og:title" content="{html.escape(title, quote=True)}">'),
        ('property="og:description"', f'<meta property="og:description" content="{html.escape(description, quote=True)}">'),
        ('property="og:url"', f'<meta property="og:url" content="{html.escape(canonical, quote=True)}">'),
        ('property="og:image"', f'<meta property="og:image" content="{SOCIAL_IMAGE}">'),
        ('property="og:image:alt"', f'<meta property="og:image:alt" content="{html.escape(image_alt, quote=True)}">'),
        ('name="twitter:card"', '<meta name="twitter:card" content="summary_large_image">'),
        ('name="twitter:title"', f'<meta name="twitter:title" content="{html.escape(title, quote=True)}">'),
        ('name="twitter:description"', f'<meta name="twitter:description" content="{html.escape(description, quote=True)}">'),
        ('name="twitter:image"', f'<meta name="twitter:image" content="{SOCIAL_IMAGE}">'),
        ('name="twitter:image:alt"', f'<meta name="twitter:image:alt" content="{html.escape(image_alt, quote=True)}">'),
    )
    for identity, tag in tags:
        text = upsert_head_tag(text, identity, tag)

    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebApplication",
                    "name": base_title,
                    "description": description,
                    "applicationCategory": "HealthApplication",
                    "operatingSystem": "Any",
                    "inLanguage": "ar",
                    "url": canonical,
                    "isAccessibleForFree": True,
                    "publisher": {
                        "@type": "Organization",
                        "name": SITE_NAME,
                        "alternateName": FOUNDING_NAME,
                        "url": BASE,
                    },
                },
                {
                    "@type": "WebPage",
                    "name": title,
                    "description": description,
                    "inLanguage": "ar",
                    "url": canonical,
                    "isPartOf": {
                        "@type": "WebSite",
                        "name": SITE_NAME,
                        "alternateName": FOUNDING_NAME,
                        "url": BASE,
                    },
                },
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    script_pattern = re.compile(
        r'<script\b[^>]*type="application/ld\+json"[^>]*>.*?</script>',
        re.I | re.S,
    )
    scripts = list(script_pattern.finditer(text))
    script_tag = f'<script type="application/ld+json">{schema}</script>'
    if len(scripts) > 1:
        raise SystemExit("Duplicate sleep-log JSON-LD blocks before normalization")
    if scripts:
        match = scripts[0]
        text = text[: match.start()] + script_tag + text[match.end() :]
    else:
        text = add_head_once(text, script_tag)
    return text


def validate_metadata(text: str) -> None:
    head_match = re.search(r"<head\b[^>]*>(.*?)</head>", text, re.I | re.S)
    if not head_match:
        raise SystemExit("Sleep-log head is missing after normalization")
    head = head_match.group(1)
    required = (
        f'data-design="marshmallow-v{DESIGN_CONTRACT}"',
        f'data-seo="institutional-v{SEO_CONTRACT}"',
        'name="keywords"',
        'name="robots"',
        'rel="manifest"',
        'rel="icon"',
        'rel="search"',
        'rel="sitemap"',
        'property="og:image"',
        'name="twitter:card"',
        'name="twitter:image"',
        'type="application/ld+json"',
        SITE_NAME,
    )
    missing = [
        marker for marker in required
        if marker not in (text if marker.startswith("data-") else head)
    ]
    if missing:
        raise SystemExit(f"Missing post-publication contract markers: {missing}")
    for marker in (
        '<title',
        '<meta name="description"',
        '<meta name="keywords"',
        '<link rel="canonical"',
        '<meta property="og:title"',
        '<meta property="og:url"',
        '<meta property="og:image"',
        '<meta name="twitter:card"',
        '<script type="application/ld+json"',
    ):
        if head.count(marker) != 1:
            raise SystemExit(f"Sleep-log head metadata must occur exactly once: {marker}")
    keyword_value = first_group(
        head,
        r'<meta\b[^>]*\bname="keywords"[^>]*\bcontent="([^"]*)"[^>]*>',
        "keywords",
    )
    keywords = [item.strip() for item in keyword_value.split(",") if item.strip()]
    if not 4 <= len(keywords) <= 8 or len(keywords) != len(set(keywords)):
        raise SystemExit(f"Sleep-log keyword contract failed: {keywords}")
    if f"| {FOUNDING_NAME}</title>" in head:
        raise SystemExit("Founding name remains the primary sleep-log title identity")


def main() -> None:
    if not TARGET.is_file():
        raise SystemExit(f"Missing generated sleep-log page: {TARGET}")
    text = TARGET.read_text(encoding="utf-8")
    text = normalize_html_contract(text)

    style_pattern = re.compile(r"<style>.*?</style>", re.S)
    replacement = f"<style>{STYLE}\n{SLEEP_EXTENSION}</style>"
    text, count = style_pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Expected one sleep-log style block, found {count}")

    text = text.replace(
        '<a href="/daily-tools/">الأدوات اليومية</a>',
        '<a href="/daily-tools/">الأدوات التفاعلية</a>',
        1,
    )
    header_marker = '<header><p>أداة تنظيمية غير تشخيصية للبالغين ومقدمي الرعاية</p>'
    if header_marker in text:
        text = text.replace(
            header_marker,
            '<header><span class="tool-kicker">أداة تفاعلية تنظيمية غير تشخيصية</span><p>للبالغين ومقدمي الرعاية</p>',
            1,
        )

    text = enrich_metadata(text)
    normalized = text.replace(" ", "").lower()
    if "rgba(0,0,0" in normalized or "text-shadow" in normalized:
        raise SystemExit("Dark text-box shadow regression detected in sleep-log page")
    for marker in (
        "--mint:#e5faf5",
        "--rose:#fff0f5",
        "--lilac:#f2edff",
        "--peach:#fff0e8",
        "--butter:#fff8d8",
    ):
        if marker not in text:
            raise SystemExit(f"Missing marshmallow palette marker: {marker}")
    validate_metadata(text)

    TARGET.write_text(text, encoding="utf-8")
    print(
        {
            "status": "passed",
            "design_contract": DESIGN_CONTRACT,
            "seo_contract": SEO_CONTRACT,
            "institutional_identity": SITE_NAME,
            "page": TARGET.relative_to(SITE).as_posix(),
        }
    )


if __name__ == "__main__":
    main()
