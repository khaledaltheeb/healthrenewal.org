#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

BASE_URL = "https://healthrenewal.org/"
REPORT_NAME = "editorial-page-quality-v309.json"
VERIFY_RE = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
SPACE_RE = re.compile(r"\s+")

AUTHORITATIVE_DOMAINS = {
    "who.int",
    "cdc.gov",
    "nih.gov",
    "nimh.nih.gov",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "nice.org.uk",
    "un.org",
    "unicef.org",
    "unesco.org",
    "cochranelibrary.com",
    "psychiatry.org",
    "apa.org",
    "aap.org",
    "doi.org",
}

PROHIBITED_CLAIMS = (
    "شفاء مضمون",
    "يعالج نهائيًا",
    "علاج نهائي",
    "نتيجة مضمونة",
    "بديل عن الطبيب",
    "بديل عن المختص",
    "تشخيصك هو",
    "أوقف الدواء",
    "stop your medication",
    "guaranteed cure",
)

PLACEHOLDER_PHRASES = (
    "lorem ipsum",
    "قريبًا",
    "سيتم إضافة",
    "محتوى تجريبي",
    "نص مؤقت",
    "todo",
    "coming soon",
)

SOURCE_TERMS = (
    "المصادر",
    "المراجع",
    "المصدر الأصلي",
    "قراءة الدليل",
    "references",
    "sources",
    "bibliography",
)
EVIDENCE_TERMS = (
    "doi",
    "pmid",
    "pubmed",
    "مراجعة منهجية",
    "تحليل تلوي",
    "إرشادات",
    "دليل سريري",
    "systematic review",
    "meta-analysis",
    "guideline",
)
REVIEW_TERMS = (
    "آخر تحديث",
    "تاريخ التحديث",
    "تاريخ المراجعة",
    "مراجعة المحتوى",
    "reviewed",
    "updated",
    "dateModified",
)
LIMITATION_TERMS = (
    "حدود الدليل",
    "لا يكفي",
    "لا يثبت",
    "لا يستبدل",
    "قد يختلف",
    "بحسب السياق",
    "limitations",
    "does not replace",
    "not diagnostic",
)
DISCLAIMER_TERMS = (
    "ليس تشخيصًا",
    "لا يستبدل التقييم",
    "لا يستبدل العلاج",
    "للتثقيف",
    "للتوعية",
    "not a diagnosis",
    "educational purposes",
)
DANGER_TERMS = (
    "إيذاء النفس",
    "الانتحار",
    "خطر مباشر",
    "خطر وشيك",
    "self-harm",
    "suicide",
    "immediate danger",
)
EMERGENCY_TERMS = (
    "الطوارئ",
    "خدمات الطوارئ",
    "مساعدة عاجلة",
    "خط الأزمات",
    "emergency services",
    "crisis line",
    "urgent help",
)
PRACTICAL_GROUPS = {
    "steps": ("خطوات", "ماذا تفعل", "خطة", "ابدأ", "steps", "action plan"),
    "examples": ("مثال", "أمثلة", "حالة تطبيقية", "سيناريو", "example", "case"),
    "warnings": ("متى تطلب", "علامات الخطر", "تحذير", "مؤشرات", "when to seek", "warning"),
    "faq": ("أسئلة شائعة", "سؤال", "faq", "frequently asked"),
    "contexts": ("الأسرة", "المدرسة", "المعلم", "العمل", "الأطفال", "المراهق", "family", "school", "workplace"),
}

FAMILY_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("languages", ("en/", "es/")),
    ("encyclopedia", ("encyclopedia/",)),
    ("glossary", ("glossary/", "terms/")),
    ("hubs", ("hubs/",)),
    ("comparisons", ("comparisons/",)),
    ("care-guides", ("care-guides/",)),
    ("guided-assessment", ("guided-assessment/",)),
    ("library", ("library/",)),
    ("magazine", ("magazine/",)),
    ("special-needs", ("special-needs/",)),
    ("tools", ("daily-tools/", "tools/", "assessments/", "assessment-lab/", "cognitive-tests/", "cognitive-lab/")),
    ("learning-paths", ("learning-paths/",)),
    ("provider-platform", ("provider-assessment-demo/",)),
)

WORD_TARGETS = {
    "main": 500,
    "languages": 400,
    "encyclopedia": 650,
    "glossary": 450,
    "hubs": 650,
    "comparisons": 600,
    "care-guides": 700,
    "guided-assessment": 500,
    "library": 650,
    "magazine": 700,
    "special-needs": 700,
    "tools": 450,
    "learning-paths": 550,
    "provider-platform": 800,
}


def compact(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip()


def normalized(value: str) -> str:
    return compact(value).casefold()


def contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(phrase.casefold() in lowered for phrase in phrases)


def route_for(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if relative == "index.html":
        return ""
    return relative.removesuffix("index.html") if relative.endswith("/index.html") else relative


def expected_url(path: Path, root: Path, base_url: str) -> str:
    route = route_for(path, root)
    return base_url if not route else base_url + route


def family_for(path: Path, root: Path) -> str:
    route = route_for(path, root)
    for family, prefixes in FAMILY_PREFIXES:
        if any(route.startswith(prefix) for prefix in prefixes):
            return family
    return "main"


def authoritative_domain(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return any(host == domain or host.endswith("." + domain) for domain in AUTHORITATIVE_DOMAINS)


@dataclass
class ParsedPage:
    lang: str = ""
    direction: str = ""
    title_parts: list[str] = field(default_factory=list)
    h1_parts: list[str] = field(default_factory=list)
    visible_parts: list[str] = field(default_factory=list)
    paragraph_parts: list[str] = field(default_factory=list)
    current_paragraph: list[str] = field(default_factory=list)
    stack: list[str] = field(default_factory=list)
    meta_description: str = ""
    robots: str = ""
    canonical: list[str] = field(default_factory=list)
    og_title: str = ""
    og_description: str = ""
    json_ld_count: int = 0
    h1_count: int = 0
    heading_count: int = 0
    list_item_count: int = 0
    table_count: int = 0
    details_count: int = 0
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        return compact(" ".join(self.title_parts))

    @property
    def h1(self) -> str:
        return compact(" ".join(self.h1_parts))

    @property
    def visible_text(self) -> str:
        return compact(" ".join(self.visible_parts))

    @property
    def noindex(self) -> bool:
        return "noindex" in self.robots.casefold()


class PageParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = ParsedPage()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {str(key).lower(): value or "" for key, value in attrs}
        self.page.stack.append(tag)
        if tag == "html":
            self.page.lang = values.get("lang", "").lower()
            self.page.direction = values.get("dir", "").lower()
        elif tag == "h1":
            self.page.h1_count += 1
            self.page.heading_count += 1
        elif tag in {"h2", "h3", "h4", "h5", "h6"}:
            self.page.heading_count += 1
        elif tag == "li":
            self.page.list_item_count += 1
        elif tag == "table":
            self.page.table_count += 1
        elif tag == "details":
            self.page.details_count += 1
        elif tag == "meta":
            name = values.get("name", "").lower()
            prop = values.get("property", "").lower()
            content = values.get("content", "").strip()
            if name == "description":
                self.page.meta_description = content
            elif name in {"robots", "googlebot"}:
                self.page.robots += " " + content
            elif prop == "og:title":
                self.page.og_title = content
            elif prop == "og:description":
                self.page.og_description = content
        elif tag == "link":
            rel = {token.lower() for token in values.get("rel", "").split()}
            if "canonical" in rel and values.get("href"):
                self.page.canonical.append(values["href"].strip())
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.page.json_ld_count += 1
        elif tag == "a":
            href = values.get("href", "").strip()
            if href:
                parsed = urlparse(href)
                if parsed.scheme in {"http", "https"}:
                    if parsed.netloc.lower().endswith("khaledaltheeb.github.io") and parsed.path.startswith("/"):
                        self.page.internal_links.append(href)
                    else:
                        self.page.external_links.append(href)
                elif not parsed.scheme and not href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:", "//")):
                    self.page.internal_links.append(href)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "p" and self.page.current_paragraph:
            paragraph = compact(" ".join(self.page.current_paragraph))
            if paragraph:
                self.page.paragraph_parts.append(paragraph)
            self.page.current_paragraph.clear()
        for index in range(len(self.page.stack) - 1, -1, -1):
            if self.page.stack[index] == tag:
                del self.page.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        text = compact(data)
        if not text:
            return
        if any(tag in self.page.stack for tag in self.SKIP_TAGS):
            return
        if "title" in self.page.stack:
            self.page.title_parts.append(text)
        if "h1" in self.page.stack:
            self.page.h1_parts.append(text)
        if "p" in self.page.stack:
            self.page.current_paragraph.append(text)
        self.page.visible_parts.append(text)

    def close(self) -> None:
        super().close()
        if self.page.current_paragraph:
            paragraph = compact(" ".join(self.page.current_paragraph))
            if paragraph:
                self.page.paragraph_parts.append(paragraph)
            self.page.current_paragraph.clear()


def parse_page(path: Path) -> ParsedPage:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    parser.close()
    return parser.page


def score_band(score: int) -> str:
    if score >= 90:
        return "reference"
    if score >= 80:
        return "ready"
    if score >= 70:
        return "upgrade"
    return "priority-upgrade"


def density_points(count: int, thresholds: tuple[int, int, int, int]) -> int:
    if count >= thresholds[3]:
        return 5
    if count >= thresholds[2]:
        return 4
    if count >= thresholds[1]:
        return 3
    if count >= thresholds[0]:
        return 2
    if count > 0:
        return 1
    return 0


def recommendations(components: dict[str, int], details: dict[str, object]) -> list[str]:
    output: list[str] = []
    if components["accuracy_readiness"] < 14:
        output.append("أضف مصادر أولية أو إرشادات رسمية، وحدود الدليل وتاريخ المراجعة دون ادعاء مراجعة غير موثقة.")
    if components["distinctiveness"] < 11:
        output.append("ميّز العنوان والوصف والأمثلة والفقرات عن الصفحات القريبة، وأضف زاوية بحث مستقلة.")
    if components["sources"] < 10:
        output.append("اربط الادعاءات بمصادر مباشرة موثوقة، وأظهر قسم المصادر ومعرفات DOI أو PMID عند توفرها.")
    if components["depth"] < 11:
        output.append("وسّع الشرح بمحاور وفروق وأمثلة وجداول أو أسئلة شائعة بدل الحشو أو التكرار.")
    if components["practical_value"] < 7:
        output.append("أضف خطوات عملية وأمثلة ومؤشرات طلب المساعدة وإرشادات بحسب الأسرة أو المدرسة أو العمل.")
    if components["language"] < 8:
        output.append("حسّن وضوح اللغة وطول العنوان والوصف وأزل العبارات المؤقتة أو العامة.")
    if components["safety"] < 5:
        output.append("أضف حدودًا مهنية وإرشاد طوارئ عند تناول الخطر، وأزل أي وعود علاجية مطلقة.")
    if components["seo"] < 5:
        output.append("استكمل العنوان والوصف وH1 وCanonical والبيانات المنظمة.")
    if components["internal_linking"] < 4:
        output.append("أضف روابط داخلية سياقية إلى الصفحات السابقة والتالية والمركز الموضوعي المناسب.")
    if bool(details.get("duplicate_text")):
        output.append("أعد كتابة الكتلة الأساسية لأنها مطابقة نصيًا لصفحة أخرى.")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--minimum-score", type=int, default=80)
    parser.add_argument("--fail-below-minimum", action="store_true")
    args = parser.parse_args()

    site = args.site.resolve()
    base_url = args.base_url.rstrip("/") + "/"
    if not site.is_dir():
        raise SystemExit(f"Site root not found: {site}")

    parsed_pages: list[dict[str, object]] = []
    parse_errors: list[dict[str, str]] = []
    title_counts: Counter[str] = Counter()
    description_counts: Counter[str] = Counter()
    h1_counts: Counter[str] = Counter()
    text_counts: Counter[str] = Counter()
    paragraph_counts: Counter[str] = Counter()

    for path in sorted(site.rglob("*.html")):
        raw = path.read_text(encoding="utf-8", errors="strict")
        if path.name == "404.html" or (path.parent == site and VERIFY_RE.match(raw.strip())):
            continue
        try:
            page = parse_page(path)
        except Exception as exc:
            parse_errors.append({"path": path.relative_to(site).as_posix(), "error": str(exc)})
            continue
        if page.noindex:
            continue
        visible = page.visible_text
        tokens = TOKEN_RE.findall(visible)
        text_key = hashlib.sha256(normalized(visible).encode("utf-8")).hexdigest() if visible else ""
        paragraph_keys = []
        for paragraph in page.paragraph_parts:
            if len(TOKEN_RE.findall(paragraph)) < 20:
                continue
            key = hashlib.sha256(normalized(paragraph).encode("utf-8")).hexdigest()
            paragraph_keys.append(key)
            paragraph_counts[key] += 1
        record = {
            "path": path,
            "page": page,
            "visible": visible,
            "tokens": tokens,
            "text_key": text_key,
            "paragraph_keys": paragraph_keys,
            "family": family_for(path, site),
            "url": expected_url(path, site, base_url),
        }
        parsed_pages.append(record)
        if page.title:
            title_counts[normalized(page.title)] += 1
        if page.meta_description:
            description_counts[normalized(page.meta_description)] += 1
        if page.h1:
            h1_counts[normalized(page.h1)] += 1
        if text_key:
            text_counts[text_key] += 1

    pages: list[dict[str, object]] = []
    family_scores: defaultdict[str, list[int]] = defaultdict(list)

    for record in parsed_pages:
        path = record["path"]
        page: ParsedPage = record["page"]  # type: ignore[assignment]
        visible = str(record["visible"])
        lowered = visible.casefold()
        tokens: list[str] = record["tokens"]  # type: ignore[assignment]
        family = str(record["family"])
        url = str(record["url"])
        word_count = len(tokens)
        external_domains = {
            urlparse(link).netloc.lower().removeprefix("www.")
            for link in page.external_links
            if urlparse(link).netloc
        }
        authoritative = sorted(domain for domain in external_domains if authoritative_domain(domain))
        has_sources_section = contains_any(visible, SOURCE_TERMS)
        has_evidence_identifier = contains_any(visible, EVIDENCE_TERMS) or any(
            "doi.org" in link or "pubmed" in link for link in page.external_links
        )
        has_review_marker = contains_any(visible, REVIEW_TERMS) or "dateModified" in path.read_text(encoding="utf-8")
        has_limitation = contains_any(visible, LIMITATION_TERMS)
        prohibited = [phrase for phrase in PROHIBITED_CLAIMS if phrase.casefold() in lowered]
        placeholders = [phrase for phrase in PLACEHOLDER_PHRASES if phrase.casefold() in lowered]
        has_disclaimer = contains_any(visible, DISCLAIMER_TERMS)
        has_danger = contains_any(visible, DANGER_TERMS)
        has_emergency = contains_any(visible, EMERGENCY_TERMS)

        accuracy = min(8, len(authoritative) * 3)
        accuracy += 4 if has_evidence_identifier else 0
        accuracy += 3 if has_review_marker else 0
        accuracy += 3 if has_limitation else 0
        accuracy += 2 if not prohibited else 0
        accuracy = min(20, accuracy)

        title_unique = bool(page.title) and title_counts[normalized(page.title)] == 1
        description_unique = bool(page.meta_description) and description_counts[normalized(page.meta_description)] == 1
        h1_unique = bool(page.h1) and h1_counts[normalized(page.h1)] == 1
        text_key = str(record["text_key"])
        text_unique = bool(text_key) and text_counts[text_key] == 1
        paragraph_keys: list[str] = record["paragraph_keys"]  # type: ignore[assignment]
        repeated_paragraphs = sum(1 for key in paragraph_keys if paragraph_counts[key] > 1)
        repeated_ratio = repeated_paragraphs / len(paragraph_keys) if paragraph_keys else 0.0
        distinctiveness = 4 if title_unique else 0
        distinctiveness += 3 if description_unique else 0
        distinctiveness += 2 if h1_unique else 0
        distinctiveness += 3 if text_unique else 0
        distinctiveness += 3 if repeated_ratio <= 0.2 else 1 if repeated_ratio <= 0.5 else 0

        sources = min(6, len(authoritative) * 3)
        sources += min(3, len(external_domains))
        sources += 2 if has_sources_section else 0
        sources += 2 if has_evidence_identifier else 0
        sources += 2 if has_review_marker else 0
        sources = min(15, sources)

        target = WORD_TARGETS.get(family, WORD_TARGETS["main"])
        depth = min(9, round(9 * min(1.0, word_count / target)))
        depth += 2 if page.heading_count >= 3 else 1 if page.heading_count >= 1 else 0
        depth += 2 if page.list_item_count >= 5 else 1 if page.list_item_count >= 2 else 0
        depth += 2 if (page.table_count + page.details_count) >= 1 or contains_any(visible, ("أسئلة شائعة", "faq")) else 0
        depth = min(15, depth)

        practical_hits = {
            key: contains_any(visible, phrases) for key, phrases in PRACTICAL_GROUPS.items()
        }
        practical_value = sum(2 for present in practical_hits.values() if present)

        visible_chars = [char for char in visible if char.isalpha()]
        arabic_ratio = (
            sum(1 for char in visible_chars if ARABIC_RE.match(char)) / len(visible_chars)
            if visible_chars
            else 0.0
        )
        arabic_expected = page.lang.startswith("ar") or page.direction == "rtl"
        language = 3 if (arabic_ratio >= 0.35 if arabic_expected else bool(visible_chars)) else 0
        language += 3 if not placeholders else 0
        language += 2 if 20 <= len(page.title) <= 100 else 1 if page.title else 0
        language += 2 if 70 <= len(page.meta_description) <= 220 else 1 if page.meta_description else 0
        language = min(10, language)

        safety = 3 if not prohibited else 0
        safety += 1 if has_disclaimer else 0
        safety += 1 if (not has_danger or has_emergency) else 0

        canonicals = [value for value in page.canonical if value]
        self_canonical = len(canonicals) == 1 and canonicals[0].rstrip("/") == url.rstrip("/")
        seo = int(bool(page.title))
        seo += int(bool(page.meta_description))
        seo += int(self_canonical)
        seo += int(page.h1_count == 1)
        seo += int(page.json_ld_count > 0)

        internal_count = len(set(page.internal_links))
        internal_linking = density_points(internal_count, (1, 2, 4, 8))

        components = {
            "accuracy_readiness": accuracy,
            "distinctiveness": distinctiveness,
            "sources": sources,
            "depth": depth,
            "practical_value": practical_value,
            "language": language,
            "safety": safety,
            "seo": seo,
            "internal_linking": internal_linking,
        }
        score = sum(components.values())
        details: dict[str, object] = {
            "word_count": word_count,
            "word_target": target,
            "authoritative_domains": authoritative,
            "external_domains": sorted(external_domains),
            "internal_links": internal_count,
            "headings": page.heading_count,
            "list_items": page.list_item_count,
            "tables": page.table_count,
            "details_blocks": page.details_count,
            "arabic_ratio": round(arabic_ratio, 4),
            "duplicate_title": not title_unique,
            "duplicate_description": not description_unique,
            "duplicate_h1": not h1_unique,
            "duplicate_text": not text_unique,
            "repeated_paragraph_ratio": round(repeated_ratio, 4),
            "prohibited_claims": prohibited,
            "placeholder_phrases": placeholders,
            "has_disclaimer": has_disclaimer,
            "danger_requires_emergency_guidance": has_danger,
            "has_emergency_guidance": has_emergency,
            "self_canonical": self_canonical,
            "json_ld_blocks": page.json_ld_count,
            "practical_signals": practical_hits,
        }
        page_report = {
            "path": path.relative_to(site).as_posix(),
            "url": url,
            "family": family,
            "score": score,
            "band": score_band(score),
            "components": components,
            "component_maximums": {
                "accuracy_readiness": 20,
                "distinctiveness": 15,
                "sources": 15,
                "depth": 15,
                "practical_value": 10,
                "language": 10,
                "safety": 5,
                "seo": 5,
                "internal_linking": 5,
            },
            "details": details,
            "recommendations": recommendations(components, details),
        }
        pages.append(page_report)
        family_scores[family].append(score)

    pages.sort(key=lambda item: (int(item["score"]), str(item["path"])))
    scores = [int(item["score"]) for item in pages]
    below_minimum = [item for item in pages if int(item["score"]) < args.minimum_score]
    bands = Counter(str(item["band"]) for item in pages)
    family_summary = {
        family: {
            "pages": len(values),
            "minimum": min(values),
            "median": median(values),
            "average": round(sum(values) / len(values), 2),
            "below_minimum": sum(1 for value in values if value < args.minimum_score),
        }
        for family, values in sorted(family_scores.items())
        if values
    }

    report = {
        "version": 309,
        "status": "passed" if not parse_errors else "parse-errors",
        "score_type": "editorial-operational-readiness",
        "minimum_target": args.minimum_score,
        "caveat": "The automated score measures evidence readiness, distinctiveness, depth, usefulness, safety and technical structure. It does not establish medical correctness or replace named specialist review.",
        "policy": "Pages below the target enter an upgrade queue; they are not deleted merely because of a low score.",
        "pages_scanned": len(pages),
        "parse_error_count": len(parse_errors),
        "minimum_score": min(scores) if scores else 0,
        "median_score": median(scores) if scores else 0,
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "pages_below_target": len(below_minimum),
        "bands": dict(sorted(bands.items())),
        "families": family_summary,
        "priority_upgrade_queue": below_minimum[:500],
        "pages": pages,
        "parse_errors": parse_errors,
    }

    output = args.output or (site / "api" / REPORT_NAME)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "pages_scanned": report["pages_scanned"],
        "average_score": report["average_score"],
        "pages_below_target": report["pages_below_target"],
        "bands": report["bands"],
        "report": str(output),
    }, ensure_ascii=False, indent=2))

    if parse_errors:
        return 1
    if args.fail_below_minimum and below_minimum:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
