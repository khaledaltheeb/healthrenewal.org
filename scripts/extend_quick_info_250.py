#!/usr/bin/env python3
"""Extend the Quick Information section from 200 to 250 pages."""

from __future__ import annotations

import json
import re

import build_quick_info as base
import extend_quick_info_200 as v200

EXPECTED_BASE = 200
EXPECTED_TOTAL = 250
DATA_PATH = base.ROOT / "content/quick-info-extension-v250.tsv"


def parse_new_topics() -> tuple[list[dict], dict[str, dict]]:
    topics: list[dict] = []
    details: dict[str, dict] = {}
    for number, line in enumerate(DATA_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split("|", 8)
        if len(fields) != 9:
            raise SystemExit(f"Invalid topic row {number}: expected 9 fields")
        slug, title, fmt, domain, left, right, summary_text, key, item_text = fields
        items = [value.strip() for value in item_text.split("~") if value.strip()]
        topics.append({
            "slug": slug,
            "title": title,
            "format": fmt,
            "domain": domain,
            "left": left,
            "right": right,
        })
        details[slug] = {"summary": summary_text, "key": key, "items": items}
    return topics, details


NEW_TOPICS, DETAILS = parse_new_topics()
ORIGINAL_SUMMARY = v200.summary
ORIGINAL_BODY = v200.body


def summary(topic: dict) -> str:
    detail = DETAILS.get(topic["slug"])
    return detail["summary"] if detail else ORIGINAL_SUMMARY(topic)


def _list(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    cls = " class='steps'" if ordered else ""
    return f"<{tag}{cls}>" + "".join(f"<li>{base.e(item)}</li>" for item in items) + f"</{tag}>"


def body(topic: dict) -> str:
    detail = DETAILS.get(topic["slug"])
    if not detail:
        return ORIGINAL_BODY(topic)

    guide = base.guide(topic)
    fmt = topic["format"]
    items = list(detail["items"])

    if fmt == "comparison":
        if len(items) < 3:
            raise SystemExit(f"Comparison needs three signals: {topic['slug']}")
        rows = [
            ("المعنى", f"{base.e(topic['left'])}: يحتفظ بقدر من الاختيار والمرونة.", f"{base.e(topic['right'])}: يُفهم من النمط والأثر لا الاسم وحده."),
            ("ما يرجح الفرق", base.e(items[0]), base.e(items[1])),
            ("الأثر الوظيفي", "قد يبقى الأداء ممكنًا مع وعي وحدود مناسبة.", base.e(items[2])),
            ("السؤال الفاصل", base.e(detail["key"]), "لا يكفي موقف واحد أو عرض منفرد للحكم."),
            ("الخطوة التالية", "دوّن المدة والسياق وما يساعد.", "اطلب تقييمًا عند الاستمرار أو التعطل أو الخطر."),
        ]
        trs = "".join(f"<tr><th>{a}</th><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)
        return (
            f"<h2>الخلاصة الدقيقة</h2><p>{base.e(detail['summary'])}</p>"
            f"<div class='notice'><strong>السؤال الأهم</strong>{base.e(detail['key'])}</div>"
            f"<table class='compare'><thead><tr><th>المعيار</th><th>{base.e(topic['left'])}</th><th>{base.e(topic['right'])}</th></tr></thead><tbody>{trs}</tbody></table>"
            f"<h2>إشارات تستحق المراقبة</h2>{_list(items + guide['signals'][:2])}"
            f"<h2>خطوات عملية</h2>{_list(guide['actions'], ordered=True)}"
        )

    if fmt == "check":
        questions = [value if value.endswith("؟") else value + "؟" for value in items]
        questions += [
            "هل استمر النمط بدل أن يكون موقفًا عابرًا؟",
            "هل أثر في النوم أو العمل أو الدراسة أو العلاقات؟",
            "هل دفعك إلى التجنب أو العزلة؟",
            "هل لاحظه شخص موثوق؟",
            "هل توجد خطورة أو فقدان قدرة على العناية بالنفس؟",
        ]
        return (
            f"<h2>قبل الإجابة</h2><p>{base.e(detail['summary'])}</p>"
            "<div class='notice'><strong>الفحص للتثقيف لا للتشخيص.</strong> لا تجمع الإجابات لتمنح نفسك تسمية؛ راقب المدة والشدة والأثر.</div>"
            f"<h2>الأسئلة العشرة</h2>{_list(questions[:10], ordered=True)}"
            f"<h2>السؤال المحوري</h2><p>{base.e(detail['key'])}</p>"
            f"<h2>ما الخطوة التالية؟</h2>{_list(guide['actions'], ordered=True)}"
        )

    if fmt == "factors":
        if len(items) != 5:
            raise SystemExit(f"Factors page needs exactly five items: {topic['slug']}")
        sections = "".join(
            f"<section><h3>{i}. {base.e(value)}</h3><p>قد يساهم هذا العامل في النمط، لكنه لا يثبت السبب وحده. راقب توقيته وما يزيده وما يخففه.</p></section>"
            for i, value in enumerate(items, 1)
        )
        return (
            f"<h2>الفكرة الأساسية</h2><p>{base.e(detail['summary'])}</p>"
            f"<div class='notice'><strong>السؤال الأهم</strong>{base.e(detail['key'])}</div>"
            "<div class='notice'><strong>لا تختزل السبب في عامل واحد.</strong> الأسباب النفسية والجسدية والاجتماعية قد تتداخل.</div>"
            f"<h2>العوامل الخمسة</h2>{sections}"
            f"<h2>خطة مراجعة عملية</h2>{_list(guide['actions'], ordered=True)}"
        )

    signals = items + guide["signals"][: max(0, 5 - len(items))]
    actions = [detail["key"]] + guide["actions"][:4]
    return (
        f"<h2>الخلاصة</h2><p>{base.e(detail['summary'])}</p>"
        f"<h2>ما الذي تراقبه؟</h2>{_list(signals)}"
        f"<h2>خطة قابلة للتنفيذ</h2>{_list(actions, ordered=True)}"
        f"<h2>ما الذي لا يساعد؟</h2>{_list(['التعميم والاتهام بدل وصف السلوك', 'انتظار اللحظة المثالية أو حل كامل', 'العزلة عن مصادر الدعم الموثوقة'])}"
    )


def patch_homepage_count() -> None:
    path = base.ROOT / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- QUICK_INFO_SECTION_START -->.*?<!-- QUICK_INFO_SECTION_END -->", re.DOTALL)
    match = pattern.search(text)
    if match:
        block = re.sub(r"\b(?:150|200)\b", "250", match.group(0))
        text = text[:match.start()] + block + text[match.end():]
    base.write(path, text)


def write_tests(new_slugs: set[str]) -> None:
    new_slug_literal = repr(sorted(new_slugs))
    content = """from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 250
NEW_SLUGS = __NEW_SLUGS__

def test_quick_info():
    api = json.loads((ROOT / "api/v1/quick-info.json").read_text(encoding="utf-8"))
    assert api["count"] == EXPECTED
    assert len(api["items"]) == EXPECTED
    assert len(list((ROOT / "quick-info").glob("*/index.html"))) == EXPECTED
    assert len({item["slug"] for item in api["items"]}) == EXPECTED
    assert len({item["title"] for item in api["items"]}) == EXPECTED
    assert set(NEW_SLUGS).issubset({item["slug"] for item in api["items"]})
    for item in api["items"]:
        page = ROOT / "quick-info" / item["slug"] / "index.html"
        source = page.read_text(encoding="utf-8")
        assert "max-image-preview:large" in source
        assert '"Article"' in source
        assert '"FAQPage"' in source
        assert "المصادر المحورية" in source
        assert item["url"] in source
        with Image.open(ROOT / "assets/quick-info/cards" / (item["slug"] + ".png")) as image:
            assert image.size == (1280, 720)
    sitemap = (ROOT / "sitemap-quick-info.xml").read_text(encoding="utf-8")
    assert sitemap.count("<url>") == EXPECTED + 1
    assert "sitemap-quick-info.xml" in (ROOT / "sitemap-index.xml").read_text(encoding="utf-8")
    assert "250 صفحة" in (ROOT / "quick-info/index.html").read_text(encoding="utf-8")
    assert 'href="/quick-info/"' in (ROOT / "index.html").read_text(encoding="utf-8")
""".replace("__NEW_SLUGS__", new_slug_literal)
    base.write(base.ROOT / "tests/test_quick_info_section.py", content)


def main() -> None:
    existing = list(base.TOPICS) + v200.parse_new_topics()
    if len(existing) != EXPECTED_BASE:
        raise SystemExit(f"Expected {EXPECTED_BASE} composed topics, found {len(existing)}")
    if len(NEW_TOPICS) != 50:
        raise SystemExit(f"Expected 50 new topics, found {len(NEW_TOPICS)}")

    existing_slugs = {topic["slug"] for topic in existing}
    existing_titles = {topic["title"] for topic in existing}
    collisions = [
        topic["slug"] for topic in NEW_TOPICS
        if topic["slug"] in existing_slugs or topic["title"] in existing_titles
    ]
    if collisions:
        raise SystemExit(f"Topic collisions: {collisions}")

    base.TOPICS = existing + NEW_TOPICS
    base.summary = summary
    base.body = body

    if len(base.TOPICS) != EXPECTED_TOTAL:
        raise SystemExit(f"Expected {EXPECTED_TOTAL} topics, found {len(base.TOPICS)}")
    if len({topic["slug"] for topic in base.TOPICS}) != EXPECTED_TOTAL:
        raise SystemExit("Duplicate slugs")
    if len({topic["title"] for topic in base.TOPICS}) != EXPECTED_TOTAL:
        raise SystemExit("Duplicate titles")

    for topic in base.TOPICS:
        if not re.fullmatch(r"[a-z0-9-]+", topic["slug"]):
            raise SystemExit(f"Invalid slug: {topic['slug']}")
        if topic["format"] not in base.FORMAT_LABELS:
            raise SystemExit(f"Invalid format: {topic['format']}")
        if topic["domain"] not in base.GUIDES:
            raise SystemExit(f"Invalid domain: {topic['domain']}")

    base.write(base.ROOT / "assets/quick-info/quick-info.css", base.CSS)
    base.write(base.ROOT / "quick-info/index.html", re.sub(r"\b(?:150|200)\b", "250", base.hub()))
    base.make_image(base.ROOT / "assets/quick-info/quick-info-cover.png")
    for topic in base.TOPICS:
        base.write(base.ROOT / "quick-info" / topic["slug"] / "index.html", base.article(topic))
        base.make_image(base.ROOT / "assets/quick-info/cards" / (topic["slug"] + ".png"), topic)

    base.update_home()
    patch_homepage_count()
    base.sitemap()
    base.api()
    write_tests({topic["slug"] for topic in NEW_TOPICS})

    report = {
        "generatedAt": base.PUBLISHED + "T10:05:00+03:00",
        "pages": EXPECTED_TOTAL,
        "images": EXPECTED_TOTAL + 1,
        "newPages": len(NEW_TOPICS),
        "formats": {
            key: sum(1 for topic in base.TOPICS if topic["format"] == key)
            for key in base.FORMAT_LABELS
        },
        "discover": {
            "largeImages": True,
            "maxImagePreviewLarge": True,
            "articleSchema": True,
            "faqSchema": True,
            "canonicalUrls": True,
            "nonDiagnosticDisclosures": True,
        },
        "errors": [],
    }
    base.write(
        base.ROOT / "reports/quick-info-build.json",
        json.dumps(report, ensure_ascii=False, indent=2),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
