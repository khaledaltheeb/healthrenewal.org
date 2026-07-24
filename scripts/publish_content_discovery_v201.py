#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
VERIFY_FILE = "google644f1f7a8b7aaa2b.html"
TOPICAL_MARKER = "data-topical-seo-v201"
MAX_KEYWORDS = 12
MAX_KEYWORDS_CHARS = 480

GLOBAL_TAGS = {
    "ar": ["الصحة النفسية", "علم النفس", "محتوى نفسي عربي", "الدعم النفسي"],
    "en": ["mental health", "psychology", "Arabic mental health resources"],
    "es": ["salud mental", "psicología", "recursos de salud mental en árabe"],
}

SECTION_CONFIG = {
    "ar": {
        "encyclopedia": ("الموسوعة النفسية", ["مصطلحات علم النفس", "الصحة النفسية", "الموسوعة النفسية"]),
        "terms": ("المعجم النفسي", ["مصطلحات علم النفس", "تعريفات نفسية", "علم النفس"]),
        "hubs": ("المراكز الموضوعية", ["موضوعات نفسية", "مراكز معرفية", "الصحة النفسية"]),
        "care-guides": ("أدلة التعامل", ["أدلة التعامل مع الحالات", "الدعم الأسري", "إرشادات عملية"]),
        "special-needs": ("ذوو الاحتياجات الخاصة", ["الأشخاص ذوو الاحتياجات الخاصة", "التربية الدامجة", "التدخل المبكر"]),
        "tips": ("النصائح النفسية", ["نصائح نفسية", "مهارات نفسية", "جودة الحياة"]),
        "provider-assessment-demo": ("منصة التقييم", ["التقييم النفسي", "الاستكشاف المهني", "متابعة الحالات"]),
        "assessment-lab": ("المقاييس النفسية", ["المقاييس النفسية", "التقييم الاستكشافي", "حدود التفسير"]),
        "cognitive-lab": ("القدرات المعرفية", ["القدرات المعرفية", "الانتباه", "الذاكرة"]),
        "magazine": ("المجلة والأبحاث", ["أبحاث الصحة النفسية", "دراسات علم النفس", "تحليل الأدلة"]),
        "trust": ("الثقة والمنهجية", ["مصادر موثوقة", "منهجية المحتوى", "مراجعة علمية"]),
        "partners": ("الشركاء والشفافية", ["الشفافية", "الشركاء", "الحوكمة"]),
        "api": ("واجهة البيانات", ["واجهة API", "بيانات منظمة", "تكامل المواقع"]),
        "start-here": ("ابدأ من هنا", ["مسارات الصحة النفسية", "دليل استخدام المنصة", "اختيار الدعم"]),
        "sectors": ("الأقسام المتخصصة", ["الصحة النفسية للطفل", "الصحة النفسية للأسرة", "الدعم الأسري"]),
        "guides": ("الأدلة", ["أدلة الصحة النفسية", "إرشادات عملية", "الدعم النفسي"]),
        "blog": ("المقالات", ["مقالات علم النفس", "الصحة النفسية", "محتوى نفسي عربي"]),
    },
    "en": {
        "encyclopedia": ("Psychology encyclopedia", ["psychology encyclopedia", "mental health", "psychology terms"]),
        "special-needs": ("Inclusive support", ["people with additional support needs", "inclusive education", "early intervention"]),
        "care-guides": ("Care guides", ["care guides", "family support", "practical guidance"]),
        "api": ("Data API", ["API", "structured data", "website integration"]),
    },
    "es": {
        "encyclopedia": ("Enciclopedia de psicología", ["enciclopedia de psicología", "salud mental", "términos de psicología"]),
        "special-needs": ("Apoyo inclusivo", ["necesidades de apoyo", "educación inclusiva", "intervención temprana"]),
        "care-guides": ("Guías prácticas", ["guías prácticas", "apoyo familiar", "salud mental"]),
        "api": ("API de datos", ["API", "datos estructurados", "integración web"]),
    },
}

CONTROLLED_TERMS = {
    "ar": [
        "اضطراب طيف التوحد", "التوحد", "متلازمة داون", "فرط الحركة وتشتت الانتباه",
        "اضطراب فرط الحركة ونقص الانتباه", "صعوبات التعلم", "الإعاقة الذهنية",
        "القلق", "الاكتئاب", "الوسواس القهري", "اضطرابات النوم", "الصحة النفسية للطفل",
        "الصحة النفسية للأسرة", "العلاج النفسي", "الإرشاد النفسي", "الدعم الأسري",
        "التدخل المبكر", "التربية الدامجة", "التقييم النفسي", "المقاييس النفسية",
        "الأشخاص ذوو الاحتياجات الخاصة", "ذوو الاحتياجات الخاصة", "جودة الحياة",
    ],
    "en": [
        "autism", "Down syndrome", "ADHD", "learning disabilities", "anxiety",
        "depression", "OCD", "child mental health", "family mental health",
        "psychological assessment", "inclusive education", "early intervention",
    ],
    "es": [
        "autismo", "síndrome de Down", "TDAH", "dificultades de aprendizaje",
        "ansiedad", "depresión", "salud mental infantil", "educación inclusiva",
    ],
}


@dataclass
class PageMetadata:
    lang: str = "ar"
    direction: str = "rtl"
    title: str = ""
    description: str = ""
    canonical: str = ""
    robots: str = ""
    keywords: list[str] = field(default_factory=list)
    h1: str = ""
    text: str = ""


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta = PageMetadata()
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._text: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        values = {str(k).lower(): (v or "") for k, v in attrs}
        if lower == "html":
            self.meta.lang = values.get("lang", self.meta.lang).split("-")[0].lower() or "ar"
            self.meta.direction = values.get("dir", self.meta.direction) or ("rtl" if self.meta.lang == "ar" else "ltr")
        elif lower == "meta":
            name = values.get("name", "").lower()
            prop = values.get("property", "").lower()
            content = html.unescape(values.get("content", "")).strip()
            if name == "description":
                self.meta.description = content
            elif name == "robots":
                self.meta.robots = content.lower()
            elif name == "keywords":
                self.meta.keywords = split_keywords(content)
            elif prop == "og:description" and not self.meta.description:
                self.meta.description = content
        elif lower == "link":
            rels = values.get("rel", "").lower().split()
            if "canonical" in rels:
                self.meta.canonical = html.unescape(values.get("href", "")).strip()
        elif lower in {"script", "style", "noscript", "template"}:
            self._skip_depth += 1
        elif lower == "title":
            self._capture = "title"
            self._buffer = []
        elif lower == "h1" and not self.meta.h1:
            self._capture = "h1"
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript", "template"} and self._skip_depth:
            self._skip_depth -= 1
        if self._capture == lower:
            value = clean_text(" ".join(self._buffer))
            if lower == "title":
                self.meta.title = value
            elif lower == "h1":
                self.meta.h1 = value
            self._capture = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = clean_text(data)
        if not value:
            return
        self._text.append(value)
        if self._capture:
            self._buffer.append(value)

    def close(self) -> None:
        super().close()
        self.meta.text = clean_text(" ".join(self._text))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def split_keywords(value: str) -> list[str]:
    return [clean_text(item) for item in re.split(r"[,،;؛|]", value) if clean_text(item)]


def normalize_keyword(value: str) -> str:
    value = clean_text(value).strip(" .,:;،؛|-—_")
    return re.sub(r"\s+", " ", value).casefold()


def add_unique(target: list[str], candidate: str) -> None:
    candidate = clean_text(candidate).strip(" .,:;،؛|-—_")
    if len(candidate) < 2 or len(candidate) > 100:
        return
    normalized = normalize_keyword(candidate)
    if not normalized or any(normalize_keyword(item) == normalized for item in target):
        return
    target.append(candidate)


def route_for(page: Path, site: Path) -> str:
    rel = page.relative_to(site).as_posix()
    if rel == "index.html":
        return ""
    if rel.endswith("/index.html"):
        return rel[:-10]
    return rel


def section_key(route: str) -> str:
    clean = route.strip("/")
    if not clean:
        return "home"
    first = clean.split("/", 1)[0]
    return first


def section_info(route: str, lang: str) -> tuple[str, list[str]]:
    key = section_key(route)
    localized = SECTION_CONFIG.get(lang, {})
    if key in localized:
        return localized[key]
    if key == "home":
        labels = {
            "ar": ("الصفحة الرئيسية", GLOBAL_TAGS["ar"]),
            "en": ("Home", GLOBAL_TAGS["en"]),
            "es": ("Inicio", GLOBAL_TAGS["es"]),
        }
        return labels.get(lang, labels["en"])
    fallback = SECTION_CONFIG.get("ar", {}).get(key)
    if lang == "ar" and fallback:
        return fallback
    return (key.replace("-", " ").title(), GLOBAL_TAGS.get(lang, GLOBAL_TAGS["en"]))


def canonical_is_public(canonical: str) -> bool:
    if not canonical:
        return False
    parsed = urlparse(canonical)
    return parsed.scheme == "https" and parsed.netloc == "khaledaltheeb.github.io" and parsed.path.startswith(BASE_PATH)


def derive_keywords(meta: PageMetadata, route: str) -> list[str]:
    lang = meta.lang if meta.lang in GLOBAL_TAGS else "en"
    result: list[str] = []
    for item in meta.keywords:
        add_unique(result, item)

    title_without_brand = re.sub(
        r"\s*[|—]\s*(?:منصة الصحة النفسية وذوي الاحتياجات الخاصة|مصطلحات علم النفس|Psychology Terminology).*$",
        "",
        meta.title,
        flags=re.I,
    )
    for item in re.split(r"\s*[|—]\s*|\s+-\s+", title_without_brand):
        add_unique(result, item)
    add_unique(result, meta.h1)

    section_label, section_tags = section_info(route, lang)
    add_unique(result, section_label)
    for item in section_tags:
        add_unique(result, item)

    haystack = " ".join([meta.title, meta.h1, meta.description, meta.text[:5000]]).casefold()
    for term in CONTROLLED_TERMS.get(lang, []):
        if term.casefold() in haystack:
            add_unique(result, term)

    for item in GLOBAL_TAGS.get(lang, GLOBAL_TAGS["en"]):
        if len(result) >= 6:
            break
        add_unique(result, item)

    selected: list[str] = []
    chars = 0
    for item in result:
        extra = len(item) + (2 if selected else 0)
        if len(selected) >= MAX_KEYWORDS or chars + extra > MAX_KEYWORDS_CHARS:
            break
        selected.append(item)
        chars += extra
    return selected


def parse_page(text: str) -> PageMetadata:
    parser = PageParser()
    parser.feed(text)
    parser.close()
    return parser.meta


def replace_keywords_meta(text: str, keywords: list[str]) -> tuple[str, bool]:
    payload = f'<meta name="keywords" content="{html.escape(", ".join(keywords), quote=True)}">'
    pattern = re.compile(
        r'<meta\b(?=[^>]*\bname\s*=\s*["\']keywords["\'])[^>]*>',
        flags=re.I,
    )
    if pattern.search(text):
        updated = pattern.sub(payload, text, count=1)
        return updated, updated != text
    updated, count = re.subn(r"</head\s*>", payload + "\n</head>", text, count=1, flags=re.I)
    if count != 1:
        raise ValueError("head_close_missing")
    return updated, True


def topical_schema(meta: PageMetadata, keywords: list[str], route: str) -> str:
    section_label, _ = section_info(route, meta.lang)
    graph = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": meta.canonical + "#topical-page",
        "url": meta.canonical,
        "name": meta.title or meta.h1,
        "description": meta.description,
        "inLanguage": meta.lang,
        "keywords": keywords,
        "about": [{"@type": "Thing", "name": item} for item in keywords[:8]],
        "isPartOf": {"@id": BASE_URL + "#website"},
        "genre": section_label,
    }
    return (
        f'<script type="application/ld+json" {TOPICAL_MARKER}>'
        + json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


def replace_topical_schema(text: str, payload: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf'<script\b(?=[^>]*\b{TOPICAL_MARKER}\b)[^>]*>.*?</script\s*>',
        flags=re.I | re.S,
    )
    if pattern.search(text):
        updated = pattern.sub(payload, text, count=1)
        return updated, updated != text
    updated, count = re.subn(r"</head\s*>", payload + "\n</head>", text, count=1, flags=re.I)
    if count != 1:
        raise ValueError("head_close_missing")
    return updated, True


def enrich_page(text: str, route: str) -> tuple[str, PageMetadata, list[str], bool]:
    meta = parse_page(text)
    if "noindex" in meta.robots or not canonical_is_public(meta.canonical):
        return text, meta, [], False
    if not meta.title or not meta.description:
        raise ValueError("title_or_description_missing")
    keywords = derive_keywords(meta, route)
    if len(keywords) < 4:
        raise ValueError("insufficient_topical_keywords")
    updated, keywords_changed = replace_keywords_meta(text, keywords)
    schema_payload = topical_schema(meta, keywords, route)
    updated, schema_changed = replace_topical_schema(updated, schema_payload)
    final_meta = parse_page(updated)
    return updated, final_meta, keywords, keywords_changed or schema_changed


def generated_at() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def publish(site: Path) -> dict[str, int]:
    site = Path(site).resolve()
    if not site.is_dir():
        raise ValueError(f"missing_site:{site}")

    items: list[dict[str, object]] = []
    section_counts: Counter[str] = Counter()
    section_labels: dict[str, str] = {}
    tag_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    pages_scanned = 0
    pages_changed = 0
    skipped = 0

    for page in sorted(site.rglob("*.html")):
        if page.name == VERIFY_FILE or page.name == "404.html":
            skipped += 1
            continue
        pages_scanned += 1
        route = route_for(page, site)
        original = page.read_text(encoding="utf-8")
        try:
            updated, meta, keywords, changed = enrich_page(original, route)
        except ValueError as error:
            raise ValueError(f"{page.relative_to(site).as_posix()}:{error}") from error
        if not keywords:
            skipped += 1
            continue
        if changed:
            page.write_text(updated, encoding="utf-8")
            pages_changed += 1

        key = section_key(route)
        label, _ = section_info(route, meta.lang)
        section_counts[key] += 1
        section_labels.setdefault(key, label)
        language_counts[meta.lang] += 1
        for tag in keywords[:8]:
            tag_counts[tag] += 1

        items.append(
            {
                "id": route.strip("/") or "home",
                "path": "/" + route.lstrip("/"),
                "url": meta.canonical,
                "lang": meta.lang,
                "dir": meta.direction,
                "section": key,
                "sectionLabel": label,
                "title": meta.title,
                "description": meta.description,
                "h1": meta.h1,
                "tags": keywords[:8],
            }
        )

    api_dir = site / "api" / "v1"
    api_dir.mkdir(parents=True, exist_ok=True)
    stamp = generated_at()
    index_payload = {
        "apiVersion": "1.0.0",
        "generatedAt": stamp,
        "total": len(items),
        "items": sorted(items, key=lambda item: (str(item["lang"]), str(item["path"]))),
    }
    taxonomy_payload = {
        "apiVersion": "1.0.0",
        "generatedAt": stamp,
        "totalPages": len(items),
        "languages": [
            {"code": code, "pages": count}
            for code, count in sorted(language_counts.items())
        ],
        "sections": [
            {
                "id": key,
                "label": section_labels[key],
                "pages": section_counts[key],
            }
            for key in sorted(section_counts)
        ],
        "tags": [
            {"name": name, "pages": count}
            for name, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
    }
    (api_dir / "content-index.json").write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (api_dir / "taxonomy.json").write_text(
        json.dumps(taxonomy_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "version": 201,
        "pages_scanned": pages_scanned,
        "pages_indexed": len(items),
        "pages_changed": pages_changed,
        "pages_skipped": skipped,
        "sections": len(section_counts),
        "tags": len(tag_counts),
    }


def main() -> None:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    result = publish(site)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
