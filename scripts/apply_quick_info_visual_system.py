#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_quick_info as base
from quick_info_visuals import make_quick_info_image, quick_info_alt

BUILD_PATH = SCRIPTS / "build_quick_info.py"
HUB_PATH = ROOT / "quick-info" / "index.html"
API_PATH = ROOT / "api" / "v1" / "quick-info.json"


def compose_topics() -> list[dict]:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    topics = [dict(item) for item in payload.get("items", [])]
    if len(topics) != 250:
        raise RuntimeError(f"Expected 250 Quick Info topics, found {len(topics)}")
    if len({topic["slug"] for topic in topics}) != 250:
        raise RuntimeError("Duplicate Quick Info slugs detected in current API inventory")
    required = {"slug", "title", "domain", "format", "summary"}
    for topic in topics:
        missing = required.difference(topic)
        if missing:
            raise RuntimeError(f"API topic {topic.get('slug')} missing fields: {sorted(missing)}")
    return topics


def category_label(topic: dict) -> str:
    return base.GUIDES.get(topic["domain"], base.GUIDES["general"])["label"]


def summary_for(topic: dict) -> str:
    return " ".join(str(topic.get("summary", "")).split())


def patch_generated_page(topic: dict) -> None:
    page = ROOT / "quick-info" / topic["slug"] / "index.html"
    if not page.exists():
        raise FileNotFoundError(page)
    source = page.read_text(encoding="utf-8")
    alt = quick_info_alt(topic, category_label(topic))
    alt_html = html.escape(alt, quote=True)
    image_url = f"https://healthrenewal.org/assets/quick-info/cards/{topic['slug']}.png"
    image_src = f"/assets/quick-info/cards/{topic['slug']}.png"

    tag_pattern = rf'<img\s+class="cover"\s+src="{re.escape(image_src)}"[^>]*>'
    match = re.search(tag_pattern, source)
    if not match:
        raise RuntimeError(f"Could not find article image for {topic['slug']}")
    tag = match.group(0)
    if re.search(r'\salt="[^"]*"', tag):
        tag = re.sub(r'\salt="[^"]*"', f' alt="{alt_html}"', tag, count=1)
    else:
        tag = tag[:-1] + f' alt="{alt_html}">'
    if 'decoding=' not in tag:
        tag = tag[:-1] + ' decoding="async">'
    source = source[:match.start()] + tag + source[match.end():]

    og_alt = f'<meta property="og:image:alt" content="{alt_html}">'
    if 'property="og:image:alt"' not in source:
        source = source.replace(
            f'<meta property="og:image" content="{image_url}">',
            f'<meta property="og:image" content="{image_url}">{og_alt}',
            1,
        )

    twitter_alt = f'<meta name="twitter:image:alt" content="{alt_html}">'
    if 'name="twitter:image:alt"' not in source:
        source = source.replace(
            f'<meta name="twitter:image" content="{image_url}">',
            f'<meta name="twitter:image" content="{image_url}">{twitter_alt}',
            1,
        )

    page.write_text(source, encoding="utf-8")


def patch_hub(topics: list[dict]) -> None:
    source = HUB_PATH.read_text(encoding="utf-8")
    for topic in topics:
        image_src = f"/assets/quick-info/cards/{topic['slug']}.png"
        alt = html.escape(quick_info_alt(topic, category_label(topic)), quote=True)
        pattern = rf'(<img\s+src="{re.escape(image_src)}"[^>]*\salt=")[^"]*(")'
        source, count = re.subn(pattern, rf'\1{alt}\2', source, count=1)
        if count == 0:
            raise RuntimeError(f"Could not patch hub image alt for {topic['slug']}")
    source = re.sub(
        r'(<img\s+class="cover"\s+src="/assets/quick-info/quick-info-cover\.png"[^>]*\salt=")[^"]*(")',
        r'\1بطاقة الغلاف لقسم معلومات سريعة في منصة روافد\2',
        source,
        count=1,
    )
    HUB_PATH.write_text(source, encoding="utf-8")


def patch_api(topics: list[dict]) -> None:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    topic_map = {topic["slug"]: topic for topic in topics}
    if len(payload.get("items", [])) != 250:
        raise RuntimeError(f"Expected 250 API items, found {len(payload.get('items', []))}")
    for item in payload["items"]:
        topic = topic_map[item["slug"]]
        item["imageAlt"] = quick_info_alt(topic, category_label(topic))
    API_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_generator_source() -> None:
    source = BUILD_PATH.read_text(encoding="utf-8")
    import_line = "from quick_info_visuals import make_quick_info_image, quick_info_alt\n"
    if import_line not in source:
        source = source.replace("from PIL import Image, ImageDraw\n", "from PIL import Image, ImageDraw\n" + import_line, 1)

    if "def image_alt(topic):" not in source:
        replacement = '''def image_alt(topic):\n    if topic is None:\n        return quick_info_alt(None)\n    return quick_info_alt(topic, guide(topic)["label"])\n\ndef make_image(path, topic=None):\n    make_quick_info_image(\n        path,\n        topic,\n        category_label=guide(topic)["label"] if topic else "معلومات سريعة",\n        format_label=FORMAT_LABELS.get(topic["format"]) if topic else "معلومات سريعة",\n        summary_text=summary(topic) if topic else "مقارنات واضحة، فحوص تثقيفية، أسباب محتملة وخطوات عملية بلغة عربية موثوقة.",\n    )\n\n'''
        source, count = re.subn(
            r'def make_image\(path, topic=None\):\n.*?(?=def write\(path, text\):)',
            replacement,
            source,
            count=1,
            flags=re.S,
        )
        if count != 1:
            raise RuntimeError("Could not replace legacy make_image()")

    source = source.replace(
        'alt="رسم توضيحي مجرد مرتبط بموضوع الصفحة"',
        'alt="{e(image_alt(topic))}"',
    )
    source = source.replace(
        'loading="{"eager" if i<3 else "lazy"}" alt=""',
        'loading="{"eager" if i<3 else "lazy"}" decoding="async" alt="{e(image_alt(t))}"',
    )
    source = source.replace(
        'alt="رسم تجريدي للصحة النفسية"',
        'alt="بطاقة الغلاف لقسم معلومات سريعة في منصة روافد"',
    )

    article_og = '<meta property="og:image" content="{img_url(topic)}">'
    if 'property="og:image:alt"' not in source:
        source = source.replace(
            article_og,
            article_og + '<meta property="og:image:alt" content="{e(image_alt(topic))}">',
            1,
        )
    article_twitter = '<meta name="twitter:image" content="{img_url(topic)}">'
    if 'name="twitter:image:alt"' not in source:
        source = source.replace(
            article_twitter,
            article_twitter + '<meta name="twitter:image:alt" content="{e(image_alt(topic))}">',
            1,
        )

    source = source.replace(
        '"image":img_url(t)} for t in TOPICS',
        '"image":img_url(t),"imageAlt":image_alt(t)} for t in TOPICS',
    )
    BUILD_PATH.write_text(source, encoding="utf-8")


def validate(topics: list[dict]) -> None:
    forbidden_marker = re.compile(r'(رسم توضيحي مجرد مرتبط|alt="")')
    for topic in topics:
        image = ROOT / "assets" / "quick-info" / "cards" / f"{topic['slug']}.png"
        if not image.exists():
            raise FileNotFoundError(image)
        page = ROOT / "quick-info" / topic["slug"] / "index.html"
        source = page.read_text(encoding="utf-8")
        expected_alt = html.escape(quick_info_alt(topic, category_label(topic)), quote=True)
        if expected_alt not in source:
            raise RuntimeError(f"Missing page alt for {topic['slug']}")
        if 'property="og:image:alt"' not in source or 'name="twitter:image:alt"' not in source:
            raise RuntimeError(f"Missing social image alt for {topic['slug']}")
        if forbidden_marker.search(source):
            raise RuntimeError(f"Legacy/generic alt remains in {topic['slug']}")

    hub = HUB_PATH.read_text(encoding="utf-8")
    for topic in topics:
        expected_alt = html.escape(quick_info_alt(topic, category_label(topic)), quote=True)
        if expected_alt not in hub:
            raise RuntimeError(f"Missing hub alt for {topic['slug']}")

    api = json.loads(API_PATH.read_text(encoding="utf-8"))
    if any(not item.get("imageAlt") for item in api["items"]):
        raise RuntimeError("Some API items are missing imageAlt")

    build = BUILD_PATH.read_text(encoding="utf-8")
    legacy_tokens = ('domain=="sleep"', 'domain in {"relationships","grief"}', 'd.polygon([(470,315)')
    if any(token in build for token in legacy_tokens):
        raise RuntimeError("Legacy topic pictogram generator remains in build_quick_info.py")


def main() -> None:
    topics = compose_topics()

    # Fix source generation first so future builds cannot reintroduce pictograms.
    patch_generator_source()

    # Regenerate only visual assets and patch accessibility metadata. Article
    # bodies remain untouched, preserving later editorial and SEO improvements.
    make_quick_info_image(
        ROOT / "assets" / "quick-info" / "quick-info-cover.png",
        None,
        summary_text="مقارنات واضحة، فحوص تثقيفية، أسباب محتملة وخطوات عملية بلغة عربية موثوقة.",
    )
    for topic in topics:
        make_quick_info_image(
            ROOT / "assets" / "quick-info" / "cards" / f"{topic['slug']}.png",
            topic,
            category_label=category_label(topic),
            format_label=base.FORMAT_LABELS[topic["format"]],
            summary_text=summary_for(topic),
        )
        patch_generated_page(topic)

    patch_hub(topics)
    patch_api(topics)
    validate(topics)

    report = {
        "status": "ok",
        "topics": len(topics),
        "imagesRegenerated": len(topics) + 1,
        "imageTemplate": "rawafid-text-first-no-topic-pictograms",
        "altText": True,
        "openGraphImageAlt": True,
        "twitterImageAlt": True,
        "articleBodiesRebuilt": False,
    }
    report_path = ROOT / "reports" / "quick-info-visual-refresh.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
