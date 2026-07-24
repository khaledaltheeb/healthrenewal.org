#!/usr/bin/env python3
from __future__ import annotations

"""مزامن مصدر الصفحة الرئيسية مع تصميم المارشملو القديم أو الجديد."""

import json
from pathlib import Path

from scripts import expose_daily_tools_home_v219_core as _core

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
RELEASE = 220


def _insert_before_first(text: str, markers: tuple[str, ...], addition: str, label: str) -> str:
    for marker in markers:
        if marker in text:
            return text.replace(marker, addition + marker, 1)
    raise SystemExit(f"Homepage {label} insertion point changed")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    text = _core.patch_keywords(text)
    text = _core.patch_jsonld(text)

    if 'href="daily-tools/"' not in text:
        text = _insert_before_first(
            text,
            (
                '<a href="provider-assessment-demo/">منصة مقدم الخدمة<span>التوثيق والسجل المهني المحلي</span></a>',
                '<a href="provider-assessment-demo/">منصة التقييم</a>',
            ),
            '<a href="daily-tools/">أدوات تفاعلية</a><a href="learning-paths/">مسارات التعلم</a>',
            "navigation",
        )

    if "data-daily-tools-v219" not in text:
        card_marker = '<a href="cognitive-tests/">فتح المهام</a></article>'
        if card_marker not in text:
            raise SystemExit("Homepage tools-card insertion point changed")
        card_class = "card tool-card" if 'class="tools-grid"' in text else "card"
        cards = (
            f'<article class="{card_class}" data-daily-tools-v219><h3>الأدوات النفسية التفاعلية</h3>'
            '<p>ثماني أدوات يومية للتنظيم والمتابعة المحلية في التوتر والنوم والأسرة والفقد والحدود، دون تشخيص أو إرسال البيانات إلى خادم.</p>'
            '<a href="daily-tools/">فتح الأدوات التفاعلية</a></article>'
            f'<article class="{card_class}" data-learning-paths-v219><h3>مسارات التعلم القصيرة</h3>'
            '<p>أربعة مسارات مترابطة تحول المعرفة إلى خطة أيام وأدوات عملية قابلة للمراجعة.</p>'
            '<a href="learning-paths/">فتح مسارات التعلم</a></article>'
        )
        text = text.replace(card_marker, card_marker + cards, 1)

    required = {
        'href="daily-tools/"': 2,
        'href="learning-paths/"': 2,
        "data-daily-tools-v219": 1,
        "data-learning-paths-v219": 1,
        _core.BASE + "daily-tools/": 1,
        _core.BASE + "learning-paths/": 1,
    }
    errors = {marker: text.count(marker) for marker, expected in required.items() if text.count(marker) != expected}
    if errors:
        raise SystemExit(f"Homepage interactive-tools discovery contract failed: {errors}")
    INDEX.write_text(text, encoding="utf-8")


def main() -> None:
    patch_index()
    _core.patch_verifier()
    print(
        json.dumps(
            {
                "status": "passed",
                "release": RELEASE,
                "homepage_source_linked": True,
                "daily_tools": "daily-tools/",
                "learning_paths": "learning-paths/",
                "desktop_marshmallow_compatible": True,
                "duplicate_free": True,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
