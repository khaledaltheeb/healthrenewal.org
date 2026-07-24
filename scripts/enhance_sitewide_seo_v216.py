#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote


SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
BRAND_AR = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
BRAND_EN = "Mental Health and Special Needs Platform"
BRAND_ES = "Plataforma de Salud Mental y Necesidades Especiales"
SOCIAL_IMAGE = BASE_URL + "assets/brand/social-card.png"
SKIP_FILES = {"404.html", "offline.html"}
SKIP_PREFIXES = ("coverage/", "reports/", "tmp/", "node_modules/")

TAG_RE = re.compile(r"<(?:meta|link)\b[^>]*>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.I | re.S)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
HTML_RE = re.compile(r"<html\b([^>]*)>", re.I | re.S)
HEAD_END_RE = re.compile(r"</head\s*>", re.I)
JSONLD_RE = re.compile(
    r"<script\b[^>]*\btype\s*=\s*([\"'])application/ld\+json\1[^>]*>",
    re.I | re.S,
)
STRIP_TAGS_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")

LOCALE = {
    "ar": "ar_AR",
    "en": "en_US",
    "es": "es_ES",
}
BRANDS = {
    "ar": BRAND_AR,
    "en": BRAND_EN,
    "es": BRAND_ES,
}
BASE_TERMS = {
    "ar": ["الصحة النفسية", "علم النفس", "مصطلحات علم النفس"],
    "en": ["mental health", "psychology", "psychology terminology"],
    "es": ["salud mental", "psicología", "términos de psicología"],
}
ROUTE_TERMS = {
    "encyclopedia": {
        "ar": ["الموسوعة النفسية", "المفاهيم النفسية", "الاضطرابات النفسية"],
        "en": ["psychology encyclopedia", "mental health concepts", "mental disorders"],
        "es": ["enciclopedia de psicología", "conceptos de salud mental", "trastornos mentales"],
    },
    "special-needs": {
        "ar": ["ذوو الاحتياجات الخاصة", "التربية الدامجة", "الدعم الأسري", "التدخل المبكر"],
        "en": ["special needs", "inclusive education", "family support", "early intervention"],
        "es": ["necesidades especiales", "educación inclusiva", "apoyo familiar", "intervención temprana"],
    },
    "care-guides": {
        "ar": ["أدلة التعامل", "دعم الأسرة", "مقدم الخدمة", "خطوات عملية"],
        "en": ["care guides", "family support", "service providers", "practical guidance"],
        "es": ["guías de apoyo", "apoyo familiar", "proveedores de servicios", "orientación práctica"],
    },
    "assessment-lab": {
        "ar": ["التقييم النفسي", "المقاييس النفسية", "الاستكشاف النفسي"],
        "en": ["psychological assessment", "psychological scales", "screening"],
        "es": ["evaluación psicológica", "escalas psicológicas", "detección"],
    },
    "cognitive-lab": {
        "ar": ["القدرات المعرفية", "الانتباه", "الذاكرة", "الاستدلال"],
        "en": ["cognitive abilities", "attention", "memory", "reasoning"],
        "es": ["capacidades cognitivas", "atención", "memoria", "razonamiento"],
    },
    "tips": {
        "ar": ["نصائح نفسية", "مهارات نفسية", "جودة الحياة"],
        "en": ["mental health tips", "psychological skills", "quality of life"],
        "es": ["consejos de salud mental", "habilidades psicológicas", "calidad de vida"],
    },
    "magazine": {
        "ar": ["أبحاث علم النفس", "الدراسات النفسية", "الصحة النفسية المبنية على الدليل"],
        "en": ["psychology research", "mental health studies", "evidence-based mental health"],
        "es": ["investigación en psicología", "estudios de salud mental", "salud mental basada en evidencia"],
    },
    "provider-assessment-demo": {
        "ar": ["التقييم المهني", "مقدم الخدمة", "تقارير التقييم"],
        "en": ["professional assessment", "service provider", "assessment reports"],
        "es": ["evaluación profesional", "proveedor de servicios", "informes de evaluación"],
    },
    "api": {
        "ar": ["واجهة برمجة التطبيقات", "تكامل البيانات", "OpenAPI", "بيانات الدورات"],
        "en": ["API", "data integration", "OpenAPI", "course data"],
        "es": ["API", "integración de datos", "OpenAPI", "datos de cursos"],
    },
    "child": {
        "ar": ["الصحة النفسية للطفل", "نمو الطفل", "سلوك الطفل"],
        "en": ["child mental health", "child development", "child behavior"],
        "es": ["salud mental infantil", "desarrollo infantil", "conducta infantil"],
    },
    "family": {
        "ar": ["الصحة النفسية للأسرة", "العلاقات الأسرية", "الدعم الأسري"],
        "en": ["family mental health", "family relationships", "family support"],
        "es": ["salud mental familiar", "relaciones familiares", "apoyo familiar"],
    },
}
CONTENT_ROOTS = {
    "encyclopedia",
    "care-guides",
    "special-needs",
    "tips",
    "magazine",
    "assessment-lab",
    "cognitive-lab",
}


def attrs(tag: str) -> dict[str, str]:
    return {name.lower(): html.unescape(value.strip()) for name, _, value in ATTR_RE.findall(tag)}


def clean_text(value: str) -> str:
    value = STRIP_TAGS_RE.sub(" ", value)
    return SPACE_RE.sub(" ", html.unescape(value)).strip()


def escape_attr(value: str) -> str:
    return html.escape(value, quote=True)


def language_of(source: str) -> str:
    match = HTML_RE.search(source)
    if not match:
        return "ar"
    language = attrs(match.group(0)).get("lang", "ar").split("-", 1)[0].lower()
    return language if language in LOCALE else "ar"


def title_of(head: str, h1: str, language: str) -> tuple[str, str]:
    match = TITLE_RE.search(head)
    title = clean_text(match.group(1)) if match else ""
    if title:
        return title, head
    if not h1:
        return "", head
    title = f"{h1} | {BRANDS[language]}"
    return title, f"<title>{html.escape(title)}</title>\n" + head


def first_meta(head: str, key: str, value: str) -> tuple[str | None, str | None, tuple[int, int] | None]:
    key = key.lower()
    value = value.lower()
    for match in TAG_RE.finditer(head):
        tag = match.group(0)
        parsed = attrs(tag)
        if parsed.get(key, "").lower() == value:
            return parsed.get("content"), tag, match.span()
    return None, None, None


def link_rel(head: str, rel: str) -> tuple[str | None, str | None, tuple[int, int] | None]:
    rel = rel.lower()
    for match in TAG_RE.finditer(head):
        tag = match.group(0)
        if not tag.lower().startswith("<link"):
            continue
        parsed = attrs(tag)
        rels = {part.lower() for part in parsed.get("rel", "").split()}
        if rel in rels:
            return parsed.get("href"), tag, match.span()
    return None, None, None


def replace_content(tag: str, value: str) -> str:
    replacement = escape_attr(value)
    if re.search(r"\bcontent\s*=", tag, re.I):
        return re.sub(
            r"(\bcontent\s*=\s*)([\"']).*?\2",
            lambda match: f'{match.group(1)}"{replacement}"',
            tag,
            count=1,
            flags=re.I | re.S,
        )
    return tag[:-1] + f' content="{replacement}">'


def canonical_for(path: Path) -> str:
    relative = path.relative_to(SITE).as_posix()
    if relative == "index.html":
        route = ""
    elif relative.endswith("/index.html"):
        route = relative[: -len("index.html")]
    else:
        route = relative
    return BASE_URL + quote(route, safe="/-._~")


def route_key(relative: str) -> str:
    parts = Path(relative).parts
    if not parts:
        return "home"
    root = parts[0]
    if root == "sectors" and len(parts) > 1:
        if parts[1] == "child":
            return "child"
        if parts[1] in {"family", "home"}:
            return "family"
    return root


def normalized_keyword(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip(" |—–-،,.;:").casefold()


def title_topic(title: str, language: str) -> str:
    topic = title
    for brand in (BRANDS[language], BRAND_AR, "مصطلحات علم النفس", "Psychology Terminology"):
        topic = topic.replace(brand, "")
    topic = re.split(r"\s*[|—–]\s*", topic, maxsplit=1)[0]
    return clean_text(topic).strip(" -|—–")


def build_keywords(relative: str, language: str, title: str, h1: str, existing: str | None) -> list[str]:
    candidates: list[str] = []
    if existing:
        candidates.extend(part.strip() for part in re.split(r"[,،]", existing) if part.strip())
    topic = title_topic(title, language)
    if 3 <= len(topic) <= 120:
        candidates.append(topic)
    if h1 and normalized_keyword(h1) != normalized_keyword(topic) and len(h1) <= 120:
        candidates.append(h1)
    key = route_key(relative)
    candidates.extend(ROUTE_TERMS.get(key, {}).get(language, []))
    candidates.extend(BASE_TERMS[language])

    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = clean_text(candidate)
        normalized = normalized_keyword(candidate)
        if not normalized or normalized in seen or len(candidate) > 120:
            continue
        seen.add(normalized)
        result.append(candidate)
        if len(result) >= 15:
            break
    return result


def is_article(relative: str) -> bool:
    parts = Path(relative).parts
    return bool(parts and parts[0] in CONTENT_ROOTS and len(parts) >= 3)


def generic_description(topic: str, language: str) -> str:
    topic = topic or BRANDS[language]
    if language == "en":
        text = f"A structured evidence-aware guide to {topic}, with practical context, related topics, and clear professional limits."
    elif language == "es":
        text = f"Guía estructurada y basada en evidencia sobre {topic}, con contexto práctico, temas relacionados y límites profesionales claros."
    else:
        text = f"دليل عربي منظم حول {topic} يوضح السياق العملي والموضوعات المرتبطة والحدود المهنية ضمن منصة الصحة النفسية وذوي الاحتياجات الخاصة."
    return text[:220]


def inject_before_head_end(source: str, additions: list[str]) -> str:
    if not additions:
        return source
    matches = list(HEAD_END_RE.finditer(source))
    if len(matches) != 1:
        raise ValueError("expected exactly one closing head tag")
    position = matches[0].start()
    block = "\n" + "\n".join(additions) + "\n"
    return source[:position] + block + source[position:]


def enrich_page(path: Path) -> tuple[bool, dict[str, int | str | bool]]:
    relative = path.relative_to(SITE).as_posix()
    source = path.read_text(encoding="utf-8")
    if relative in SKIP_FILES or relative.startswith(SKIP_PREFIXES):
        return False, {"status": "skipped_special"}
    head_match = re.search(r"<head\b[^>]*>(.*?)</head\s*>", source, re.I | re.S)
    if not head_match:
        return False, {"status": "missing_head"}
    head = head_match.group(1)
    robots, _, _ = first_meta(head, "name", "robots")
    if robots and "noindex" in robots.lower():
        return False, {"status": "skipped_noindex"}

    language = language_of(source)
    h1_match = H1_RE.search(source)
    h1 = clean_text(h1_match.group(1)) if h1_match else ""
    title, updated_head = title_of(head, h1, language)
    if not title:
        return False, {"status": "missing_title_and_h1"}
    if updated_head != head:
        source = source.replace(head, updated_head, 1)
        head = updated_head

    description, _, _ = first_meta(head, "name", "description")
    if not description:
        description = generic_description(h1 or title_topic(title, language), language)
    canonical, _, _ = link_rel(head, "canonical")
    canonical = canonical or canonical_for(path)
    existing_keywords, keyword_tag, keyword_span = first_meta(head, "name", "keywords")
    keywords = build_keywords(relative, language, title, h1, existing_keywords)
    if len(keywords) < 5:
        return False, {"status": "insufficient_keywords"}
    keyword_value = ", ".join(keywords)

    additions: list[str] = []
    counters: Counter[str] = Counter()
    if not first_meta(head, "name", "description")[0]:
        additions.append(f'<meta name="description" content="{escape_attr(description)}">')
        counters["description_added"] += 1
    if not robots:
        additions.append('<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">')
        counters["robots_added"] += 1
    if not canonical:
        raise AssertionError("canonical resolution failed")
    if not link_rel(head, "canonical")[0]:
        additions.append(f'<link rel="canonical" href="{escape_attr(canonical)}">')
        counters["canonical_added"] += 1

    if keyword_tag and keyword_span:
        if existing_keywords != keyword_value:
            new_tag = replace_content(keyword_tag, keyword_value)
            start, end = keyword_span
            head = head[:start] + new_tag + head[end:]
            source = source.replace(head_match.group(1), head, 1)
            counters["keywords_augmented"] += 1
    else:
        additions.append(f'<meta name="keywords" content="{escape_attr(keyword_value)}">')
        counters["keywords_added"] += 1

    singleton_properties = {
        "og:type": "article" if is_article(relative) else "website",
        "og:site_name": BRANDS[language],
        "og:locale": LOCALE[language],
        "og:title": title,
        "og:description": description,
        "og:url": canonical,
        "og:image": SOCIAL_IMAGE,
        "og:image:alt": title,
    }
    for prop, value in singleton_properties.items():
        if first_meta(head, "property", prop)[0] is None:
            additions.append(f'<meta property="{prop}" content="{escape_attr(value)}">')
            counters["open_graph_added"] += 1

    twitter = {
        "twitter:card": "summary_large_image",
        "twitter:title": title,
        "twitter:description": description,
        "twitter:image": SOCIAL_IMAGE,
        "twitter:image:alt": title,
    }
    for name, value in twitter.items():
        if first_meta(head, "name", name)[0] is None:
            additions.append(f'<meta name="{name}" content="{escape_attr(value)}">')
            counters["twitter_added"] += 1

    if is_article(relative):
        existing_tags = {
            normalized_keyword(attrs(match.group(0)).get("content", ""))
            for match in TAG_RE.finditer(head)
            if attrs(match.group(0)).get("property", "").lower() == "article:tag"
        }
        for keyword in keywords[:8]:
            if normalized_keyword(keyword) in existing_tags:
                continue
            additions.append(f'<meta property="article:tag" content="{escape_attr(keyword)}">')
            counters["article_tags_added"] += 1

    if not JSONLD_RE.search(head):
        schema = {
            "@context": "https://schema.org",
            "@type": "Article" if is_article(relative) else "WebPage",
            "name": title,
            "headline": h1 or title,
            "description": description,
            "url": canonical,
            "inLanguage": language,
            "keywords": keywords,
            "isPartOf": {
                "@type": "WebSite",
                "name": BRANDS[language],
                "url": BASE_URL,
            },
        }
        payload = json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        additions.append(f'<script type="application/ld+json">{payload}</script>')
        counters["schema_added"] += 1

    enriched = inject_before_head_end(source, additions)
    changed = enriched != source
    if changed:
        path.write_text(enriched, encoding="utf-8")
    result: dict[str, int | str | bool] = {
        "status": "modified" if changed else "unchanged",
        "language": language,
        "route": route_key(relative),
        "article": is_article(relative),
        "keyword_count": len(keywords),
    }
    result.update(counters)
    return changed, result


def main() -> int:
    if not SITE.is_dir():
        raise SystemExit(f"Missing production site directory: {SITE}")
    pages = sorted(SITE.rglob("*.html"))
    if not pages:
        raise SystemExit("No HTML pages found")

    totals: Counter[str] = Counter()
    routes: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    failures: list[dict[str, str]] = []
    for path in pages:
        relative = path.relative_to(SITE).as_posix()
        try:
            changed, result = enrich_page(path)
        except Exception as exc:  # fail closed and report exact page
            failures.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})
            continue
        status = str(result.get("status", "unknown"))
        totals["html_pages"] += 1
        totals[status] += 1
        if changed:
            totals["modified_pages"] += 1
        for key, value in result.items():
            if isinstance(value, int) and key not in {"keyword_count"}:
                totals[key] += value
        if result.get("route"):
            routes[str(result["route"])] += 1
        if result.get("language"):
            languages[str(result["language"])] += 1

    report = {
        "version": 216,
        "site": str(SITE),
        "base_url": BASE_URL,
        "social_image": SOCIAL_IMAGE,
        "totals": dict(sorted(totals.items())),
        "languages": dict(sorted(languages.items())),
        "routes": dict(sorted(routes.items())),
        "failure_count": len(failures),
        "failures": failures[:200],
        "policy": {
            "keyword_limit": 15,
            "no_keyword_stuffing": True,
            "preserve_existing_metadata": True,
            "skip_noindex_pages": True,
            "canonical_scope": BASE_URL,
            "course_import_permission_required": True,
        },
    }
    output = SITE / "api" / "sitewide-seo-v216.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(f"SEO enrichment failed for {len(failures)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
