#!/usr/bin/env python3
"""Upgrade every magazine article with visible intent content and matching schema.

The script reuses the governed extraction logic in enhance_search_intent_v1 and
extends it to every static magazine article. It does not invent study findings:
answers are copied from the published lead, summary, limitations and practical
sections, plus one fixed medical-safety statement.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts import enhance_search_intent_v1 as base

ROOT = Path(__file__).resolve().parents[1]
MAGAZINE = ROOT / "magazine"
NAV_MARKER = 'data-research-navigation="v2"'
INDEX_MARKER = 'data-magazine-reading-guide="v2"'


def article_graph(title: str, url: str, items: list[tuple[str, str]]) -> dict:
    description = items[0][1] if items else title
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": url + "#article",
                "headline": title,
                "name": title,
                "description": description,
                "url": url,
                "inLanguage": "ar",
                "mainEntityOfPage": {"@id": url + "#webpage"},
                "isPartOf": {
                    "@type": "CollectionPage",
                    "name": "المجلة والأبحاث",
                    "url": base.ORIGIN + "/magazine/",
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
                    "url": base.ORIGIN + "/",
                },
                "breadcrumb": {"@id": url + "#breadcrumb"},
                "mainEntity": {"@id": url + "#faq"},
            },
            {
                "@type": "WebPage",
                "@id": url + "#webpage",
                "name": title,
                "url": url,
                "inLanguage": "ar",
                "breadcrumb": {"@id": url + "#breadcrumb"},
                "mainEntity": {"@id": url + "#article"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": base.ORIGIN + "/"},
                    {"@type": "ListItem", "position": 2, "name": "المجلة والأبحاث", "item": base.ORIGIN + "/magazine/"},
                    {"@type": "ListItem", "position": 3, "name": title, "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": question,
                        "acceptedAnswer": {"@type": "Answer", "text": answer},
                    }
                    for question, answer in items
                ],
            },
        ],
    }


def related_navigation() -> str:
    return (
        f'<nav class="research-navigation" {NAV_MARKER} aria-label="مسارات مرتبطة">'
        '<h2>مسارات مرتبطة لفهم الدليل</h2><ul>'
        '<li><a href="./">فهرس المجلة والأبحاث</a></li>'
        '<li><a href="../family-guide/">دليل الأسرة العملي</a></li>'
        '<li><a href="../special-needs/">مركز ذوي الاحتياجات الخاصة</a></li>'
        '<li><a href="../trust/">منهجية المصادر والمراجعة</a></li>'
        '</ul></nav>'
    )


def enhance_article(path: Path) -> str:
    original_graph = base.magazine_graph
    try:
        base.magazine_graph = article_graph
        source = base.enhance_magazine(path)
    finally:
        base.magazine_graph = original_graph

    source = re.sub(
        r'<nav\b[^>]*data-research-navigation=["\']v2["\'][^>]*>.*?</nav>',
        "",
        source,
        flags=re.I | re.S,
    )
    faq = re.search(
        r'<section\b[^>]*data-search-intent-faq=["\']v1["\'][^>]*>.*?</section>',
        source,
        flags=re.I | re.S,
    )
    if not faq:
        raise RuntimeError(f"Visible FAQ block missing after enhancement: {path}")
    source = source[: faq.end()] + related_navigation() + source[faq.end() :]
    return source


def enhance_index(source: str) -> str:
    source = base.remove_meta_keywords(source)
    if INDEX_MARKER in source:
        return source
    block = (
        f'<section class="wrap reading-guide" {INDEX_MARKER} aria-labelledby="magazine-reading-guide">'
        '<h2 id="magazine-reading-guide">كيف تقرأ تحليلات المجلة؟</h2>'
        '<h3>ابدأ بسؤال الدراسة ثم افحص النتيجة والقيود</h3>'
        '<p>ابدأ بتحديد سؤال الدراسة ونوع التصميم والعينة، ثم افصل بين النتيجة الإحصائية ومعناها العملي. '
        'راجع القيود واحتمال التحيز ومدة المتابعة قبل تعميم النتيجة، وقارنها بجسم الدليل والإرشادات بدل الاعتماد على دراسة منفردة. '
        'التحليل العربي يساعد على فهم البحث ولا يحول النتيجة السكانية إلى تشخيص أو علاج فردي.</p>'
        '<h3>استخدم الروابط الأصلية للتحقق والتوسع</h3>'
        '<p>تحتفظ كل قراءة برابط المصدر الأصلي وبياناته الأساسية. ارجع إلى النص الأصلي عند الحاجة إلى تفاصيل المنهج أو الجداول أو تعريف النتائج، '
        'واستخدم صفحة منهجية المصادر لفهم مراتب الدليل وكيفية التعامل مع عدم اليقين والتعارض بين الدراسات.</p>'
        '</section>'
    )
    needle = '<section class="wrap grid"'
    if needle not in source:
        raise RuntimeError("Magazine index grid marker was not found")
    return source.replace(needle, block + needle, 1)


def collect_changes() -> list[tuple[Path, str]]:
    changes: list[tuple[Path, str]] = []
    index = MAGAZINE / "index.html"
    updated_index = enhance_index(index.read_text(encoding="utf-8"))
    if updated_index != index.read_text(encoding="utf-8"):
        changes.append((index, updated_index))

    for path in sorted(MAGAZINE.glob("*.html")):
        if path.name == "index.html":
            continue
        updated = enhance_article(path)
        if updated != path.read_text(encoding="utf-8"):
            changes.append((path, updated))
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    changes = collect_changes()
    if args.check:
        if changes:
            for path, _ in changes:
                print(path.relative_to(ROOT))
            return 1
        return 0

    for path, content in changes:
        path.write_text(content, encoding="utf-8")
    print(f"Updated {len(changes)} magazine files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
