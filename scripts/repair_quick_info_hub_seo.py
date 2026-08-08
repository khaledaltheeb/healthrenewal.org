#!/usr/bin/env python3
"""Repair the Quick Information hub's semantic SEO and image accessibility.

The repair is deterministic and idempotent. It does not rewrite article prose.
It completes social metadata, adds a meaningful H2/H3 usage guide for the deep
collection page, and assigns topic-specific alt text to Quick Info card images
using the canonical v1 manifest. Images that are genuinely decorative receive
explicit presentation semantics instead of a bare empty alt attribute.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

MARKER_START = "<!-- QUICK_INFO_HUB_SEO_V1_START -->"
MARKER_END = "<!-- QUICK_INFO_HUB_SEO_V1_END -->"
SITE_URL = "https://healthrenewal.org/quick-info/"
COVER_URL = "https://healthrenewal.org/assets/quick-info/quick-info-cover.png"
TITLE = "معلومات سريعة | مقارنات واختبارات وأدلة نفسية عربية"
DESCRIPTION = "معلومات نفسية وصحية عربية منظمة حسب نية البحث: مقارنات، فحوص تثقيفية، علاقات، نوم، قلق، تعافٍ وخطوات عملية مع مصادر موثوقة."
OG_TAGS = (
    f'<meta property="og:url" content="{SITE_URL}">',
    f'<meta property="og:description" content="{DESCRIPTION}">',
    '<meta property="og:image:alt" content="غلاف قسم المعلومات السريعة في منصة روافد">',
    f'<meta name="twitter:title" content="{TITLE}">',
    f'<meta name="twitter:description" content="{DESCRIPTION}">',
    f'<meta name="twitter:image" content="{COVER_URL}">',
    '<meta name="twitter:image:alt" content="غلاف قسم المعلومات السريعة في منصة روافد">',
)

TITLE_RE = re.compile(r"<title>.*?</title>", re.I | re.S)
DESC_RE = re.compile(r'<meta\s+name=["\']description["\']\s+content=["\'].*?["\']\s*/?>', re.I | re.S)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I | re.S)
SRC_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.I)
ALT_EMPTY_RE = re.compile(r'\balt=["\']["\']', re.I)


def replace_or_insert_meta(source: str, property_name: str, tag: str) -> str:
    if property_name.startswith("og:"):
        pattern = re.compile(
            rf'<meta\s+property=["\']{re.escape(property_name)}["\']\s+content=["\'].*?["\']\s*/?>',
            re.I | re.S,
        )
    else:
        pattern = re.compile(
            rf'<meta\s+name=["\']{re.escape(property_name)}["\']\s+content=["\'].*?["\']\s*/?>',
            re.I | re.S,
        )
    if pattern.search(source):
        return pattern.sub(tag, source, count=1)
    return source.replace("</head>", tag + "\n</head>", 1)


def set_decorative_semantics(tag: str) -> str:
    if 'role="presentation"' not in tag and "role='presentation'" not in tag:
        tag = tag[:-1].rstrip() + ' role="presentation">'
    if 'aria-hidden="true"' not in tag and "aria-hidden='true'" not in tag:
        tag = tag[:-1].rstrip() + ' aria-hidden="true">'
    return tag


def repair_image(tag: str, titles: dict[str, str]) -> str:
    if not ALT_EMPTY_RE.search(tag):
        return tag
    match = SRC_RE.search(tag)
    src = match.group(1) if match else ""
    card = re.search(r"/assets/quick-info/cards/([^/?#]+)\.png", src, re.I)
    if card:
        slug = card.group(1)
        title = titles.get(slug, slug.replace("-", " "))
        alt = html.escape(f"بطاقة توضيحية لموضوع: {title}", quote=True)
        return ALT_EMPTY_RE.sub(f'alt="{alt}"', tag, count=1)
    if "quick-info-cover" in src:
        return ALT_EMPTY_RE.sub('alt="غلاف قسم المعلومات السريعة"', tag, count=1)
    return set_decorative_semantics(tag)


def repair(root: Path) -> dict[str, object]:
    hub = root / "quick-info" / "index.html"
    manifest = root / "api" / "v1" / "quick-info.json"
    if not hub.is_file() or not manifest.is_file():
        raise SystemExit("Quick Info hub or manifest is missing")

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if payload.get("count") != 250 or len(items) != 250:
        raise SystemExit(f"Expected 250 primary Quick Info items, found {len(items)}")
    titles = {str(item["slug"]): str(item["title"]) for item in items}

    source = hub.read_text(encoding="utf-8")
    before = source
    source = TITLE_RE.sub(f"<title>{TITLE}</title>", source, count=1)
    description_tag = f'<meta name="description" content="{DESCRIPTION}">'
    source = DESC_RE.sub(description_tag, source, count=1) if DESC_RE.search(source) else source.replace("</head>", description_tag + "\n</head>", 1)

    for tag in OG_TAGS:
        name_match = re.search(r'(?:property|name)="([^"]+)"', tag)
        assert name_match
        source = replace_or_insert_meta(source, name_match.group(1), tag)

    source = IMG_RE.sub(lambda match: repair_image(match.group(0), titles), source)

    guide = f'''{MARKER_START}
<section class="wrap hub-use-guide" aria-labelledby="quick-info-use-guide">
  <h2 id="quick-info-use-guide">كيف تستخدم قسم المعلومات السريعة؟</h2>
  <h3>ابدأ بالسؤال الأقرب إلى ما تريد فهمه، ثم انتقل إلى الخطوة التالية</h3>
  <p>تجمع الصفحة مقارنات وفحوصًا تثقيفية وخطوات عملية. لا تتعامل مع العنوان أو قائمة العلامات كتشخيص؛ افتح الموضوع الأقرب إلى نية بحثك، راجع السياق والمدة والأثر، ثم استخدم المصادر والملاحظات العملية لتحديد ما إذا كانت المراقبة الذاتية كافية أو أن التقييم المهني أنسب.</p>
</section>
{MARKER_END}'''
    source = re.sub(re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END), "", source, flags=re.S)
    position = source.lower().rfind("</main>")
    if position < 0:
        raise SystemExit("Quick Info hub is missing </main>")
    source = source[:position] + guide + "\n" + source[position:]

    hub.write_text(source, encoding="utf-8", newline="\n")

    remaining_bare_empty_alt = 0
    for tag in IMG_RE.findall(source):
        if ALT_EMPTY_RE.search(tag) and "presentation" not in tag and 'aria-hidden="true"' not in tag:
            remaining_bare_empty_alt += 1
    checks = {
        "changed": source != before,
        "title": TITLE in source,
        "description": DESCRIPTION in source,
        "guideH2H3": "كيف تستخدم قسم المعلومات السريعة؟" in source and "ابدأ بالسؤال الأقرب" in source,
        "ogUrl": 'property="og:url"' in source,
        "ogDescription": 'property="og:description"' in source,
        "ogImageAlt": 'property="og:image:alt"' in source,
        "twitterComplete": all(field in source for field in ("twitter:title", "twitter:description", "twitter:image", "twitter:image:alt")),
        "remainingBareEmptyAlt": remaining_bare_empty_alt,
    }
    if not all(value is True for key, value in checks.items() if key not in {"changed", "remainingBareEmptyAlt"}) or remaining_bare_empty_alt:
        raise SystemExit(json.dumps(checks, ensure_ascii=False))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = repair(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
