#!/usr/bin/env python3
"""Enforce semantic heading hierarchy and visible search-intent answers.

The contract can audit either the repository source tree or an independently
materialized deployment artifact. Every indexable HTML page listed by the
selected sitemap must expose exactly one H1, at least one H2 and H3, and a
minimum number of visible question-and-answer pairs appropriate to its route.
The deterministic fallback only modifies pages that do not already comply.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, replace
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URLS = ("https://healthrenewal.org/",)
MARKER = 'data-sitewide-heading-intent="v2"'
QUESTION_PREFIXES = ("ما هو", "ما هي", "كيف ", "متى ", "هل ", "لماذا ", "ما الفرق", "ماذا ", "لمن ")
CAPABILITY_HUBS = {"", "expanded", "methodology", "protocol", "registry"}


@dataclass(frozen=True)
class PageTarget:
    url: str
    route: str
    path: Path


@dataclass(frozen=True)
class PageStatus:
    url: str
    route: str
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
        if "؟" in item or any(item.startswith(prefix) for prefix in QUESTION_PREFIXES)
    )


def normalize_base_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {value}")
    base_path = parsed.path or "/"
    if not base_path.endswith("/"):
        base_path += "/"
    return parsed.netloc.lower(), base_path


def relative_route(url: str, base_urls: tuple[str, ...]) -> str | None:
    parsed = urlparse(url)
    for base_url in base_urls:
        host, base_path = normalize_base_url(base_url)
        if parsed.netloc.lower() != host or not parsed.path.startswith(base_path):
            continue
        relative = unquote(parsed.path[len(base_path):]).lstrip("/")
        return "/" + relative
    return None


def classify(route: str) -> str:
    normalized = "/" + route.lstrip("/")
    if normalized.startswith("/family-guide/conditions/"):
        return "family_condition"
    if normalized.startswith("/magazine/") and normalized.endswith(".html"):
        return "research_article"
    if "/tools/" in normalized or normalized.startswith("/ai-search/"):
        return "tool"
    if normalized in {"/copyright/", "/accessibility/", "/trust/"}:
        return "governance"
    if normalized.startswith("/capabilities/"):
        parts = [part for part in normalized.strip("/").split("/") if part]
        slug = parts[1] if len(parts) > 1 else ""
        if slug not in CAPABILITY_HUBS:
            return "capability_condition"
        return "capability_hub"
    if normalized.endswith("/"):
        return "hub"
    return "page"


def minimum_questions(kind: str) -> int:
    return {
        "family_condition": 5,
        "capability_condition": 5,
        "research_article": 4,
        "tool": 3,
        "capability_hub": 3,
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
            ("ما الخطوات الأولى التي تساعد الأسرة؟", "ابدأ بتوثيق الملاحظات وتحديد الأولويات اليومية وتجهيز الأسئلة، ثم اطلب تقييمًا مهنيًا متعدد التخصصات عند الحاجة."),
            ("كيف تُبنى خطة دعم قابلة للقياس؟", "حوّل الاحتياجات إلى أهداف قصيرة واضحة، وحدد مسؤولية كل طرف وطريقة قياس التقدم وموعد مراجعة الخطة وتعديلها."),
            ("متى يلزم طلب مساعدة عاجلة؟", "تُطلب المساعدة العاجلة عند وجود خطر فوري أو تدهور حاد أو فقدان مفاجئ للمهارات أو صعوبة شديدة في التنفس أو الوعي أو الأمان."),
        ]
    if kind == "capability_condition":
        return [
            (f"ما المقصود بدليل «{label}»؟", description),
            ("ما الذي ينبغي تقييمه قبل بناء خطة دعم؟", "ابدأ بالصحة والأمان والتواصل والوصول والأداء الفعلي في البيئات المهمة، ولا تستنتج القدرة أو الاستقلال من اسم الحالة وحده."),
            ("كيف تُختبر القدرة أو فائدة التكييف بأمان؟", "استخدم مهمة قصيرة ذات هدف واضح، وغيّر عامل وصول واحدًا فقط، وسجّل الدقة والاستقلال والتعب والرغبة في التكرار عبر أكثر من محاولة."),
            ("ما الحدود التي تمنع التفسير المبالغ فيه؟", "لا تُعمّم نتيجة تجربة قصيرة على الذكاء أو المستقبل، ولا تنسب أداء الشريك أو الأداة إلى الشخص، ولا تجعل الألم أو الخطر أو الإجبار دليل نجاح."),
            ("متى يجب إيقاف التجربة وطلب مساعدة؟", "تتوقف التجربة عند الرفض أو الألم أو التدهور أو الخطر أو زيادة الأعراض، وتُطلب المساعدة المهنية أو الطارئة بحسب شدة الحالة وخطة الأمان المعتمدة."),
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
            ("كيف أستخدم الأداة بطريقة صحيحة؟", "جهّز المعلومات المطلوبة وأدخلها بدقة، ثم اقرأ النتيجة مع الشرح والحدود بدل الاعتماد على رقم أو مخرج منفرد."),
            ("ما حدود نتيجة الأداة؟", "النتيجة تنظيمية أو تثقيفية ولا تستبدل التشخيص أو التقييم أو القرار السريري، ويجب الرجوع إلى مختص عند وجود قلق أو خطر."),
        ]
    if kind == "governance":
        return [
            (f"ما الذي توضحه صفحة «{label}»؟", description),
            ("كيف أتحقق من السياسة أو أبلّغ عن ملاحظة؟", "راجع البنود والتواريخ والروابط الرسمية في الصفحة، ثم استخدم قناة التواصل المعلنة مع وصف واضح للمشكلة أو الطلب."),
            ("متى تُراجع هذه المعلومات؟", "تُراجع عند تغير المتطلبات أو اكتشاف فجوة أو ورود ملاحظة موثقة، ويجب أن تبقى الصياغة قابلة للتدقيق دون ادعاءات غير مثبتة."),
        ]
    if kind in {"hub", "capability_hub"}:
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
    line_start = source.rfind("\n", 0, match.start()) + 1
    leading = source[line_start:match.start()]
    if leading.strip():
        insertion_at = match.start()
        indent = ""
    else:
        insertion_at = line_start
        indent = leading
    rendered = "\n".join((indent + line).rstrip() for line in section.splitlines())
    prefix = source[:insertion_at]
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + rendered + "\n" + source[insertion_at:]


def url_to_local(url: str, root: Path, base_urls: tuple[str, ...]) -> tuple[Path, str] | None:
    route = relative_route(url, base_urls)
    if route is None:
        return None
    relative = route.lstrip("/")
    if not relative:
        return root / "index.html", "/"
    if relative.endswith(".xml"):
        return root / relative, route
    if relative.endswith("/"):
        return root / relative / "index.html", route
    if relative.endswith(".html"):
        return root / relative, route
    return None


def sitemap_urls(root: Path, sitemap: Path, base_urls: tuple[str, ...], seen: set[Path] | None = None) -> list[str]:
    seen = seen or set()
    sitemap = sitemap.resolve()
    if sitemap in seen or not sitemap.is_file():
        return []
    seen.add(sitemap)
    document = ET.parse(sitemap).getroot()
    urls: list[str] = []
    for node in document.iter():
        if not node.tag.endswith("loc") or not node.text:
            continue
        value = clean_text(node.text)
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.path.endswith(".xml"):
            resolved = url_to_local(value, root, base_urls)
            if resolved is not None:
                urls.extend(sitemap_urls(root, resolved[0], base_urls, seen))
        else:
            urls.append(value)
    return sorted(set(urls))


def discover_targets(root: Path, sitemap: Path, base_urls: tuple[str, ...]) -> tuple[list[PageTarget], list[str]]:
    targets: list[PageTarget] = []
    unsupported: list[str] = []
    for url in sitemap_urls(root, sitemap, base_urls):
        resolved = url_to_local(url, root, base_urls)
        if resolved is None:
            suffix = Path(urlparse(url).path).suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif", ".ico", ".json", ".csv", ".txt", ".pdf"}:
                continue
            unsupported.append(url)
            continue
        path, route = resolved
        if path.suffix.lower() == ".html":
            targets.append(PageTarget(url=url, route=route, path=path))
    return targets, unsupported


def status_for(root: Path, target: PageTarget, source: str, *, changed: bool = False) -> PageStatus:
    parser = parse_page(source)
    robots = parser.meta_name.get("robots", "").lower()
    indexable = "noindex" not in robots
    levels = [level for level, text in parser.headings if text]
    kind = classify(target.route)
    return PageStatus(
        url=target.url,
        route=target.route,
        path=target.path.relative_to(root).as_posix(),
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


def collect(root: Path, sitemap: Path, base_urls: tuple[str, ...], *, write: bool) -> tuple[list[PageStatus], list[Path], list[str]]:
    statuses: list[PageStatus] = []
    changed_paths: list[Path] = []
    targets, unsupported = discover_targets(root, sitemap, base_urls)
    for target in targets:
        if not target.path.is_file():
            statuses.append(PageStatus(
                url=target.url,
                route=target.route,
                path=target.path.relative_to(root).as_posix(),
                kind=classify(target.route),
                indexable=True,
                h1=0,
                h2=0,
                h3=0,
                questions=0,
                minimum_questions=minimum_questions(classify(target.route)),
                error="missing HTML file",
            ))
            continue
        source = target.path.read_text(encoding="utf-8")
        before = status_for(root, target, source)
        updated = source
        changed = False
        if needs_fallback(before):
            if MARKER in source:
                statuses.append(replace(before, error="fallback marker exists but contract still fails"))
                continue
            parser = parse_page(source)
            label = first_h1(parser)
            try:
                updated = insert_before_main_end(source, render_section(before.kind, label, safe_description(parser, label)))
            except RuntimeError as exc:
                statuses.append(replace(before, error=str(exc)))
                continue
            changed = updated != source
        after = status_for(root, target, updated, changed=changed)
        error = validate_status(after)
        if error:
            after = replace(after, error=error)
        statuses.append(after)
        if changed:
            changed_paths.append(target.path)
            if write:
                target.path.write_text(updated, encoding="utf-8")
    return statuses, changed_paths, unsupported


def default_sitemap(root: Path) -> Path:
    index = root / "sitemap-index.xml"
    return index if index.is_file() else root / "sitemap.xml"


def write_report(path: Path, statuses: list[PageStatus], *, applied: int, unsupported: list[str], root: Path, sitemap: Path, base_urls: tuple[str, ...]) -> dict[str, object]:
    payload = {
        "contract": "sitewide-heading-search-intent-v2",
        "root": str(root),
        "sitemap": str(sitemap),
        "base_urls": list(base_urls),
        "pages": len(statuses),
        "indexable": sum(item.indexable for item in statuses),
        "applied": applied,
        "changed": sum(item.changed for item in statuses),
        "failed": sum(bool(item.error) for item in statuses),
        "unsupported_urls": unsupported,
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
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--sitemap", type=Path)
    parser.add_argument("--base-url", action="append", dest="base_urls")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    sitemap = args.sitemap.resolve() if args.sitemap else default_sitemap(root).resolve()
    base_urls = tuple(args.base_urls or DEFAULT_BASE_URLS)
    report_path = args.report or (root / "reports" / "sitewide-heading-intent-v2.json")

    statuses, changes, unsupported = collect(root, sitemap, base_urls, write=args.write)
    applied = len(changes) if args.write else 0
    if args.write and not any(item.error for item in statuses):
        statuses, remaining, unsupported = collect(root, sitemap, base_urls, write=False)
        if remaining:
            statuses = [replace(item, error=item.error or "non-idempotent generation") for item in statuses]
    payload = write_report(
        report_path,
        statuses,
        applied=applied,
        unsupported=unsupported,
        root=root,
        sitemap=sitemap,
        base_urls=base_urls,
    )
    print(json.dumps({key: payload[key] for key in ("contract", "pages", "indexable", "applied", "changed", "failed")}, ensure_ascii=False))
    if payload["failed"] or unsupported:
        return 1
    if args.check and changes:
        for path in changes:
            print(path.relative_to(root))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
