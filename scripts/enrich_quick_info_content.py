#!/usr/bin/env python3
"""Post-process generated Quick Information pages with deeper unique explanations.

The base generator intentionally centralizes evidence profiles. This pass combines
profile-specific factors, markers and actions so list cards do not repeat generic
paragraphs and every article has an additional contextual interpretation section.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from generate_quick_info import OUT, TOPICS, profile


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def enrich_five(text: str, title: str) -> str:
    p = profile(title)
    pattern = re.compile(
        r"(<article class='point-card'><span>(\d+)</span><h3>.*?</h3><p>)(.*?)(</p></article>)",
        re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        index = max(0, min(int(match.group(2)) - 1, 4))
        explanation = (
            f"قد يظهر أثر هذا العامل في {p['markers'][index]}. "
            f"راقب السياق والتكرار بدل افتراض السبب، والخطوة العملية الأقرب هي: {p['actions'][index]}."
        )
        return match.group(1) + esc(explanation) + match.group(4)

    return pattern.sub(replace, text)


def enrich_standard(text: str, title: str) -> str:
    p = profile(title)
    pattern = re.compile(
        r"(<article class='point-card'><span>(\d+)</span><h3>.*?</h3><p>)"
        r"راقب تكرار هذا النمط وسياقه وأثره، ولا تحكم من موقف واحد\."
        r"(</p></article>)",
        re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        index = max(0, min(int(match.group(2)) - 1, 4))
        explanation = (
            f"يصبح هذا المؤشر أكثر أهمية عندما يتكرر مع {p['factors'][index]}. "
            f"بدل الحكم السريع، جرّب هذه الخطوة: {p['actions'][index]}."
        )
        return match.group(1) + esc(explanation) + match.group(3)

    return pattern.sub(replace, text)


def contextual_section(title: str) -> str:
    p = profile(title)
    points = [
        f"اسأل عن المدة: هل هو موقف عابر أم نمط يتكرر؟ راقب خصوصًا {p['markers'][0]}.",
        f"اسأل عن السياق: قد يرتبط الأمر بـ{p['factors'][1]}، لكن وجود العامل لا يثبت أنه السبب الوحيد.",
        f"اسأل عن الأثر: إذا تأثر النوم أو العمل أو الدراسة أو العلاقات، ابدأ بـ{p['actions'][2]} ثم اطلب تقييمًا عند الاستمرار.",
    ]
    items = "".join(f"<li>{esc(point)}</li>" for point in points)
    return (
        '<section class="article-section context-section" data-quality="enriched-v2">'
        '<h2>كيف تفهم هذا في سياقك؟</h2>'
        f'<ul>{items}</ul>'
        '<p class="micro-note">المعلومة الأكثر فائدة ليست اسم الشعور وحده، بل متى بدأ، وما الذي يزيده، وكيف يغيّر قدرتك على العيش بأمان ومرونة.</p>'
        '</section>'
    )


def main() -> None:
    changed = 0
    for slug, title, kind, _category in TOPICS:
        path = OUT / slug / "index.html"
        text = path.read_text(encoding="utf-8")
        if kind == "five":
            text = enrich_five(text, title)
        elif kind in {"relationship", "habit", "family"}:
            text = enrich_standard(text, title)
        if 'data-quality="enriched-v2"' not in text:
            text = text.replace(
                '<section class="article-section"><h2>خطأ شائع</h2>',
                contextual_section(title) + '<section class="article-section"><h2>خطأ شائع</h2>',
                1,
            )
        path.write_text(text, encoding="utf-8")
        changed += 1
    print({"enriched_pages": changed, "quality_marker": "enriched-v2"})


if __name__ == "__main__":
    main()
