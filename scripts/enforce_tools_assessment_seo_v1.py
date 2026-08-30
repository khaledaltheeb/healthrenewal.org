from __future__ import annotations

"""Head-only technical SEO gate for Rawafid tools, assessments and cognitive labs.

The gate is intentionally narrow. It never edits visible body content, headings,
URLs or slugs; it never changes noindex pages into indexable pages; and its
semantic query map is an internal build artifact, never meta-keywords/hidden text.
"""

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

ORIGIN = "https://healthrenewal.org"
SITE_AR = "روافد"
SITE_EN = "Health Renewal"
PROFILE = "tools-assessment-seo-v1"
SCOPE_ROOTS = (
    "daily-tools",
    "guided-assessment",
    "assessment-library",
    "assessment-lab",
    "assessments",
    "cognitive-lab",
    "cognitive-tests",
)
SECTION_NAMES = {
    "daily-tools": "الأدوات اليومية",
    "guided-assessment": "التقييم الموجّه",
    "assessment-library": "مكتبة التقييم",
    "assessment-lab": "مختبر المقاييس",
    "assessments": "دليل التقييمات",
    "cognitive-lab": "المختبر المعرفي",
    "cognitive-tests": "المهام المعرفية",
}

HEAD_RE = re.compile(r"(?is)(<head\b[^>]*>)(.*?)(</head\s*>)")
BODY_RE = re.compile(r"(?is)<body\b[^>]*>.*?</body\s*>")
HTML_RE = re.compile(r"(?is)<html\b(?P<attrs>[^>]*)>")
TITLE_RE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title\s*>")
H1_RE = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1\s*>")
HEADING_RE = re.compile(r"(?is)<h[2-4]\b[^>]*>(.*?)</h[2-4]\s*>")
P_RE = re.compile(r"(?is)<p\b[^>]*>(.*?)</p\s*>")
TAG_RE = re.compile(r"(?is)<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1\s*>")
META_TAG_RE = re.compile(r"(?is)<meta\b[^>]*>")
LINK_TAG_RE = re.compile(r"(?is)<link\b[^>]*>")
ATTR_RE = re.compile(r"(?is)([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*([\"'])(.*?)\2")
JSONLD_RE = re.compile(r"(?is)<script\b([^>]*)type\s*=\s*([\"'])application/ld\+json\2([^>]*)>(.*?)</script\s*>")
OWN_SCHEMA_RE = re.compile(
    r"(?is)\s*<script\b[^>]*data-rawafid-seo\s*=\s*([\"'])tools-assessment-seo-v1\1[^>]*>.*?</script\s*>\s*"
)
MARKER_RE = re.compile(r"(?is)\s*<!--\s*rawafid-tools-assessment-seo:v1\s+fingerprint=[0-9a-f]{24}\s*-->\s*")

PAGE_SCHEMA_TYPES = {"WebPage", "CollectionPage", "Article", "MedicalWebPage", "ProfilePage"}
STOPWORDS = {
    "هذا", "هذه", "ذلك", "تلك", "الذي", "التي", "على", "الى", "إلى", "عن", "من", "في", "مع",
    "بين", "عند", "بعد", "قبل", "حتى", "أو", "او", "ثم", "لكن", "كما", "قد", "ما", "ماذا", "كيف",
    "متى", "هل", "لماذا", "هو", "هي", "هم", "نحن", "كان", "كانت", "يكون", "تكون", "يمكن", "يجب",
    "إذا", "اذا", "إن", "ان", "أن", "لا", "غير", "كل", "أي", "اي", "أكثر", "أقل", "ضمن", "حول",
    "خلال", "دون", "عبر", "لدى", "فقط", "صفحة", "منصة", "روافد", "المستخدم", "المستخدمين", "المحتوى",
    "الأداة", "اداة", "أداة", "التقييم", "النتيجة", "النتائج", "استخدام", "الاستخدام", "المصدر", "المصادر",
    "الخطوة", "خطوة", "واحد", "واحدة", "أيضا", "أيضًا", "مرة", "أخرى", "بشكل", "الهدف", "الحالي",
}
QUERY_TEMPLATES = (
    "{topic} {term}",
    "شرح {topic} {term}",
    "دليل {topic} {term}",
    "ما هو {topic} {term}",
    "ما معنى {topic} {term}",
    "كيفية استخدام {topic} {term}",
    "طريقة استخدام {topic} {term}",
    "خطوات {topic} {term}",
    "كيف أستخدم {topic} {term}",
    "متى أستخدم {topic} {term}",
    "لمن يناسب {topic} {term}",
    "ما فائدة {topic} {term}",
    "أسئلة عن {topic} {term}",
    "مثال على {topic} {term}",
    "تطبيق {topic} {term}",
    "فهم {topic} {term}",
    "{topic} شرح عملي {term}",
    "{topic} دليل عملي {term}",
    "{topic} خطوة بخطوة {term}",
    "{topic} بالعربي {term}",
    "{topic} روافد {term}",
    "{topic} Health Renewal {term}",
    "ما علاقة {topic} بـ {term}",
    "كيف أفهم {topic} مع {term}",
)
PAIR_TEMPLATES = (
    "{topic} {a} {b}",
    "شرح {topic} {a} {b}",
    "دليل {topic} {a} {b}",
    "كيفية استخدام {topic} {a} {b}",
    "أسئلة عن {topic} {a} {b}",
    "{topic} روافد {a} {b}",
    "{topic} Health Renewal {a} {b}",
    "فهم {topic} {a} {b}",
)


@dataclass
class PagePlan:
    path: Path
    rel: str
    url: str
    root: str
    section: str
    topic: str
    title: str
    description: str
    primary_intent: str
    body_hash: str
    original: str
    updated: str
    changes: list[str]
    fingerprint: str


@dataclass
class Result:
    path: str
    url: str
    status: str
    changes: list[str]
    detail: str = ""
    fingerprint: str = ""
    query_count: int = 0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(tag)}


def strip_tags(value: str) -> str:
    value = SCRIPT_STYLE_RE.sub(" ", value)
    value = TAG_RE.sub(" ", value)
    return " ".join(html.unescape(value).split())


def visible_body(source: str) -> str:
    m = BODY_RE.search(source)
    return strip_tags(m.group(0) if m else source)


def raw_body_hash(source: str) -> str:
    m = BODY_RE.search(source)
    return sha(m.group(0) if m else source)


def get_title(head: str) -> str:
    m = TITLE_RE.search(head)
    return strip_tags(m.group(1)) if m else ""


def get_meta(head: str, attr: str, value: str) -> str:
    for tag in META_TAG_RE.findall(head):
        data = attrs(tag)
        if data.get(attr, "").lower() == value.lower():
            return data.get("content", "").strip()
    return ""


def get_canonical(head: str) -> str:
    for tag in LINK_TAG_RE.findall(head):
        data = attrs(tag)
        if "canonical" in {x.lower() for x in data.get("rel", "").split()}:
            return data.get("href", "").strip()
    return ""


def replace_title(head: str, value: str) -> str:
    tag = f"<title>{html.escape(value)}</title>"
    if TITLE_RE.search(head):
        return TITLE_RE.sub(tag, head, count=1)
    return head.rstrip() + "\n" + tag + "\n"


def replace_meta(head: str, attr: str, key: str, value: str) -> str:
    found = False
    out: list[str] = []
    cursor = 0
    for m in META_TAG_RE.finditer(head):
        out.append(head[cursor:m.start()])
        tag = m.group(0)
        data = attrs(tag)
        if data.get(attr, "").lower() == key.lower():
            if not found:
                out.append(f'<meta {attr}="{html.escape(key, quote=True)}" content="{html.escape(value, quote=True)}">')
                found = True
        else:
            out.append(tag)
        cursor = m.end()
    out.append(head[cursor:])
    result = "".join(out)
    if not found:
        result = result.rstrip() + f'\n<meta {attr}="{html.escape(key, quote=True)}" content="{html.escape(value, quote=True)}">\n'
    return result


def replace_canonical(head: str, value: str) -> str:
    found = False
    out: list[str] = []
    cursor = 0
    for m in LINK_TAG_RE.finditer(head):
        out.append(head[cursor:m.start()])
        tag = m.group(0)
        data = attrs(tag)
        if "canonical" in {x.lower() for x in data.get("rel", "").split()}:
            if not found:
                out.append(f'<link rel="canonical" href="{html.escape(value, quote=True)}">')
                found = True
        else:
            out.append(tag)
        cursor = m.end()
    out.append(head[cursor:])
    result = "".join(out)
    if not found:
        result = result.rstrip() + f'\n<link rel="canonical" href="{html.escape(value, quote=True)}">\n'
    return result


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", value)
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    return " ".join(value.lower().split())


def tokens(value: str) -> list[str]:
    return re.findall(r"[\u0600-\u06FFA-Za-z][\u0600-\u06FFA-Za-z0-9_-]{2,}", unicodedata.normalize("NFKC", value))


def route_for(path: Path, site: Path) -> str:
    rel = path.relative_to(site).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[:-10]
    return "/" + rel


def topic_for(source: str, head: str, path: Path) -> str:
    m = H1_RE.search(source)
    if m:
        value = strip_tags(m.group(1))
        if value:
            return value[:120]
    title = get_title(head)
    title = re.sub(r"\s*[|\-–—:]\s*(?:منصة\s*)?روافد(?:\s*[|\-–—:]\s*Health Renewal)?\s*$", "", title, flags=re.I)
    title = re.sub(r"\s*[|\-–—:]\s*Health Renewal\s*$", "", title, flags=re.I)
    if title.strip():
        return title.strip()[:120]
    return (path.parent.name if path.name == "index.html" else path.stem).replace("-", " ")[:120]


def indexable(head: str) -> bool:
    robots = (get_meta(head, "name", "robots") + " " + get_meta(head, "name", "googlebot")).lower()
    return "noindex" not in robots


def existing_jsonld(head: str, *, exclude_owned: bool = True) -> tuple[list[Any], list[str]]:
    probe = OWN_SCHEMA_RE.sub("", head) if exclude_owned else head
    payloads: list[Any] = []
    errors: list[str] = []
    for m in JSONLD_RE.finditer(probe):
        raw = html.unescape(m.group(4)).strip()
        try:
            payloads.append(json.loads(raw))
        except Exception as exc:
            errors.append(str(exc))
    return payloads, errors


def schema_types(value: Any) -> set[str]:
    output: set[str] = set()
    if isinstance(value, dict):
        t = value.get("@type")
        if isinstance(t, str):
            output.add(t)
        elif isinstance(t, list):
            output.update(str(x) for x in t)
        for child in value.values():
            output.update(schema_types(child))
    elif isinstance(value, list):
        for child in value:
            output.update(schema_types(child))
    return output


def title_supported(title: str, topic: str) -> bool:
    if not 12 <= len(title) <= 85:
        return False
    if "روافد" not in title and SITE_EN.lower() not in title.lower():
        return False
    topic_words = {normalize(x) for x in tokens(topic) if len(x) >= 4}
    return not topic_words or any(word and word in normalize(title) for word in topic_words)


def build_title(topic: str, section: str, duplicated: bool) -> str:
    suffix = " | روافد"
    qualifier = f" | {section}" if duplicated else ""
    budget = max(24, 78 - len(suffix) - len(qualifier))
    core = " ".join(topic.split())
    if len(core) > budget:
        core = core[: budget + 1].rsplit(" ", 1)[0].rstrip(" ،؛:|-–—")
    return f"{core}{qualifier}{suffix}"


def description_supported(description: str, topic: str) -> bool:
    if not 65 <= len(description) <= 200:
        return False
    topic_words = [normalize(x) for x in tokens(topic) if len(x) >= 4]
    return not topic_words or any(word and word in normalize(description) for word in topic_words)


def body_excerpt(source: str, topic: str) -> str:
    body_match = BODY_RE.search(source)
    body = body_match.group(0) if body_match else source
    candidates: list[str] = []
    for m in P_RE.finditer(body):
        text = strip_tags(m.group(1))
        if 35 <= len(text) <= 420 and not any(x in text for x in ("جميع الحقوق", "Google Tag Manager")):
            candidates.append(text)
        if sum(len(x) for x in candidates) >= 170:
            break
    text = " ".join(candidates) if candidates else visible_body(source)[:240]
    if topic and normalize(topic) not in normalize(text[:120]):
        text = f"{topic}: {text}"
    text = " ".join(text.split())
    if len(text) > 180:
        text = text[:181].rsplit(" ", 1)[0].rstrip(" ،؛:|-–—")
    return text


def image_for(head: str, site: Path) -> str:
    current = get_meta(head, "property", "og:image") or get_meta(head, "name", "twitter:image")
    if current:
        parsed = urlparse(current)
        if parsed.scheme in {"http", "https"} and parsed.netloc and parsed.netloc.lower() != "healthrenewal.org":
            return current
        local = site / (parsed.path if parsed.scheme else current).lstrip("/")
        if local.is_file():
            return current if parsed.scheme else ORIGIN + "/" + current.lstrip("/")
    for rel in ("assets/brand/rawafid-social-card.jpg", "assets/brand/social-card.svg", "assets/brand/logo-mark.svg"):
        if (site / rel).is_file():
            return f"{ORIGIN}/{rel}"
    return ""


def clean_broken_hreflang(head: str, site: Path) -> tuple[str, int]:
    removed = 0
    out: list[str] = []
    cursor = 0
    for m in LINK_TAG_RE.finditer(head):
        out.append(head[cursor:m.start()])
        tag = m.group(0)
        data = attrs(tag)
        hreflang = data.get("hreflang", "")
        href = data.get("href", "")
        rels = {x.lower() for x in data.get("rel", "").split()}
        broken = False
        if hreflang and "alternate" in rels and href:
            parsed = urlparse(href)
            if (not parsed.netloc or parsed.netloc.lower() == "healthrenewal.org"):
                route = parsed.path or "/"
                candidates = [site / route.lstrip("/")]
                if route.endswith("/"):
                    candidates.append(site / route.lstrip("/") / "index.html")
                else:
                    candidates.append(site / route.lstrip("/") / "index.html")
                    candidates.append(site / (route.lstrip("/") + ".html"))
                broken = not any(x.is_file() for x in candidates)
        if broken:
            removed += 1
        else:
            out.append(tag)
        cursor = m.end()
    out.append(head[cursor:])
    return "".join(out), removed


def ensure_html_ar(source: str) -> tuple[str, bool]:
    m = HTML_RE.search(source)
    if not m:
        return source, False
    tag = m.group(0)
    data = attrs(tag)
    changed = False
    if not data.get("lang", "").lower().startswith("ar"):
        if re.search(r"(?is)\blang\s*=\s*([\"']).*?\1", tag):
            tag = re.sub(r"(?is)\blang\s*=\s*([\"']).*?\1", 'lang="ar"', tag, count=1)
        else:
            tag = tag[:-1] + ' lang="ar">'
        changed = True
    if not data.get("dir"):
        tag = tag[:-1] + ' dir="rtl">'
        changed = True
    if not changed:
        return source, False
    return source[:m.start()] + tag + source[m.end():], True


def build_owned_schema(canonical: str, topic: str, description: str, root: str, section: str, base_types: set[str]) -> dict[str, Any] | None:
    graph: list[dict[str, Any]] = []
    needs_page = not bool(PAGE_SCHEMA_TYPES & base_types)
    needs_breadcrumb = "BreadcrumbList" not in base_types
    if needs_page:
        page: dict[str, Any] = {
            "@type": "WebPage",
            "@id": canonical + "#webpage",
            "url": canonical,
            "name": topic,
            "description": description,
            "inLanguage": "ar",
            "isPartOf": {"@id": ORIGIN + "/#website"},
        }
        if needs_breadcrumb:
            page["breadcrumb"] = {"@id": canonical + "#breadcrumb"}
        graph.append(page)
    if needs_breadcrumb:
        section_url = f"{ORIGIN}/{root}/"
        items: list[dict[str, Any]] = [
            {"@type": "ListItem", "position": 1, "name": SITE_AR, "item": ORIGIN + "/"},
            {"@type": "ListItem", "position": 2, "name": section, "item": section_url},
        ]
        if canonical.rstrip("/") != section_url.rstrip("/"):
            items.append({"@type": "ListItem", "position": 3, "name": topic, "item": canonical})
        graph.append({"@type": "BreadcrumbList", "@id": canonical + "#breadcrumb", "itemListElement": items})
    if not graph:
        return None
    return {"@context": "https://schema.org", "@graph": graph}


def root_and_section(path: Path, site: Path) -> tuple[str, str]:
    root = path.relative_to(site).parts[0]
    return root, SECTION_NAMES.get(root, root)


def discover(site: Path) -> list[Path]:
    output: list[Path] = []
    for root in SCOPE_ROOTS:
        directory = site / root
        if directory.is_dir():
            output.extend(x for x in directory.rglob("*.html") if x.is_file())
    return sorted(set(output), key=lambda x: x.relative_to(site).as_posix())


def intent_key(topic: str) -> str:
    value = normalize(topic)
    value = re.sub(r"\b(?:اختبار|مقياس|مهمة|أداة|اداة|مختبر|تقييم|دليل)\b", " ", value)
    return " ".join(value.split()) or normalize(topic)


def content_terms(source: str, topic: str, limit: int = 48) -> list[str]:
    body = visible_body(source)
    topic_norm = normalize(topic)
    counts: Counter[str] = Counter()
    order: dict[str, int] = {}
    raw = tokens(body)
    for idx, token in enumerate(raw):
        token = token.strip("-_.,،؛:()[]{}\"'")
        n = normalize(token)
        if len(token) < 4 or len(token) > 30 or token in STOPWORDS or not n or n in topic_norm:
            continue
        counts[token] += 1
        order.setdefault(token, idx)
    phrases: list[str] = []
    for m in HEADING_RE.finditer(source):
        value = strip_tags(m.group(1))
        if 4 <= len(value) <= 70 and normalize(value) not in topic_norm:
            phrases.append(value)
    ranked = sorted(counts, key=lambda x: (-counts[x], order[x], x))
    output: list[str] = []
    seen: set[str] = set()
    for value in [*phrases, *ranked]:
        key = normalize(value)
        if key and key not in seen:
            seen.add(key)
            output.append(value)
        if len(output) >= limit:
            break
    return output


def spelling_variants(topic: str) -> list[str]:
    candidates = [
        topic.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا"),
        topic.replace("ة", "ه"),
        topic.replace("ى", "ي"),
    ]
    output: list[str] = []
    seen = {normalize(topic)}
    for value in candidates:
        value = " ".join(value.split())
        key = normalize(value)
        if value and key not in seen:
            seen.add(key)
            output.append(value)
    return output[:3]


def semantic_queries(topic: str, source: str, minimum: int = 500) -> list[str]:
    terms = content_terms(source, topic)
    queries: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        value = " ".join(value.split()).strip(" ،؛:|-–—")
        key = normalize(value)
        if value and 3 <= len(value) <= 180 and key not in seen:
            seen.add(key)
            queries.append(value)

    for value in (
        topic,
        f"ما هو {topic}",
        f"شرح {topic}",
        f"دليل {topic}",
        f"كيفية استخدام {topic}",
        f"طريقة استخدام {topic}",
        f"أسئلة عن {topic}",
        f"{topic} روافد",
        f"{topic} Health Renewal",
    ):
        add(value)
    for variant in spelling_variants(topic):
        add(variant)
        add(f"شرح {variant}")
        add(f"{variant} روافد")
    for term in terms:
        for template in QUERY_TEMPLATES:
            add(template.format(topic=topic, term=term))
    if len(queries) < minimum:
        for i, a in enumerate(terms):
            for b in terms[i + 1:]:
                if normalize(a) == normalize(b):
                    continue
                for template in PAIR_TEMPLATES:
                    add(template.format(topic=topic, a=a, b=b))
                    if len(queries) >= minimum:
                        break
                if len(queries) >= minimum:
                    break
            if len(queries) >= minimum:
                break
    if len(queries) < minimum:
        raise ValueError(f"semantic map below {minimum}: {len(queries)}")
    return queries[:minimum]


def sitemap_text(site: Path) -> str:
    parts: list[str] = []
    for path in sorted(site.glob("sitemap*.xml")):
        try:
            parts.append(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    return "\n".join(parts)


def build_plan(
    path: Path,
    site: Path,
    title_counts: Counter[str],
    desc_counts: Counter[str],
    intent_counts: Counter[str],
) -> PagePlan | None:
    original = path.read_text(encoding="utf-8")
    hm = HEAD_RE.search(original)
    if not hm:
        raise ValueError("missing <head>")
    head = hm.group(2)
    if not indexable(head):
        return None
    root, section = root_and_section(path, site)
    topic = topic_for(original, head, path)
    canonical = ORIGIN + route_for(path, site)
    current_title = get_title(head)
    current_desc = get_meta(head, "name", "description")
    duplicated_topic = intent_counts[intent_key(topic)] > 1
    title = current_title if title_supported(current_title, topic) and title_counts[normalize(current_title)] == 1 else build_title(topic, section, duplicated_topic)
    description = current_desc if description_supported(current_desc, topic) and desc_counts[normalize(current_desc)] == 1 else body_excerpt(original, topic)
    primary_intent = topic if not duplicated_topic else f"{topic} — {section}"

    base_head = MARKER_RE.sub("", head)
    had_owned_schema = bool(OWN_SCHEMA_RE.search(base_head))
    base_head = OWN_SCHEMA_RE.sub("", base_head)
    payloads, json_errors = existing_jsonld(base_head, exclude_owned=False)
    if json_errors:
        raise ValueError("invalid existing JSON-LD: " + "; ".join(json_errors[:2]))
    base_types: set[str] = set()
    for payload in payloads:
        base_types.update(schema_types(payload))
    owned_schema = build_owned_schema(canonical, topic, description, root, section, base_types)

    new_head = base_head
    changes: list[str] = []
    if current_title != title or head.count("<title") != 1:
        new_head = replace_title(new_head, title)
        changes.append("title")
    if current_desc != description or len(re.findall(r"(?is)<meta\b[^>]*\bname\s*=\s*([\"'])description\1", head)) != 1:
        new_head = replace_meta(new_head, "name", "description", description)
        changes.append("meta-description")
    if get_canonical(head) != canonical or len([t for t in LINK_TAG_RE.findall(head) if "canonical" in {x.lower() for x in attrs(t).get("rel", "").split()}]) != 1:
        new_head = replace_canonical(new_head, canonical)
        changes.append("canonical")

    robots = get_meta(head, "name", "robots")
    desired_robots = "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
    if normalize(robots.replace(",", " ")) != normalize(desired_robots.replace(",", " ")):
        new_head = replace_meta(new_head, "name", "robots", desired_robots)
        changes.append("robots-indexability")

    desired_site_name = get_meta(head, "property", "og:site_name") or "روافد | Health Renewal"
    if "روافد" not in desired_site_name:
        desired_site_name = "روافد | Health Renewal"
    metadata = (
        ("property", "og:type", get_meta(head, "property", "og:type") or "website", "og-type"),
        ("property", "og:locale", "ar_AR", "og-locale"),
        ("property", "og:site_name", desired_site_name, "og-site-name"),
        ("property", "og:title", title, "og-title"),
        ("property", "og:description", description, "og-description"),
        ("property", "og:url", canonical, "og-url"),
        ("name", "twitter:title", title, "twitter-title"),
        ("name", "twitter:description", description, "twitter-description"),
    )
    for attr, key, value, label in metadata:
        if get_meta(head, attr, key) != value:
            new_head = replace_meta(new_head, attr, key, value)
            changes.append(label)

    image = image_for(head, site)
    if image:
        if get_meta(head, "property", "og:image") != image:
            new_head = replace_meta(new_head, "property", "og:image", image)
            changes.append("og-image")
        if get_meta(head, "name", "twitter:image") != image:
            new_head = replace_meta(new_head, "name", "twitter:image", image)
            changes.append("twitter-image")
        if not get_meta(head, "property", "og:image:alt"):
            new_head = replace_meta(new_head, "property", "og:image:alt", f"{topic} — روافد")
            changes.append("og-image-alt")
        if not get_meta(head, "name", "twitter:image:alt"):
            new_head = replace_meta(new_head, "name", "twitter:image:alt", f"{topic} — روافد")
            changes.append("twitter-image-alt")
        desired_card = "summary_large_image"
    else:
        desired_card = "summary"
    if get_meta(head, "name", "twitter:card") != desired_card:
        new_head = replace_meta(new_head, "name", "twitter:card", desired_card)
        changes.append("twitter-card")

    new_head, removed_hreflang = clean_broken_hreflang(new_head, site)
    if removed_hreflang:
        changes.append(f"remove-broken-hreflang:{removed_hreflang}")

    if owned_schema is not None:
        encoded = json.dumps(owned_schema, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        new_head = new_head.rstrip() + f'\n<script type="application/ld+json" data-rawafid-seo="{PROFILE}">{encoded}</script>\n'
        if not had_owned_schema:
            if not (PAGE_SCHEMA_TYPES & base_types):
                changes.append("schema-WebPage")
            if "BreadcrumbList" not in base_types:
                changes.append("schema-BreadcrumbList")
    elif had_owned_schema:
        changes.append("remove-redundant-owned-schema")

    interim = original[:hm.start(2)] + new_head + original[hm.end(2):]
    interim, lang_changed = ensure_html_ar(interim)
    if lang_changed:
        changes.append("lang-locale")

    material = bool(changes)
    body_hash = raw_body_hash(original)
    fingerprint_source = json.dumps(
        {
            "profile": PROFILE,
            "path": path.relative_to(site).as_posix(),
            "body": body_hash,
            "title": title,
            "description": description,
            "canonical": canonical,
            "primaryIntent": primary_intent,
            "changes": changes,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    fingerprint = sha(fingerprint_source)[:24]
    if material:
        hm2 = HEAD_RE.search(interim)
        assert hm2
        marked = hm2.group(2).rstrip() + f"\n<!-- rawafid-tools-assessment-seo:v1 fingerprint={fingerprint} -->\n"
        interim = interim[:hm2.start(2)] + marked + interim[hm2.end(2):]

    if raw_body_hash(interim) != body_hash:
        raise ValueError("visible/raw body changed during head-only mutation")
    rel = path.relative_to(site).as_posix()
    return PagePlan(path, rel, canonical, root, section, topic, title, description, primary_intent, body_hash, original, interim, changes, fingerprint)


def verify_page(plan: PagePlan, site: Path, sitemap: str) -> None:
    source = plan.path.read_text(encoding="utf-8")
    if raw_body_hash(source) != plan.body_hash:
        raise ValueError("body hash changed after write")
    hm = HEAD_RE.search(source)
    if not hm:
        raise ValueError("head missing after write")
    head = hm.group(2)
    if get_title(head) != plan.title:
        raise ValueError("title mismatch")
    if get_meta(head, "name", "description") != plan.description:
        raise ValueError("description mismatch")
    if get_canonical(head) != plan.url:
        raise ValueError("canonical mismatch")
    if not indexable(head):
        raise ValueError("unexpected noindex")
    for attr, key, expected in (
        ("property", "og:title", plan.title),
        ("property", "og:description", plan.description),
        ("property", "og:url", plan.url),
        ("property", "og:locale", "ar_AR"),
        ("name", "twitter:title", plan.title),
        ("name", "twitter:description", plan.description),
    ):
        if get_meta(head, attr, key) != expected:
            raise ValueError(f"metadata mismatch: {key}")
    _, errors = existing_jsonld(head, exclude_owned=False)
    if errors:
        raise ValueError("invalid JSON-LD after write")
    all_payloads, _ = existing_jsonld(head, exclude_owned=False)
    types: set[str] = set()
    for payload in all_payloads:
        types.update(schema_types(payload))
    if not (PAGE_SCHEMA_TYPES & types):
        raise ValueError("missing page-level structured data")
    if "BreadcrumbList" not in types:
        raise ValueError("missing BreadcrumbList")
    if plan.url not in sitemap:
        raise ValueError("canonical missing from generated sitemap")
    if not MARKER_RE.search(head):
        raise ValueError("fingerprint marker missing")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("--target", type=int, default=50)
    parser.add_argument("--manifest", type=Path, default=Path("_seo_private/tools-assessment-search-map-v1.json"))
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    site = args.site.resolve()
    if not site.is_dir():
        print(f"site not found: {site}", file=sys.stderr)
        return 2
    pages = discover(site)
    sitemap = sitemap_text(site)
    if not sitemap:
        print("generated sitemap is missing", file=sys.stderr)
        return 2

    basic: dict[Path, tuple[str, str, str, str, str]] = {}
    title_counts: Counter[str] = Counter()
    desc_counts: Counter[str] = Counter()
    intent_counts: Counter[str] = Counter()
    skipped_noindex: list[str] = []
    scan_failures: list[str] = []

    for path in pages:
        rel = path.relative_to(site).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            hm = HEAD_RE.search(source)
            if not hm:
                raise ValueError("missing head")
            head = hm.group(2)
            if not indexable(head):
                skipped_noindex.append(rel)
                continue
            topic = topic_for(source, head, path)
            title = get_title(head)
            desc = get_meta(head, "name", "description")
            root, section = root_and_section(path, site)
            basic[path] = (root, section, topic, title, desc)
            if title:
                title_counts[normalize(title)] += 1
            if desc:
                desc_counts[normalize(desc)] += 1
            intent_counts[intent_key(topic)] += 1
        except Exception as exc:
            scan_failures.append(f"{rel}: {exc}")

    plans: list[PagePlan] = []
    noops: list[str] = []
    plan_failures: list[str] = []
    for path in basic:
        rel = path.relative_to(site).as_posix()
        try:
            plan = build_plan(path, site, title_counts, desc_counts, intent_counts)
            if plan is None:
                skipped_noindex.append(rel)
            elif plan.updated == plan.original or not plan.changes:
                noops.append(rel)
            else:
                plans.append(plan)
        except Exception as exc:
            plan_failures.append(f"{rel}: {exc}")

    # Prioritize the most materially deficient pages; deterministic path is the tie-breaker.
    plans.sort(key=lambda p: (-len(p.changes), p.rel))
    results: list[Result] = []
    successful: list[PagePlan] = []
    failed: list[str] = [*scan_failures, *plan_failures]
    attempted: set[str] = set()

    for plan in plans:
        if len(successful) >= args.target:
            break
        attempted.add(plan.rel)
        try:
            plan.path.write_text(plan.updated, encoding="utf-8", newline="\n")
            verify_page(plan, site, sitemap)
            successful.append(plan)
            results.append(Result(plan.rel, plan.url, "success", plan.changes, fingerprint=plan.fingerprint))
        except Exception as exc:
            try:
                plan.path.write_text(plan.original, encoding="utf-8", newline="\n")
            except Exception:
                pass
            failed.append(f"{plan.rel}: {exc}")
            results.append(Result(plan.rel, plan.url, "failed", plan.changes, detail=str(exc), fingerprint=plan.fingerprint))

    # Build the internal semantic map for every indexable page in this owned scope.
    manifest_pages: dict[str, Any] = {}
    semantic_failures: list[str] = []
    updated_by_rel = {p.rel: p for p in successful}
    for path, (root, section, topic, _, _) in basic.items():
        rel = path.relative_to(site).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            queries = semantic_queries(topic, source, 500)
            primary = topic if intent_counts[intent_key(topic)] == 1 else f"{topic} — {section}"
            record = {
                "path": rel,
                "url": ORIGIN + route_for(path, site),
                "root": root,
                "topic": topic,
                "primaryIntent": primary,
                "cannibalizationKey": intent_key(topic),
                "cannibalizationCount": intent_counts[intent_key(topic)],
                "queryCount": len(queries),
                "queries": queries,
                "bodyHash": raw_body_hash(source),
                "lastOptimizationFingerprint": updated_by_rel.get(rel).fingerprint if rel in updated_by_rel else "",
                "lastOptimizationState": "success" if rel in updated_by_rel else "unchanged",
            }
            manifest_pages[rel] = record
            if rel in updated_by_rel:
                for result in results:
                    if result.path == rel and result.status == "success":
                        result.query_count = len(queries)
                        break
        except Exception as exc:
            semantic_failures.append(f"{rel}: {exc}")

    failed.extend(semantic_failures)
    cannibalization = [
        {"key": key, "count": count, "paths": [p.relative_to(site).as_posix() for p, data in basic.items() if intent_key(data[2]) == key]}
        for key, count in sorted(intent_counts.items()) if count > 1
    ]
    manifest = {
        "schemaVersion": 1,
        "profile": PROFILE,
        "generatedAt": now_iso(),
        "siteOrigin": ORIGIN,
        "scopeRoots": list(SCOPE_ROOTS),
        "policy": {
            "internalOnly": True,
            "metaKeywords": False,
            "hiddenText": False,
            "minimumQueriesPerPage": 500,
            "visibleContentMutation": False,
        },
        "pages": manifest_pages,
        "cannibalization": cannibalization,
    }
    write_json(args.manifest, manifest)

    remaining = [p.rel for p in plans if p.rel not in attempted]
    status = "passed" if len(successful) >= args.target and not semantic_failures else "incomplete"
    report = {
        "schemaVersion": 1,
        "profile": PROFILE,
        "status": status,
        "generatedAt": now_iso(),
        "target": args.target,
        "success": len(successful),
        "skippedNoindex": len(set(skipped_noindex)),
        "noOpAlreadyOptimal": len(noops),
        "failed": len(failed),
        "failures": failed,
        "scopePagesDiscovered": len(pages),
        "indexableOwnedPages": len(basic),
        "materialCandidates": len(plans),
        "remainingEligible": len(remaining),
        "remainingEligiblePaths": remaining,
        "manifestPages": len(manifest_pages),
        "manifestMinimumQueryCount": min((v["queryCount"] for v in manifest_pages.values()), default=0),
        "sitemapVerifiedSuccesses": all(p.url in sitemap for p in successful),
        "cannibalizationClusters": cannibalization,
        "results": [asdict(x) for x in results],
        "changesSummary": dict(Counter(change.split(":", 1)[0] for p in successful for change in p.changes)),
        "scopePolicy": "head-only; no visible text/H1/H2/URL/slug changes; no noindex override; no fabricated FAQ/author/reviewer/date/accreditation/rating/medical claims",
    }
    report_path = args.report or (site / "api/tools-assessment-seo-v1.json")
    write_json(report_path, report)
    write_json(site / "reports/tools-assessment-seo-v1.json", report)
    print(json.dumps({k: report[k] for k in (
        "status", "target", "success", "noOpAlreadyOptimal", "failed", "scopePagesDiscovered",
        "indexableOwnedPages", "materialCandidates", "remainingEligible", "manifestPages", "manifestMinimumQueryCount",
        "sitemapVerifiedSuccesses", "changesSummary"
    )}, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
