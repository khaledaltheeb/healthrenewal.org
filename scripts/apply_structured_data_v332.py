from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

SCHEMA_VERSION = 332
MARKER_ATTR = 'data-pterminology-schema="v332"'
DEFAULT_SITE_BASE = "https://khaledaltheeb.github.io/pterminology-site/"
ORG_ID = DEFAULT_SITE_BASE + "#organization"
WEBSITE_ID = DEFAULT_SITE_BASE + "#website"
VERIFY_PATTERN = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.I,
)
SCRIPT_PATTERN = re.compile(
    r"<script\b(?P<attrs>[^>]*)type=[\"']application/ld\+json[\"'](?P<tail>[^>]*)>(?P<body>.*?)</script>",
    re.I | re.S,
)
MANAGED_PATTERN = re.compile(
    r"<script\b[^>]*data-pterminology-schema=[\"']v332[\"'][^>]*>.*?</script>",
    re.I | re.S,
)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SPACE_PATTERN = re.compile(r"\s+")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+-]+Z?)?$")
SOURCE_HOSTS = {
    "doi.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "who.int",
    "nice.org.uk",
    "nhs.uk",
    "cdc.gov",
    "unicef.org",
    "apa.org",
    "psychiatry.org",
    "cochranelibrary.com",
}
COLLECTION_SEGMENTS = {
    "encyclopedia",
    "terms",
    "hubs",
    "library",
    "magazine",
    "research",
    "comparisons",
    "daily-tools",
    "learning-paths",
    "sectors",
    "sections",
    "special-needs",
    "assessment-lab",
    "cognitive-lab",
}
MEDICAL_SEGMENTS = {
    "encyclopedia",
    "terms",
    "special-needs",
    "care-guides",
    "guided-assessment",
    "comparisons",
    "magazine",
    "research",
    "library",
    "sectors",
}
ARABIC_SEGMENT_NAMES = {
    "encyclopedia": "الموسوعة",
    "terms": "المصطلحات",
    "hubs": "المراكز الموضوعية",
    "library": "المكتبة",
    "magazine": "المجلة والأبحاث",
    "research": "الأبحاث",
    "comparisons": "المقارنات",
    "daily-tools": "الأدوات اليومية",
    "learning-paths": "مسارات التعلم",
    "sectors": "القطاعات",
    "sections": "الأقسام",
    "special-needs": "ذوو الاحتياجات الخاصة",
    "assessment-lab": "مختبر المقاييس",
    "cognitive-lab": "المختبر المعرفي",
    "platform": "دليل المنصة",
    "api": "واجهة البيانات",
}


@dataclass
class PageFacts:
    title: str
    description: str
    canonical: str
    language: str
    h1: str
    visible_text: str
    meta: dict[str, list[str]] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    faq: list[tuple[str, str]] = field(default_factory=list)
    existing_types: set[str] = field(default_factory=set)
    invalid_jsonld: list[str] = field(default_factory=list)


def compact_text(value: str) -> str:
    value = re.sub(r"<(?:script|style|template)\b[^>]*>.*?</(?:script|style|template)>", " ", value, flags=re.I | re.S)
    value = TAG_PATTERN.sub(" ", value)
    return SPACE_PATTERN.sub(" ", html.unescape(value)).strip()


def attr_map(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in re.finditer(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", tag, re.I | re.S):
        attrs[match.group(1).lower()] = html.unescape(match.group(3)).strip()
    return attrs


def meta_values(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for tag in re.findall(r"<meta\b[^>]*>", text, re.I | re.S):
        attrs = attr_map(tag)
        key = (attrs.get("name") or attrs.get("property") or attrs.get("itemprop") or "").lower()
        content = attrs.get("content", "").strip()
        if key and content:
            result.setdefault(key, []).append(content)
    return result


def first(values: dict[str, list[str]], *keys: str) -> str:
    for key in keys:
        items = values.get(key.lower(), [])
        if items:
            return items[0].strip()
    return ""


def extract_title(text: str) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, re.I | re.S)
    return compact_text(match.group(1)) if match else ""


def extract_h1(text: str) -> str:
    match = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)
    return compact_text(match.group(1)) if match else ""


def extract_canonical(text: str) -> str:
    for tag in re.findall(r"<link\b[^>]*>", text, re.I | re.S):
        attrs = attr_map(tag)
        if attrs.get("rel", "").lower() == "canonical" and attrs.get("href"):
            return attrs["href"]
    return ""


def extract_language(text: str) -> str:
    match = re.search(r"<html\b[^>]*\blang=([\"'])(.*?)\1", text, re.I | re.S)
    return match.group(2).strip() if match else "ar"


def extract_links(text: str, base_url: str) -> list[str]:
    links: list[str] = []
    for tag in re.findall(r"<a\b[^>]*>", text, re.I | re.S):
        href = attr_map(tag).get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme in {"http", "https"}:
            links.append(absolute)
    return list(dict.fromkeys(links))


def extract_visible_faq(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for details in re.findall(r"<details\b[^>]*>(.*?)</details>", text, re.I | re.S):
        summary = re.search(r"<summary\b[^>]*>(.*?)</summary>", details, re.I | re.S)
        if not summary:
            continue
        question = compact_text(summary.group(1))
        answer_html = details[: summary.start()] + details[summary.end() :]
        answer = compact_text(answer_html)
        if len(question) >= 4 and len(answer) >= 12:
            pairs.append((question, answer))
    for item in re.findall(r"<[^>]+\bdata-faq-item(?:=[\"'][^\"']*[\"'])?[^>]*>(.*?)</[^>]+>", text, re.I | re.S):
        q = re.search(r"<[^>]+\bdata-faq-question[^>]*>(.*?)</[^>]+>", item, re.I | re.S)
        a = re.search(r"<[^>]+\bdata-faq-answer[^>]*>(.*?)</[^>]+>", item, re.I | re.S)
        if q and a:
            question, answer = compact_text(q.group(1)), compact_text(a.group(1))
            if len(question) >= 4 and len(answer) >= 12:
                pairs.append((question, answer))
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for question, answer in pairs:
        key = question.casefold()
        if key not in seen:
            seen.add(key)
            unique.append((question, answer))
    return unique[:20]


def walk_types(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        type_value = value.get("@type")
        if isinstance(type_value, str):
            yield type_value
        elif isinstance(type_value, list):
            yield from (item for item in type_value if isinstance(item, str))
        for child in value.values():
            yield from walk_types(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_types(child)




def remove_invalid_legacy_jsonld(text: str) -> tuple[str, list[str]]:
    issues: list[str] = []
    matches = list(SCRIPT_PATTERN.finditer(text))
    for index, match in reversed(list(enumerate(matches, start=1))):
        attrs = (match.group("attrs") + match.group("tail")).lower()
        if "data-pterminology-schema" in attrs:
            continue
        body = html.unescape(match.group("body")).strip()
        try:
            if not body:
                raise json.JSONDecodeError("empty JSON-LD", body, 0)
            json.loads(body)
        except json.JSONDecodeError as exc:
            issues.append(f"jsonld[{index}] removed: line {exc.lineno} column {exc.colno}: {exc.msg}")
            text = text[: match.start()] + text[match.end() :]
    issues.reverse()
    return text, issues

def inspect_existing_jsonld(text: str) -> tuple[set[str], list[str]]:
    types: set[str] = set()
    errors: list[str] = []
    for index, match in enumerate(SCRIPT_PATTERN.finditer(text), start=1):
        attrs = (match.group("attrs") + match.group("tail")).lower()
        if "data-pterminology-schema" in attrs:
            continue
        body = html.unescape(match.group("body")).strip()
        if not body:
            errors.append(f"jsonld[{index}] is empty")
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            errors.append(f"jsonld[{index}] invalid: line {exc.lineno} column {exc.colno}: {exc.msg}")
            continue
        types.update(walk_types(payload))
    return types, errors


def inspect_page(text: str, fallback_url: str) -> PageFacts:
    meta = meta_values(text)
    title = extract_title(text)
    h1 = extract_h1(text)
    description = first(meta, "description", "og:description", "twitter:description")
    canonical = extract_canonical(text) or fallback_url
    language = extract_language(text)
    visible = compact_text(text)
    existing_types, invalid = inspect_existing_jsonld(text)
    return PageFacts(
        title=title or h1 or "صفحة معرفية",
        description=description or f"{h1 or title or 'صفحة معرفية'} — محتوى عربي منظم للتثقيف العام.",
        canonical=canonical,
        language=language,
        h1=h1 or title,
        visible_text=visible,
        meta=meta,
        links=extract_links(text, canonical),
        faq=extract_visible_faq(text),
        existing_types=existing_types,
        invalid_jsonld=invalid,
    )


def page_url(site_base: str, relative: Path) -> str:
    rel = relative.as_posix()
    if rel == "index.html":
        return site_base
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    return urljoin(site_base, rel)


def breadcrumb_name(segment: str) -> str:
    if segment in ARABIC_SEGMENT_NAMES:
        return ARABIC_SEGMENT_NAMES[segment]
    cleaned = re.sub(r"[-_]+", " ", segment).strip()
    return cleaned or "صفحة"


def breadcrumbs(site_base: str, relative: Path, page_name: str) -> dict[str, Any]:
    parent = PurePosixPath(relative.as_posix()).parent
    segments = [] if str(parent) == "." else list(parent.parts)
    items: list[dict[str, Any]] = [
        {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": site_base}
    ]
    accumulated: list[str] = []
    for segment in segments:
        accumulated.append(segment)
        name = page_name if segment == segments[-1] else breadcrumb_name(segment)
        items.append(
            {
                "@type": "ListItem",
                "position": len(items) + 1,
                "name": name,
                "item": urljoin(site_base, "/".join(accumulated) + "/"),
            }
        )
    return {"@type": "BreadcrumbList", "@id": page_url(site_base, relative) + "#breadcrumb", "itemListElement": items}


def split_csv(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in re.split(r"[,،;؛|]", value):
            item = SPACE_PATTERN.sub(" ", item).strip()
            if item and item not in result:
                result.append(item)
    return result


def explicit_schema_type(facts: PageFacts) -> str:
    return first(facts.meta, "schema:type", "schema-type", "structured-data-type").strip()


def reviewer_node(facts: PageFacts) -> dict[str, Any] | None:
    reviewer = first(facts.meta, "reviewed-by", "reviewedby", "medical-reviewer")
    if not reviewer:
        match = re.search(r"\bdata-reviewed-by=([\"'])(.*?)\1", facts.visible_text, re.I | re.S)
        reviewer = match.group(2).strip() if match else ""
    if not reviewer:
        return None
    if reviewer not in facts.visible_text:
        return None
    reviewer_url = first(facts.meta, "reviewer-url")
    node: dict[str, Any] = {"@type": "Person", "name": reviewer}
    if reviewer_url.startswith(("https://", "http://")):
        node["url"] = reviewer_url
    return node


def author_node(facts: PageFacts) -> dict[str, Any]:
    author = first(facts.meta, "author", "article:author")
    if author:
        return {"@type": "Person", "name": author}
    return {"@id": ORG_ID}


def valid_date(value: str) -> str:
    value = value.strip()
    return value if value and DATE_PATTERN.match(value) else ""


def source_links(facts: PageFacts) -> list[str]:
    result: list[str] = []
    for link in facts.links:
        host = urlparse(link).netloc.lower().removeprefix("www.")
        if host in SOURCE_HOSTS or host.endswith(".gov") or host.endswith(".edu"):
            result.append(link)
    return result[:30]


def medical_condition_node(facts: PageFacts, url: str) -> dict[str, Any] | None:
    explicit = explicit_schema_type(facts)
    opted_in = explicit == "MedicalCondition" or "MedicalCondition" in facts.existing_types
    if not opted_in:
        return None
    node: dict[str, Any] = {
        "@type": "MedicalCondition",
        "@id": url + "#condition",
        "name": first(facts.meta, "medical-condition-name") or facts.h1,
        "description": facts.description,
        "url": url,
    }
    code_value = first(facts.meta, "medical-code", "codevalue")
    coding_system = first(facts.meta, "medical-coding-system", "codingsystem")
    if code_value and coding_system:
        node["code"] = {
            "@type": "MedicalCode",
            "codeValue": code_value,
            "codingSystem": coding_system,
        }
    mappings = {
        "medical-symptoms": ("signOrSymptom", "MedicalSymptom"),
        "medical-causes": ("cause", "MedicalCause"),
        "medical-treatments": ("possibleTreatment", "MedicalTherapy"),
        "medical-risk-factors": ("riskFactor", "MedicalRiskFactor"),
        "medical-tests": ("typicalTest", "MedicalTest"),
    }
    for meta_key, (schema_key, schema_type) in mappings.items():
        values = split_csv(facts.meta.get(meta_key, []))
        if values:
            node[schema_key] = [{"@type": schema_type, "name": value} for value in values]
    return node


def article_node(facts: PageFacts, url: str, relative: Path) -> dict[str, Any] | None:
    segments = set(PurePosixPath(relative.as_posix()).parts)
    explicit = explicit_schema_type(facts)
    article_types = {"Article", "ScholarlyArticle", "MedicalScholarlyArticle", "NewsArticle"}
    chosen = explicit if explicit in article_types else ""
    if not chosen and segments.intersection({"magazine", "research", "library"}) and relative.name == "index.html" and len(relative.parts) > 2:
        chosen = "Article"
    if not chosen:
        return None
    node: dict[str, Any] = {
        "@type": chosen,
        "@id": url + "#article",
        "headline": facts.h1,
        "name": facts.h1,
        "description": facts.description,
        "url": url,
        "mainEntityOfPage": {"@id": url + "#webpage"},
        "author": author_node(facts),
        "publisher": {"@id": ORG_ID},
        "inLanguage": facts.language,
    }
    published = valid_date(first(facts.meta, "article:published_time", "date", "datepublished"))
    modified = valid_date(first(facts.meta, "article:modified_time", "last-modified", "datemodified"))
    if published:
        node["datePublished"] = published
    if modified:
        node["dateModified"] = modified
    citations = source_links(facts)
    if citations:
        node["citation"] = citations
    publication_type = first(facts.meta, "publication-type")
    if chosen == "MedicalScholarlyArticle" and publication_type:
        node["publicationType"] = publication_type
    return node


def interactive_node(facts: PageFacts, url: str, relative: Path, text: str) -> dict[str, Any] | None:
    segments = set(PurePosixPath(relative.as_posix()).parts)
    if not segments.intersection({"daily-tools", "assessment-lab", "cognitive-lab"}):
        return None
    if not re.search(r"<(?:form|input|button|canvas)\b|data-(?:lab|tool|assessment)", text, re.I):
        return None
    return {
        "@type": "WebApplication",
        "@id": url + "#application",
        "name": facts.h1,
        "description": facts.description,
        "url": url,
        "applicationCategory": "HealthApplication",
        "operatingSystem": "Any",
        "browserRequirements": "يتطلب متصفح ويب حديثًا مع JavaScript عند استخدام الأداة التفاعلية.",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "JOD"},
        "publisher": {"@id": ORG_ID},
    }


def build_graph(facts: PageFacts, relative: Path, site_base: str, source_text: str) -> dict[str, Any]:
    url = facts.canonical or page_url(site_base, relative)
    segments = set(PurePosixPath(relative.as_posix()).parts)
    is_home = relative.as_posix() == "index.html"
    is_collection = is_home or bool(segments.intersection(COLLECTION_SEGMENTS) and len(relative.parts) <= 2)
    is_medical = bool(segments.intersection(MEDICAL_SEGMENTS))
    page_type = "CollectionPage" if is_collection else "MedicalWebPage" if is_medical else "WebPage"
    breadcrumb = breadcrumbs(site_base, relative, facts.h1)
    page: dict[str, Any] = {
        "@type": page_type,
        "@id": url + "#webpage",
        "url": url,
        "name": facts.h1,
        "description": facts.description,
        "inLanguage": facts.language,
        "isPartOf": {"@id": WEBSITE_ID},
        "publisher": {"@id": ORG_ID},
        "breadcrumb": {"@id": breadcrumb["@id"]},
    }
    keywords = split_csv(facts.meta.get("keywords", []))[:12]
    if keywords:
        page["keywords"] = keywords
        page["about"] = [{"@type": "Thing", "name": value} for value in keywords[:6]]
    reviewer = reviewer_node(facts)
    if reviewer:
        page["reviewedBy"] = reviewer
    published = valid_date(first(facts.meta, "article:published_time", "datepublished"))
    modified = valid_date(first(facts.meta, "article:modified_time", "datemodified", "last-modified"))
    if published:
        page["datePublished"] = published
    if modified:
        page["dateModified"] = modified

    graph: list[dict[str, Any]] = [
        {
            "@type": "Organization",
            "@id": ORG_ID,
            "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "alternateName": ["مصطلحات علم النفس", "Psychology Terminology"],
            "url": site_base,
            "logo": {"@type": "ImageObject", "url": urljoin(site_base, "assets/brand/logo-mark.svg")},
            "sameAs": ["https://www.instagram.com/pterminology/", "https://www.youtube.com/@psychology-term"],
        },
        {
            "@type": "WebSite",
            "@id": WEBSITE_ID,
            "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "url": site_base,
            "inLanguage": ["ar", "en", "es"],
            "publisher": {"@id": ORG_ID},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {"@type": "EntryPoint", "urlTemplate": urljoin(site_base, "encyclopedia/?q={search_term_string}")},
                "query-input": "required name=search_term_string",
            },
        },
        page,
        breadcrumb,
    ]

    condition = medical_condition_node(facts, url)
    article = article_node(facts, url, relative)
    application = interactive_node(facts, url, relative, source_text)
    main_entities: list[dict[str, str]] = []
    for node in (condition, article, application):
        if node:
            graph.append(node)
            main_entities.append({"@id": node["@id"]})
    if facts.faq:
        faq = {
            "@type": "FAQPage",
            "@id": url + "#faq",
            "url": url,
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer},
                }
                for question, answer in facts.faq
            ],
        }
        graph.append(faq)
        main_entities.append({"@id": faq["@id"]})
    if main_entities:
        page["mainEntity"] = main_entities[0] if len(main_entities) == 1 else main_entities
    return {"@context": "https://schema.org", "@graph": graph}


def schema_script(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
    return f'\n<script type="application/ld+json" {MARKER_ATTR}>\n{body}\n</script>\n'


def inject(text: str, payload: dict[str, Any]) -> str:
    script = schema_script(payload).strip()
    if MANAGED_PATTERN.search(text):
        return MANAGED_PATTERN.sub(script, text, count=1)
    if re.search(r"</head>", text, re.I):
        return re.sub(r"</head>", "\n" + script + "\n</head>", text, count=1, flags=re.I)
    if re.search(r"</body>", text, re.I):
        return re.sub(r"</body>", "\n" + script + "\n</body>", text, count=1, flags=re.I)
    return text.rstrip() + "\n" + script + "\n"


def is_verification_file(path: Path, text: str, root: Path) -> bool:
    return path.parent == root and VERIFY_PATTERN.match(text.strip()) is not None


def validate_managed_payload(payload: dict[str, Any], facts: PageFacts) -> list[str]:
    errors: list[str] = []
    try:
        encoded = json.dumps(payload, ensure_ascii=False)
        decoded = json.loads(encoded)
    except (TypeError, json.JSONDecodeError) as exc:
        return [f"managed JSON-LD serialization failed: {exc}"]
    graph = decoded.get("@graph")
    if not isinstance(graph, list) or not graph:
        errors.append("managed graph is missing or empty")
        return errors
    types = set(walk_types(decoded))
    if "WebPage" not in types and "MedicalWebPage" not in types and "CollectionPage" not in types:
        errors.append("page node is missing")
    if "BreadcrumbList" not in types:
        errors.append("breadcrumb node is missing")
    if "FAQPage" in types:
        for question, answer in facts.faq:
            if question not in facts.visible_text or answer not in facts.visible_text:
                errors.append(f"FAQ content is not visible: {question[:80]}")
    for node in graph:
        if isinstance(node, dict) and "reviewedBy" in node:
            reviewer = node["reviewedBy"]
            name = reviewer.get("name", "") if isinstance(reviewer, dict) else ""
            if not name or name not in facts.visible_text:
                errors.append("reviewedBy is not visibly supported")
    return errors


def process(root: Path, site_base: str, strict: bool) -> dict[str, Any]:
    site_base = site_base.rstrip("/") + "/"
    global ORG_ID, WEBSITE_ID
    ORG_ID = site_base + "#organization"
    WEBSITE_ID = site_base + "#website"
    pages = sorted(root.rglob("*.html"))
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "running",
        "site_base": site_base,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pages_discovered": len(pages),
        "eligible_pages": 0,
        "pages_updated": 0,
        "faq_pages": 0,
        "medical_condition_pages": 0,
        "article_pages": 0,
        "interactive_pages": 0,
        "reviewed_pages": 0,
        "existing_jsonld_blocks": 0,
        "invalid_existing_jsonld_removed": [],
        "errors": [],
        "warnings": [],
    }
    for path in pages:
        text = path.read_text(encoding="utf-8")
        if is_verification_file(path, text, root):
            continue
        relative = path.relative_to(root)
        report["existing_jsonld_blocks"] += len(SCRIPT_PATTERN.findall(text))
        text, removed_invalid = remove_invalid_legacy_jsonld(text)
        if removed_invalid:
            report["invalid_existing_jsonld_removed"].append({"page": relative.as_posix(), "issues": removed_invalid})
        fallback_url = page_url(site_base, relative)
        facts = inspect_page(text, fallback_url)
        report["eligible_pages"] += 1
        payload = build_graph(facts, relative, site_base, text)
        errors = validate_managed_payload(payload, facts)
        if errors:
            report["errors"].append({"page": relative.as_posix(), "issues": errors})
            continue
        types = set(walk_types(payload))
        report["faq_pages"] += int("FAQPage" in types)
        report["medical_condition_pages"] += int("MedicalCondition" in types)
        report["article_pages"] += int(bool(types.intersection({"Article", "ScholarlyArticle", "MedicalScholarlyArticle", "NewsArticle"})))
        report["interactive_pages"] += int("WebApplication" in types)
        report["reviewed_pages"] += int("reviewedBy" in json.dumps(payload, ensure_ascii=False))
        updated = inject(text, payload)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            report["pages_updated"] += 1

    coverage = report["eligible_pages"] - len(report["errors"])
    report["coverage_pages"] = coverage
    report["coverage_ratio"] = round(coverage / max(1, report["eligible_pages"]), 6)
    if report["invalid_existing_jsonld_removed"]:
        report["warnings"].append(
            "Invalid legacy JSON-LD blocks were removed and replaced by the managed valid graph."
        )
    report["status"] = "passed" if not report["errors"] and coverage == report["eligible_pages"] else "failed"
    api_dir = root / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    report_path = api_dir / "structured-data-v332.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if strict and report["status"] != "passed":
        raise SystemExit(json.dumps({"status": report["status"], "errors": report["errors"][:10]}, ensure_ascii=False))
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply and validate site-wide Schema.org JSON-LD without inventing medical reviewers or codes.")
    parser.add_argument("site", nargs="?", default="_site", help="Generated static site directory")
    parser.add_argument("--site-base", default=os.environ.get("SITE_BASE", DEFAULT_SITE_BASE))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when managed coverage is incomplete")
    parser.add_argument("--min-pages", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.site).resolve()
    if not root.is_dir():
        raise SystemExit(f"Missing site directory: {root}")
    report = process(root, args.site_base, args.strict)
    if report["eligible_pages"] < args.min_pages:
        raise SystemExit(f"Expected at least {args.min_pages} eligible pages, found {report['eligible_pages']}")
    print(json.dumps({
        "status": report["status"],
        "eligible_pages": report["eligible_pages"],
        "pages_updated": report["pages_updated"],
        "coverage_ratio": report["coverage_ratio"],
        "faq_pages": report["faq_pages"],
        "medical_condition_pages": report["medical_condition_pages"],
        "article_pages": report["article_pages"],
        "interactive_pages": report["interactive_pages"],
        "invalid_existing_jsonld_removed": len(report["invalid_existing_jsonld_removed"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
