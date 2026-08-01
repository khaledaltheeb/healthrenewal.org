#!/usr/bin/env python3
"""Enforce an H1/H2/H3 hierarchy and visible search-intent answers site-wide.

Every indexable HTML page listed by the sitemap must expose exactly one H1,
at least one H2 and H3, and visible questions matching likely search intent.
The processor is deterministic and only adds a fallback section when an
existing page does not already meet the stronger contract.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://healthrenewal.org"
MARKER = 'data-sitewide-heading-intent="v2"'
QUESTION_MARKERS = ("؟", "ما هو", "ما هي", "كيف ", "متى ", "هل ", "لماذا ", "ما الفرق", "ماذا ")


@dataclass(frozen=True)
class PageStatus:
    url: str
    path: str
    kind: str
    indexable: bool
    h1: int
    h2: int
    h3: int
    questions: int
    minimum_questions: int
    changed: bool = False
    error: str = ""


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.skip_depth = 0
        self.current_heading: tuple[int, list[str]] | None = None
        self.headings: list[tuple[int, str]] = []
        self.visible_parts: list[str] = []
        self.meta_name: dict[str, str] = {}

    @staticmethod
    def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {str(key).lower(): "" if value is None else str(value) for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = self.attrs_dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag in {"script", "style", "template", "svg"}:
            self.skip_depth += 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.current_heading = (int(tag[1]), [])
        if tag == "meta" and data.get("name"):
            self.meta_name[data["name"].lower()] = data.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        if tag in {"script", "style", "template", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if self.current_heading and tag == f"h{self.current_heading[0]}":
            level, parts = self.current_heading
            self.headings.append((level, clean_text(" ".join(parts))))
            self.current_heading = None

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.current_heading is not None:
            self.current_heading[1].append(data)
        if not self.skip_depth:
            value = clean_text(data)
            if value:
                self.visible_parts.append(value)

    @property
    def title(self) -> str:
        return clean_text(" ".join(self.title_parts))

    @property
    def visible_text(self) -> str:
        return clean_text(" ".join(self.visible_parts))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def parse_page(source: str) -> PageParser:
    parser = PageParser()
    parser.feed(source)
    parser.close()
    return parser


def count_questions(parser: PageParser) -> int:
    candidates = [text for _, text in parser.headings]
    candidates.extend(re.split(r"(?<=[؟?!])\s+", parser.visible_text))
    normalized = {clean_text(item) for item in candidates if clean_text(item)}
    return sum(
        1
        for item in normalized
        if "؟" in item or any(item.startswith(marker) for marker in QUESTION_MARKERS[1:])
    )


def classify(url: str) -> str:
    route = urlparse(url).path
    if route.startswith("/family-guide/conditions/"):
        return "family_condition"
    if route.startswith("/magazine/") and route.endswith(".html"):
        return "research_article"
    if "/tools/" in route or route.startswith("/ai-search/"):
        return "tool"
    if route in {"/copyright/", "/accessibility/", "/trust/"}:
        return "governance"
    if route.endswith("/"):
        return "hub"
    return "page"


def minimum_questions(kind: str) -> int:
    return {
        "family_condition": 5,
        "research_article": 4,
        "tool": 3,
        "hub": 2,
        "governance": 2,
        "page": 2,
    }.get(kind, 2)


def first_h1(parser: PageParser) -> str:
    return next((text for level, text in parser.headings if level == 1 and text), parser.title or "هذه الصفحة")


def safe_description(parser: PageParser, label: str) -> str:
    description = clean_text(parser.meta_name.get("description", ""))
    if description:
        return description
    return f"تشرح هذه الصفحة موضوع «{label}» وتربطه بالمسارات والمصادر ذات الصلة داخل المنصة."


def intent_items(kind: str, label: str, description: str) -> list[tuple[str, str]]:
    label = clean_text(label)
    if kind == "family_condition":
        return [
            (f"ما المقصود بـ«{label}»؟", description),
            ("ما العلامات أو الاحتياجات التي تستحق التقييم؟", "تُقرأ العلامات ضمن العمر والسياق والقدرة الوظيفية، ولا تكفي علامة منفردة للتشخيص أو لتحديد شدة الحالة."),
            ("ما الخطوات الأولى التي تساعد الأسرة؟", "ابدأ بتوثيق الملاحظات، وتحديد الأولويات اليومية، وتجهيز الأسئلة، ثم اطلب تقييمًا مهنيًا متعدد التخصصات عند الحاجة."),
            ("كيف تُبنى خطة دعم قابلة للقياس؟", "حوّل الاحتياجات إلى أهداف قصيرة واضحة، وحدد مسؤولية كل طرف، وطريقة قياس التقدم، وموعد مراجعة الخطة وتعديلها."),
            ("متى يلزم طلب مساعدة عاجلة؟", "تُطلب المساعدة العاجلة عند وجود خطر فوري، أو تدهور حاد، أو فقدان مفاجئ للمهارات، أو صعوبة شديدة في التنفس أو الوعي أو الأمان."),
        ]
    if kind == "research_article":
        return [
            (f"ما السؤال الذي تناقشه مادة «{label}»؟", description),
            ("ماذا تعني النتائج عمليًا؟", "تُفسَّر النتائج وفق حجم الأثر وجودة الدراسة والسياق، ولا تُحوَّل مباشرة إلى توصية فردية دون تقييم مهني مناسب."),
            ("ما حدود الدليل المنشور؟", "قد تحد العينة أو مدة المتابعة أو أدوات القياس أو اختلاف السكان من قابلية تعميم النتائج، لذلك يجب قراءة القيود مع الخلاصة."),
            ("كيف أتحقق من المصدر الأصلي؟", "استخدم رابط الدراسة أو المعرّف الرقمي المنشور في الصفحة، ثم راجع المنهج والنتائج والتمويل والتعارضات قبل الاستنتاج."),
        ]
    if kind == "tool":
        return [
            (f"ما وظيفة «{label}»؟", description),
            ("كيف أستخدم الأداة بطريقة صحيحة؟", "جهّز المعلومات المطلوبة، وأدخلها بدقة، ثم اقرأ النتيجة مع الشرح والحدود بدل الاعتماد على رقم أو مخرج منفرد."),
            ("ما حدود نتيجة الأداة؟", "النتيجة تنظيمية أو تثقيفية ولا تستبدل التشخيص أو التقييم أو القرار السريري، ويجب الرجوع إلى مختص عند وجود قلق أو خطر."),
        ]
    if kind == "governance":
        return [
            (f"ما الذي توضحه صفحة «{label}»؟", description),
            ("كيف أتحقق من السياسة أو أبلّغ عن ملاحظة؟", "راجع البنود والتواريخ والروابط الرسمية في الصفحة، ثم استخدم قناة التواصل المعلنة مع وصف واضح للمشكلة أو الطلب."),
            ("متى تُراجع هذه المعلومات؟", "تُراجع عند تغير المتطلبات أو اكتشاف فجوة أو ورود ملاحظة موثقة، ويجب أن تبقى الصياغة قابلة للتدقيق دون ادعاءات غير مثبتة."),
        ]
    if kind == "hub":
        return [
            (f"ماذا ستجد في قسم «{label}»؟", description),
            ("كيف أبدأ من هذا القسم؟", "ابدأ بالمسار الأقرب لسؤالك، واقرأ وصفه قبل الانتقال إلى الصفحة المتخصصة، ثم استخدم الروابط الداخلية لتوسيع الفهم تدريجيًا."),
            ("كيف أختار الصفحة الأكثر صلة بحاجتي؟", "قارن بين نطاق كل مسار والجمهور المقصود والهدف العملي، واختر الصفحة التي تجيب عن سؤالك المحدد بدل تصفح عناوين عامة فقط."),
        ]
    return [
        (f"ما موضوع صفحة «{label}»؟", description),
        ("لمن تفيد هذه الصفحة؟", "تفيد القارئ الذي يبحث عن شرح منظم أو مسار عملي أو مصدر موثوق مرتبط بموضوع الصفحة، مع مراعاة حدود المحتوى المنشور."),
        ("ما الخطوة التالية بعد قراءتها؟", "انتقل إلى الروابط الداخلية الأكثر صلة، وقارن المعلومات بالمصادر الأصلية، واطلب مساعدة مهنية عندما يتطلب القرار تقييمًا فرديًا."),
    ]


def render_section(kind: str, label: str, description: str) -> str:
    parts = [
        f'<section class="seo-intent-answers" {MARKER}>',
        '<h2>أسئلة تساعدك على فهم الصفحة واستخدامها</h2>',
    ]
    for question, answer in intent_items(kind, label, description):
        parts.extend([
            '<article class="seo-intent-answer">',
            f'<h3>{html.escape(question)}</h3>',
            f'<p>{html.escape(answer)}</p>',
            '</article>',
        ])
    parts.append('</section>')
    return "\n".join(parts)


def insert_before_main_end(source: str, section: str) -> str:
    matches = list(re.finditer(r"</main\s*>", source, flags=re.I))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one </main>; found {len(matches)}")
    match = matches[0]
    return source[:match.start()] + "\n" + section + "\n" + source[match.start():]


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
        value = clean_text(node.text)
        parsed = urlparse(value)
        if parsed.netloc != "healthrenewal.org":
            continue
        if parsed.path.endswith(".xml"):
            urls.extend(sitemap_urls(ROOT / unquote(parsed.path.lstrip("/")), seen))
        else:
            urls.append(value)
    return sorted(set(urls))


def url_to_html(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "healthrenewal.org":
        return None
    relative = unquote(parsed.path.lstrip("/"))
    if not relative:
        return ROOT / "index.html"
    if relative.endswith("/"):
        return ROOT / relative / "index.html"
    if relative.endswith(".html"):
        return ROOT / relative
    return None


def status_for(url: str, path: Path, source: str, *, changed: bool = False) -> PageStatus:
    parser = parse_page(source)
    robots = parser.meta_name.get("robots", "").lower()
    indexable = "noindex" not in robots
    levels = [level for level, text in parser.headings if text]
    kind = classify(url)
    return PageStatus(
        url=url,
        path=path.relative_to(ROOT).as_posix(),
        kind=kind,
        indexable=indexable,
        h1=levels.count(1),
        h2=levels.count(2),
        h3=levels.count(3),
        questions=count_questions(parser),
        minimum_questions=minimum_questions(kind),
        changed=changed,
    )


def needs_fallback(status: PageStatus) -> bool:
    return status.indexable and (status.h3 < 1 or status.questions < status.minimum_questions)


def validate_status(status: PageStatus) -> str:
    if not status.indexable:
        return ""
    failures: list[str] = []
    if status.h1 != 1:
        failures.append(f"h1={status.h1}, expected exactly 1")
    if status.h2 < 1:
        failures.append(f"h2={status.h2}, expected at least 1")
    if status.h3 < 1:
        failures.append(f"h3={status.h3}, expected at least 1")
    if status.questions < status.minimum_questions:
        failures.append(f"questions={status.questions}, expected at least {status.minimum_questions}")
    return "; ".join(failures)


def collect(write: bool) -> tuple[list[PageStatus], list[tuple[Path, str]]]:
    entry = ROOT / "sitemap-index.xml"
    if not entry.is_file():
        entry = ROOT / "sitemap.xml"
    statuses: list[PageStatus] = []
    changes: list[tuple[Path, str]] = []
    for url in sitemap_urls(entry):
        path = url_to_html(url)
        if path is None:
            continue
        if not path.is_file():
            statuses.append(PageStatus(url, path.relative_to(ROOT).as_posix(), classify(url), True, 0, 0, 0, 0, minimum_questions(classify(url)), error="missing HTML file"))
            continue
        source = path.read_text(encoding="utf-8")
        before = status_for(url, path, source)
        updated = source
        changed = False
        if needs_fallback(before):
            if MARKER in source:
                statuses.append(PageStatus(**{**asdict(before), "error": "fallback marker exists but contract still fails"}))
                continue
            parser = parse_page(source)
            label = first_h1(parser)
            updated = insert_before_main_end(source, render_section(before.kind, label, safe_description(parser, label)))
            changed = updated != source
        after = status_for(url, path, updated, changed=changed)
        error = validate_status(after)
        if error:
            after = PageStatus(**{**asdict(after), "error": error})
        statuses.append(after)
        if changed:
            changes.append((path, updated))
            if write:
                path.write_text(updated, encoding="utf-8")
    return statuses, changes


def write_report(path: Path, statuses: list[PageStatus]) -> dict[str, object]:
    payload = {
        "contract": "sitewide-heading-search-intent-v2",
        "pages": len(statuses),
        "indexable": sum(item.indexable for item in statuses),
        "changed": sum(item.changed for item in statuses),
        "failed": sum(bool(item.error) for item in statuses),
        "all_indexable_have_exactly_one_h1": all(not item.indexable or item.h1 == 1 for item in statuses),
        "all_indexable_have_h2": all(not item.indexable or item.h2 >= 1 for item in statuses),
        "all_indexable_have_h3": all(not item.indexable or item.h3 >= 1 for item in statuses),
        "all_indexable_meet_question_floor": all(not item.indexable or item.questions >= item.minimum_questions for item in statuses),
        "results": [asdict(item) for item in statuses],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "sitewide-heading-intent-v2.json")
    args = parser.parse_args()
    statuses, changes = collect(write=args.write)
    report = write_report(args.report, statuses)
    print(json.dumps({key: report[key] for key in ("contract", "pages", "indexable", "changed", "failed")}, ensure_ascii=False))
    if report["failed"]:
        return 1
    if args.check and changes:
        for path, _ in changes:
            print(path.relative_to(ROOT))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
