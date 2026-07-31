#!/usr/bin/env python3
"""Apply deterministic semantic fixes to static hubs and sitemap HTML pages."""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://healthrenewal.org"


def sitemap_urls(path: Path, seen: set[Path] | None = None) -> list[str]:
    seen = seen or set()
    path = path.resolve()
    if path in seen or not path.is_file():
        return []
    seen.add(path)
    root = ET.parse(path).getroot()
    urls: list[str] = []
    for node in root.iter():
        if not node.tag.endswith("loc") or not node.text:
            continue
        value = node.text.strip()
        parsed = urlparse(value)
        if parsed.path.endswith(".xml"):
            urls.extend(sitemap_urls(ROOT / unquote(parsed.path.lstrip("/")), seen))
        elif value.startswith(ORIGIN):
            urls.append(value)
    return urls


def url_to_html(url: str) -> Path | None:
    parsed = urlparse(url)
    relative = unquote(parsed.path.lstrip("/"))
    if not relative:
        return ROOT / "index.html"
    if relative.endswith("/"):
        return ROOT / relative / "index.html"
    if relative.endswith(".html"):
        return ROOT / relative
    return None


def remove_meta_keywords(source: str) -> str:
    return re.sub(r"\s*<meta\s+name=[\"']keywords[\"'][^>]*>\s*", "\n", source, flags=re.I)


def insert_once(source: str, marker: str, needle: str, addition: str, *, after: bool = True) -> str:
    if marker in source:
        return source
    if needle not in source:
        raise RuntimeError(f"Static SEO insertion point not found for marker {marker}")
    replacement = needle + addition if after else addition + needle
    return source.replace(needle, replacement, 1)


def patch_special_needs(source: str) -> str:
    marker = 'data-semantic-heading="special-needs-v1"'
    return insert_once(
        source,
        marker,
        "<h2>الإنسان قبل الوصف</h2>",
        '<h3 data-semantic-heading="special-needs-v1">كيف نختار لغة تحترم الشخص واحتياجاته؟</h3>',
    )


def patch_trust(source: str) -> str:
    marker = 'data-semantic-heading="trust-v1"'
    return insert_once(
        source,
        marker,
        "<h2>الغرض والنطاق</h2>",
        '<h3 data-semantic-heading="trust-v1">ما السؤال الذي تجيب عنه الصفحة وما نوع المصدر الملائم له؟</h3>',
    )


def patch_outside_box(source: str) -> str:
    marker = 'data-search-intent-hub="outside-box-v1"'
    block = (
        f'<section class="wrap" {marker} aria-labelledby="outside-method">'
        '<article class="card"><h2 id="outside-method">كيف تستخدم موارد «خارج الصندوق»؟</h2>'
        '<h3>ابدأ بالسؤال لا بجاذبية الفكرة</h3>'
        '<p>حدد المشكلة أو القرار الذي تريد فهمه، ثم اختر المورد الذي يشرح معيار الدليل أو منهجية التحقق أو الدراسة الأصلية. '
        'لا تعامل الفكرة الجديدة على أنها أفضل لمجرد اختلافها؛ قيم صلاحية المصدر للسؤال، وجودة التنفيذ، وحجم الفائدة والضرر، '
        'وإمكان تطبيق النتيجة في السياق العربي أو الخدمي المقصود.</p>'
        '<h3>افصل الاستكشاف عن التوصية</h3>'
        '<p>قد تكون الفكرة مناسبة للبحث أو النقاش دون أن تكون جاهزة للتطبيق المهني. ارجع إلى صفحة الثقة والمنهجية، '
        'وتحقق من الروابط الأصلية، وقارن النتيجة بجسم الدليل والإرشادات. في القرارات الصحية أو التعليمية الفردية، '
        'استخدم هذه الموارد لصياغة أسئلة أفضل لا لاستبدال التقييم المتخصص.</p></article></section>'
    )
    return insert_once(source, marker, '<section class="wrap">\n<div class="grid">', block, after=False)


def patch_team(source: str) -> str:
    marker = 'data-search-intent-hub="team-partners-v1"'
    block = (
        f'<section class="wrap" {marker} aria-labelledby="partner-governance">'
        '<article class="card"><h2 id="partner-governance">كيف تعمل شبكة المختصين والشركاء؟</h2>'
        '<h3>ما الذي يعنيه الظهور في الدليل؟</h3>'
        '<p>يعرض الدليل معلومات مهنية منظمة تساعد المستخدم على المقارنة والتواصل، ولا يعد اعتمادًا علاجيًا مطلقًا أو ضمانًا للنتائج. '
        'يجب أن يوضح الملف التخصص والمؤهل والمنطقة وطريقة الخدمة وحالة التحقق، وأن تبقى القرارات الصحية والتعليمية مسؤولية '
        'المختص المؤهل والمستخدم وفق القوانين والسياسات المعمول بها.</p>'
        '<h3>كيف تتم الشراكة أو الإضافة؟</h3>'
        '<p>يبدأ المسار بطلب منظم ومراجعة البيانات والوثائق وحدود النشر، ثم تحديد نوع التعاون والمسؤوليات وطريقة تحديث المعلومات. '
        'لا تنشر المنصة بيانات حساسة بلا حاجة، وتوفر مسارًا للإبلاغ عن معلومات قديمة أو مضللة. يمكن للمختص أو الجهة فتح صفحة '
        'الانضمام لمعرفة الحقول المطلوبة، ثم مراجعة سياسة التحقق والخصوصية قبل الإرسال.</p></article></section>'
    )
    return insert_once(source, marker, '<section class="wrap"><div class="grid">', block, after=False)


def patch_file(path: Path, source: str) -> str:
    source = remove_meta_keywords(source)
    relative = path.relative_to(ROOT).as_posix()
    if relative == "special-needs/index.html":
        source = patch_special_needs(source)
    elif relative == "trust/index.html":
        source = patch_trust(source)
    elif relative == "outside-the-box/index.html":
        source = patch_outside_box(source)
    elif relative == "team-and-partners/index.html":
        source = patch_team(source)
    return source


def collect_changes() -> list[tuple[Path, str]]:
    index = ROOT / "sitemap-index.xml"
    if not index.is_file():
        index = ROOT / "sitemap.xml"
    paths = {path for url in sitemap_urls(index) if (path := url_to_html(url)) and path.is_file()}
    for relative in (
        "special-needs/index.html",
        "trust/index.html",
        "outside-the-box/index.html",
        "team-and-partners/index.html",
    ):
        path = ROOT / relative
        if path.is_file():
            paths.add(path)

    changes: list[tuple[Path, str]] = []
    for path in sorted(paths):
        current = path.read_text(encoding="utf-8")
        updated = patch_file(path, current)
        if updated != current:
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
        for path, _ in changes:
            print(path.relative_to(ROOT))
        return 1 if changes else 0

    for path, content in changes:
        path.write_text(content, encoding="utf-8")
    print(f"Updated {len(changes)} static sitemap pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
