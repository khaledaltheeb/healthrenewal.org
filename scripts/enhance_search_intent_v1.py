#!/usr/bin/env python3
"""Deterministically pre-render high-value search-intent content.

Safe scope:
- family condition pages: render the existing governed data.js content into the
  initial HTML, add visible FAQs, breadcrumbs, matching JSON-LD and hreflang;
- magazine research articles: derive a visible FAQ from already published
  article sections and add matching BreadcrumbList/FAQPage data.

No medical claim is invented. Every generated answer is copied from existing
page data/content or is a fixed safety statement.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://healthrenewal.org"
FAMILY_ROOT = ROOT / "family-guide" / "conditions"
MAGAZINE_ROOT = ROOT / "magazine"
MARKER = 'data-search-intent-prerender="v1"'
FAQ_MARKER = 'data-search-intent-faq="v1"'


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def list_html(items: Iterable[object], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{esc(item)}</li>" for item in items) + f"</{tag}>"


def parse_family_data(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    start = text.rfind("})(")
    if start < 0 or not text.endswith(");"):
        raise RuntimeError(f"Unsupported family data wrapper: {path}")
    payload = text[start + 3 : -2]
    value = json.loads(payload)
    required = {"slug", "title", "en", "classification", "summary", "signs", "questions", "sources"}
    missing = sorted(required - value.keys())
    if missing:
        raise RuntimeError(f"Family data is missing {missing}: {path}")
    return value


def faq_for_family(c: dict) -> list[tuple[str, str]]:
    signs: list[str] = []
    for values in c.get("signs", {}).values():
        signs.extend(values[:1])
    first = " ".join(c.get("first_steps", [])[:3])
    avoid = " ".join(c.get("avoid", [])[:3])
    urgent = " ".join(c.get("urgent", []))
    questions = " ".join(c.get("questions", []))
    return [
        (f"ما هو {c['title']}؟", c["summary"]),
        (f"ما العلامات التي تستحق التقييم في {c['title']}؟", " ".join(signs) or c["summary"]),
        (f"ما أول خطوات الأسرة عند الاشتباه بـ{c['title']}؟", first or "ابدأ بتوثيق الملاحظات واطلب تقييمًا مهنيًا مناسبًا."),
        (f"ما الذي يجب تجنبه عند التعامل مع {c['title']}؟", avoid or "تجنب التشخيص الذاتي والوعود غير المدعومة وتغيير العلاج دون مختص."),
        ("متى نطلب مساعدة عاجلة؟", urgent or "اطلب مساعدة عاجلة عند وجود خطر مباشر أو تغير صحي حاد."),
        ("ما الأسئلة التي نطرحها على المختص؟", questions or "اسأل عن أساس التقييم والأهداف الوظيفية وطريقة قياس التقدم وحدود الخطة."),
    ]


def family_faq_html(c: dict) -> str:
    items = faq_for_family(c)
    return (
        f'<section class="card intent-faq" id="faq" {FAQ_MARKER}><p class="kicker">11</p>'
        f'<h2>أسئلة شائعة عن {esc(c["title"])}</h2>'
        + "".join(f'<article class="faq-item"><h3>{esc(question)}</h3><p>{esc(answer)}</p></article>' for question, answer in items)
        + "</section>"
    )


def family_graph(c: dict, url: str, reviewed_at: str) -> dict:
    faq = faq_for_family(c)
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "MedicalWebPage",
                "@id": url + "#webpage",
                "name": f"دليل الأسرة: {c['title']}",
                "url": url,
                "inLanguage": "ar",
                "dateModified": reviewed_at,
                "description": c["summary"],
                "about": {"@type": "MedicalCondition", "name": c["title"], "alternateName": c["en"]},
                "isPartOf": {"@type": "CollectionPage", "name": "دليل الأسرة للرعاية والدعم", "url": ORIGIN + "/family-guide/"},
                "breadcrumb": {"@id": url + "#breadcrumb"},
                "mainEntity": {"@id": url + "#faq"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": ORIGIN + "/"},
                    {"@type": "ListItem", "position": 2, "name": "دليل الأسرة", "item": ORIGIN + "/family-guide/"},
                    {"@type": "ListItem", "position": 3, "name": c["title"], "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": [
                    {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in faq
                ],
            },
        ],
    }


def section(identifier: str, number: str, title: str, body: str, cls: str = "") -> str:
    return f'<section class="card {cls}" id="{identifier}"><p class="kicker">{number}</p><h2>{esc(title)}</h2>{body}</section>'


def family_main(c: dict) -> str:
    signs = "".join(f"<h3>{esc(group)}</h3>{list_html(items)}" for group, items in c.get("signs", {}).items())
    related = "".join(f'<li><a href="{esc(url)}">{esc(name)}</a></li>' for name, url in c.get("related", []))
    sources = "".join(f'<li><a href="{esc(url)}" rel="external noopener noreferrer">{esc(name)}</a></li>' for name, url in c.get("sources", []))
    content = [
        f'<main id="condition-root" aria-busy="false" {MARKER}>',
        '<nav class="wrap breadcrumbs" aria-label="مسار التنقل"><a href="../../../">الرئيسية</a> <span aria-hidden="true">/</span> <a href="../../">دليل الأسرة</a> <span aria-hidden="true">/</span> <span aria-current="page">' + esc(c["title"]) + "</span></nav>",
        f'<section class="hero"><div class="wrap"><p class="kicker">دليل الأسرة حسب الحالة</p><h1>{esc(c["title"])}</h1><p class="lead">{esc(c["summary"])}</p><div class="toolbar"><a class="button" href="../../">العودة إلى دليل الأسرة</a><button type="button" onclick="window.print()">طباعة الدليل</button></div><p class="notice"><b>تنبيه:</b> هذه الصفحة تساعد على فهم الخطوات وتنظيم الأسئلة، ولا تثبت التشخيص ولا تحدد علاجًا أو دواءً لشخص بعينه. الأعراض المفاجئة أو الخطر المباشر تستلزم خدمة طبية أو طوارئ مناسبة.</p></div></section>',
        '<div class="wrap layout"><aside class="toc"><h2>المحتويات</h2>' + "".join(f'<a href="#{key}">{label}</a>' for key, label in (("summary", "الملخص"), ("signs", "العلامات"), ("causes", "الأسباب"), ("related", "الأقسام المرتبطة"), ("first", "ماذا نفعل أولًا؟"), ("avoid", "ما الذي نتجنبه؟"), ("daily", "التعامل اليومي"), ("plan", "الخطة الزمنية"), ("team", "الفريق والأسئلة"), ("faq", "الأسئلة الشائعة"), ("urgent", "علامات عاجلة"), ("sources", "المراجع"))) + '</aside><article class="stack">',
        section("summary", "1", "ما الحالة؟", f'<p><span class="tag">{esc(c["classification"])}</span></p><p>{esc(c["summary"])}</p><div class="summary-grid"><div><b>الهدف الأول</b><p>فهم أثر الحالة في الشخص نفسه، لا الاكتفاء باسم التشخيص.</p></div><div><b>القاعدة</b><p>ابدأ بالأمان والتواصل والصحة والمشاركة ثم رتّب بقية الأهداف.</p></div><div><b>القياس</b><p>حدد خط أساس، هدفًا وظيفيًا، مدة تجربة، ومراجعة مكتوبة.</p></div></div>'),
        section("signs", "2", "العلامات والأعراض المحتملة", signs),
        section("causes", "3", "الأسباب وما نعرفه علميًا", list_html(c.get("causes", []))),
        section("related", "4", "الأقسام ذات الصلة المباشرة", f'<ul>{related}</ul><p class="small">وجود رابط لحالة مصاحبة لا يعني أنها موجودة لدى كل شخص؛ كل مجال يحتاج تقييمًا مستقلًا عند ظهور مؤشرات.</p>'),
        section("first", "5", "ماذا تفعل الأسرة أولًا؟", list_html(c.get("first_steps", []), ordered=True), "good"),
        section("avoid", "6", "ما الذي يجب تجنبه؟", list_html(c.get("avoid", [])), "warning"),
        section("daily", "7", "كيف نتصرف في الحياة اليومية؟", list_html(c.get("daily", []))),
        section("plan", "8", "أفضل خطة عملية زمنية", f'<div class="columns"><div><h3>أول 30 يومًا</h3>{list_html(c.get("plan30", []))}</div><div><h3>خلال 90 يومًا</h3>{list_html(c.get("plan90", []))}</div></div><h3>خلال عام</h3>{list_html(c.get("plan_year", []))}', "rights"),
        section("team", "9", "الفريق والأسئلة التي تطرح عليه", f'<div class="columns"><div><h3>اختصاصات قد تدخل في الخطة</h3>{list_html(c.get("professionals", []))}</div><div><h3>أسئلة للمختص</h3>{list_html(c.get("questions", []))}</div></div>'),
        family_faq_html(c),
        section("urgent", "12", "متى نطلب مساعدة عاجلة؟", list_html(c.get("urgent", [])), "warning"),
        f'<section class="source-box" id="sources"><h2>المراجع الأساسية</h2><ul>{sources}</ul><p class="small">تُراجع التوصيات عند تحديث المصدر أو تغير الإرشادات.</p></section>',
        "</article></div></main>",
    ]
    return "".join(content)


def ensure_hreflang(source: str, url: str) -> str:
    canonical = f'<link rel="canonical" href="{url}">'
    if canonical not in source:
        raise RuntimeError(f"Canonical link not found for {url}")
    additions: list[str] = []
    if 'hreflang="ar"' not in source:
        additions.append(f'<link rel="alternate" hreflang="ar" href="{url}">')
    if 'hreflang="x-default"' not in source:
        additions.append(f'<link rel="alternate" hreflang="x-default" href="{url}">')
    if additions:
        source = source.replace(canonical, canonical + "".join(additions), 1)
    return source


def remove_meta_keywords(source: str) -> str:
    return re.sub(r"\s*<meta\s+name=[\"']keywords[\"'][^>]*>\s*", "\n", source, flags=re.I)


def replace_first_jsonld(source: str, payload: dict) -> str:
    replacement = '<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "</script>"
    updated, count = re.subn(r'<script\s+type=["\']application/ld\+json["\'][^>]*>.*?</script>', lambda _: replacement, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Expected exactly one primary JSON-LD block")
    return updated


def replace_main(source: str, rendered: str) -> str:
    updated, count = re.subn(r'<main\b[^>]*id=["\']condition-root["\'][^>]*>.*?</main>', lambda _: rendered, source, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Could not locate condition-root main element")
    return updated


def enhance_family(path: Path, reviewed_at: str) -> str:
    source = path.read_text(encoding="utf-8")
    data = parse_family_data(path.with_name("data.js"))
    url = f"{ORIGIN}/family-guide/conditions/{data['slug']}/"
    source = remove_meta_keywords(source)
    source = ensure_hreflang(source, url)
    source = replace_first_jsonld(source, family_graph(data, url, reviewed_at))
    source = replace_main(source, family_main(data))
    return source


@dataclass
class ArticleExtract:
    lead: str = ""
    sections: dict[str, list[str]] | None = None


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.current_h2: list[str] | None = None
        self.section_name = ""
        self.current_text: list[str] | None = None
        self.current_tag = ""
        self.lead = ""
        self.sections: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k: "" if v is None else v for k, v in attrs}
        self.stack.append(tag)
        if tag == "h2":
            self.current_h2 = []
        if tag in {"p", "li"}:
            self.current_text = []
            self.current_tag = tag
        if tag == "p" and "lead" in data.get("class", "").split():
            self.current_tag = "lead"

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self.current_h2 is not None:
            self.section_name = clean(" ".join(self.current_h2))
            self.sections.setdefault(self.section_name, [])
            self.current_h2 = None
        if tag in {"p", "li"} and self.current_text is not None:
            text = clean(" ".join(self.current_text))
            if text:
                if self.current_tag == "lead" and not self.lead:
                    self.lead = text
                elif self.section_name:
                    self.sections.setdefault(self.section_name, []).append(text)
            self.current_text = None
            self.current_tag = ""
        if self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.current_h2 is not None:
            self.current_h2.append(data)
        if self.current_text is not None:
            self.current_text.append(data)


def pick_section(sections: dict[str, list[str]], words: tuple[str, ...]) -> str:
    for heading, values in sections.items():
        if any(word in heading for word in words) and values:
            return " ".join(values[:4])
    return ""


def magazine_faq(source: str, title: str) -> list[tuple[str, str]]:
    parser = ArticleParser()
    parser.feed(source)
    summary = pick_section(parser.sections, ("الخلاصة", "الملخص", "النتائج الأساسية", "ماذا وجدت"))
    limits = pick_section(parser.sections, ("حدود", "القيود", "نقاط الضعف"))
    practical = pick_section(parser.sections, ("الدلالة العملية", "ماذا تعني", "التطبيق", "الاستنتاج"))
    lead = parser.lead or summary
    return [
        ("ماذا بحثت هذه الدراسة؟", lead or f"تبحث الصفحة موضوع: {title}."),
        ("ما النتيجة الرئيسية؟", summary or "تعرض الصفحة النتيجة الرئيسة مع تفسيرها وحدودها."),
        ("ما أهم حدود الدليل؟", limits or "لا تُقرأ النتائج دون مراعاة تصميم الدراسة والعينة والتباين واحتمال التحيز."),
        ("ماذا تعني النتائج عمليًا؟", practical or "تُستخدم النتائج لفهم الدليل، لا لاختيار علاج فردي دون تقييم مهني."),
        ("هل تكفي هذه الدراسة لاختيار علاج لشخص بعينه؟", "لا. تلخص الصفحة دليلًا بحثيًا عامًا ولا تستبدل التقييم المهني أو قرارًا علاجيًا فرديًا."),
    ]


def magazine_faq_html(items: list[tuple[str, str]]) -> str:
    return (
        f'<section class="intent-faq" {FAQ_MARKER}><h2>أسئلة شائعة حول الدراسة</h2>'
        + "".join(f'<article class="faq-item"><h3>{esc(q)}</h3><p>{esc(a)}</p></article>' for q, a in items)
        + "</section>"
    )


def article_title(source: str) -> str:
    match = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, flags=re.I | re.S)
    return clean(re.sub(r"<[^>]+>", " ", match.group(1))) if match else "الدراسة"


def canonical_url(source: str) -> str:
    match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)', source, flags=re.I)
    if not match:
        raise RuntimeError("Magazine article is missing canonical")
    return match.group(1)


def magazine_graph(title: str, url: str, items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": ORIGIN + "/"},
                    {"@type": "ListItem", "position": 2, "name": "المجلة والأبحاث", "item": ORIGIN + "/magazine/"},
                    {"@type": "ListItem", "position": 3, "name": title, "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items],
            },
        ],
    }


def enhance_magazine(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    title = article_title(source)
    url = canonical_url(source)
    items = magazine_faq(source, title)
    source = remove_meta_keywords(source)
    source = ensure_hreflang(source, url)
    source = re.sub(r'<meta\s+property=["\']og:type["\']\s+content=["\']website["\']\s*>', '<meta property="og:type" content="article">', source, flags=re.I)
    faq_html = magazine_faq_html(items)
    if FAQ_MARKER in source:
        source = re.sub(r'<section\b[^>]*data-search-intent-faq=["\']v1["\'][^>]*>.*?</section>', lambda _: faq_html, source, count=1, flags=re.I | re.S)
    else:
        source, count = re.subn(r"</article>", faq_html + "</article>", source, count=1, flags=re.I)
        if count != 1:
            raise RuntimeError(f"Could not locate article end in {path}")
    extra = '<script type="application/ld+json" data-search-intent-schema="v1">' + json.dumps(magazine_graph(title, url, items), ensure_ascii=False, separators=(",", ":")) + "</script>"
    if 'data-search-intent-schema="v1"' in source:
        source = re.sub(r'<script\s+type=["\']application/ld\+json["\']\s+data-search-intent-schema=["\']v1["\']>.*?</script>', lambda _: extra, source, count=1, flags=re.I | re.S)
    else:
        source = source.replace("</head>", extra + "\n</head>", 1)
    return source


def patch_family_ui(source: str) -> str:
    if "function faqItems(c)" not in source:
        needle = "function section(id,num,title,body,cls=''){return `<section class=\"card ${cls}\" id=\"${id}\"><p class=\"kicker\">${num}</p><h2>${esc(title)}</h2>${body}</section>`;}"
        insertion = needle + r'''
function faqItems(c){const signs=Object.values(c.signs||{}).flatMap(v=>v.slice(0,1)).join(' ');return [[`ما هو ${c.title}؟`,c.summary],[`ما العلامات التي تستحق التقييم في ${c.title}؟`,signs||c.summary],[`ما أول خطوات الأسرة عند الاشتباه بـ${c.title}؟`,(c.first_steps||[]).slice(0,3).join(' ')],[`ما الذي يجب تجنبه عند التعامل مع ${c.title}؟`,(c.avoid||[]).slice(0,3).join(' ')],['متى نطلب مساعدة عاجلة؟',(c.urgent||[]).join(' ')],['ما الأسئلة التي نطرحها على المختص؟',(c.questions||[]).join(' ')]];}
function faqSection(c){return `<section class="card intent-faq" id="faq" data-search-intent-faq="v1"><p class="kicker">11</p><h2>أسئلة شائعة عن ${esc(c.title)}</h2>${faqItems(c).map(([q,a])=>`<article class="faq-item"><h3>${esc(q)}</h3><p>${esc(a)}</p></article>`).join('')}</section>`;}
'''

        if needle not in source:
            raise RuntimeError("Family UI section helper changed; update enhancer contract")
        source = source.replace(needle, insertion, 1)
    source = source.replace("['team','الفريق والأسئلة'],['urgent'", "['team','الفريق والأسئلة'],['faq','الأسئلة الشائعة'],['urgent'", 1)
    if "${faqSection(c)}" not in source:
        target = "${section('team','9','الفريق والأسئلة التي تطرح عليه',`<div class=\"columns\"><div><h3>اختصاصات قد تدخل في الخطة</h3>${list(c.professionals)}</div><div><h3>أسئلة للمختص</h3>${list(c.questions)}</div></div>`)}"
        if target not in source:
            raise RuntimeError("Family UI team section changed; update enhancer contract")
        source = source.replace(target, target + "\n ${faqSection(c)}", 1)
    return source


def iter_family_pages() -> Iterable[Path]:
    for path in sorted(FAMILY_ROOT.glob("*/index.html")):
        if not path.with_name("data.js").is_file():
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(r'<meta\s+name=["\']robots["\'][^>]*noindex', source, flags=re.I):
            continue
        yield path


def iter_magazine_pages() -> Iterable[Path]:
    for path in sorted(MAGAZINE_ROOT.glob("*.html")):
        if path.name == "index.html":
            continue
        source = path.read_text(encoding="utf-8")
        if "ScholarlyArticle" in source or "مراجعة" in source or "دراسة" in source:
            yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    reviewed_at = "2026-08-01"
    changes: list[tuple[Path, str]] = []
    for path in iter_family_pages():
        updated = enhance_family(path, reviewed_at)
        if updated != path.read_text(encoding="utf-8"):
            changes.append((path, updated))
    for path in iter_magazine_pages():
        updated = enhance_magazine(path)
        if updated != path.read_text(encoding="utf-8"):
            changes.append((path, updated))
    family_index = ROOT / "family-guide" / "index.html"
    if family_index.is_file():
        family_index_source = family_index.read_text(encoding="utf-8")
        family_index_updated = remove_meta_keywords(family_index_source)
        if family_index_updated != family_index_source:
            changes.append((family_index, family_index_updated))

    ui = ROOT / "family-guide" / "family-guide-ui.js"
    ui_updated = patch_family_ui(ui.read_text(encoding="utf-8"))
    if ui_updated != ui.read_text(encoding="utf-8"):
        changes.append((ui, ui_updated))

    if args.check and changes:
        for path, _ in changes[:50]:
            print(f"NEEDS_REGENERATION {path.relative_to(ROOT)}")
        print(f"Search-intent generated surface is stale: {len(changes)} files", flush=True)
        return 1
    if args.write:
        for path, updated in changes:
            path.write_text(updated, encoding="utf-8")
    print(json.dumps({"status": "passed", "mode": "write" if args.write else "check", "changed": len(changes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
