from __future__ import annotations

"""واجهة توافق لنشر الأدوات اليومية داخل الصفحة المؤسسية الجديدة.

يبقى ناشر SEO السابق محفوظًا كـ core، بينما يقتصر هذا الملف على ربط
الأدوات ومسارات التعلم ببنية الهيدر والبطاقات القديمة أو الجديدة دون تكرار.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import publish_daily_tools_v24_core as _core
from scripts import publish_daily_tools_v24_seo_core as _seo
from scripts.publish_daily_tools_v24_seo_core import *  # noqa: F401,F403


def _insert_before_first(text: str, markers: tuple[str, ...], addition: str, label: str) -> str:
    for marker in markers:
        if marker in text:
            return text.replace(marker, addition + marker, 1)
    raise SystemExit(f"Homepage {label} insertion point is missing")


def link_homepage() -> bool:
    home = SITE / "index.html"
    if not home.is_file():
        raise SystemExit("Homepage output is missing before daily-tools publication")
    text = home.read_text(encoding="utf-8")

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
            raise SystemExit("Homepage tools-card insertion point is missing")
        card_class = "card tool-card" if 'class="tools-grid"' in text else "card"
        new_cards = (
            f'<article class="{card_class}" data-daily-tools-v219><h3>الأدوات النفسية التفاعلية</h3>'
            '<p>ثماني أدوات يومية للتنظيم والمتابعة المحلية في التوتر والنوم والأسرة والفقد والحدود، دون تشخيص أو إرسال البيانات إلى خادم.</p>'
            '<a href="daily-tools/">فتح الأدوات التفاعلية</a></article>'
            f'<article class="{card_class}" data-learning-paths-v219><h3>مسارات التعلم القصيرة</h3>'
            '<p>أربعة مسارات مترابطة تحول المعرفة إلى خطة أيام وأدوات عملية قابلة للمراجعة.</p>'
            '<a href="learning-paths/">فتح مسارات التعلم</a></article>'
        )
        text = text.replace(card_marker, card_marker + new_cards, 1)

    keyword_match = re.search(r'(<meta name="keywords" content=")([^"]*)(">)', text)
    if keyword_match:
        items = [item.strip() for item in keyword_match.group(2).split(",") if item.strip()]
        for value in (
            "أدوات نفسية تفاعلية",
            "أدوات تنظيم التوتر",
            "أدوات متابعة النوم",
            "مسارات تعلم الصحة النفسية",
        ):
            if value not in items:
                items.append(value)
        text = text[: keyword_match.start(2)] + ",".join(items) + text[keyword_match.end(2) :]

    text = _core.add_homepage_jsonld(text)
    home.write_text(text, encoding="utf-8")
    return (
        text.count('href="daily-tools/"') >= 2
        and text.count('href="learning-paths/"') >= 2
        and text.count("data-daily-tools-v219") == 1
        and text.count("data-learning-paths-v219") == 1
    )


def publish(data: dict) -> None:
    _core.link_homepage = link_homepage
    _seo.publish(data)


_core.link_homepage = link_homepage


if __name__ == "__main__":
    if not SITE.exists():
        raise SystemExit("Missing site output")
    publish(json.loads(DATA.read_text(encoding="utf-8")))
