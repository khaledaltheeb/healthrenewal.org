from __future__ import annotations

import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_URL = "https://healthrenewal.org/"
API_BASE = f"{BASE_URL}api/v1/"
SCHEMA_VERSION = 219
SHARD_SIZE = 400
SKIP_FILES = {"404.html", "offline.html", "google644f1f7a8b7aaa2b.html"}
SKIP_PREFIXES = ("coverage/", "reports/", "tmp/", "node_modules/")
KEYWORD_SPLIT_RE = re.compile(r"[,،;؛|]+")
SPACE_RE = re.compile(r"\s+")

SECTION_LABELS = {
    "home": {"ar": "الرئيسية", "en": "Home", "es": "Inicio"},
    "encyclopedia": {"ar": "الموسوعة النفسية", "en": "Psychology encyclopedia", "es": "Enciclopedia de psicología"},
    "terms": {"ar": "المعجم النفسي", "en": "Psychology glossary", "es": "Glosario de psicología"},
    "hubs": {"ar": "المراكز الموضوعية", "en": "Topic hubs", "es": "Centros temáticos"},
    "special-needs": {"ar": "ذوو الاحتياجات الخاصة", "en": "Special needs", "es": "Necesidades especiales"},
    "care-guides": {"ar": "أدلة التعامل", "en": "Care guides", "es": "Guías de apoyo"},
    "tips": {"ar": "النصائح النفسية", "en": "Mental health tips", "es": "Consejos de salud mental"},
    "assessment-lab": {"ar": "المقاييس والاستكشاف", "en": "Assessment lab", "es": "Laboratorio de evaluación"},
    "cognitive-lab": {"ar": "القدرات المعرفية", "en": "Cognitive abilities", "es": "Capacidades cognitivas"},
    "provider-assessment-demo": {"ar": "منصة التقييم المهني", "en": "Professional assessment", "es": "Evaluación profesional"},
    "magazine": {"ar": "المجلة والأبحاث", "en": "Magazine and research", "es": "Revista e investigación"},
    "developers": {"ar": "واجهة المطورين", "en": "Developer API", "es": "API para desarrolladores"},
    "trust": {"ar": "الثقة والمنهجية", "en": "Trust and methodology", "es": "Confianza y metodología"},
    "partners": {"ar": "الشركاء والشفافية", "en": "Partners and transparency", "es": "Socios y transparencia"},
    "sectors-child": {"ar": "الصحة النفسية للطفل", "en": "Child mental health", "es": "Salud mental infantil"},
    "sectors-family": {"ar": "الصحة النفسية للأسرة", "en": "Family mental health", "es": "Salud mental familiar"},
    "sectors-home": {"ar": "الصحة النفسية للعائلة", "en": "Household mental health", "es": "Salud mental del hogar"},
}


class ContentDiscoveryError(ValueError):
    pass


@dataclass
class PageMetadata:
    language: str = "ar"
    direction: str = "rtl"
    title: str = ""
    description: str = ""
    canonical: str = ""
    robots: str = ""
    keywords: list[str] = field(default_factory=list)
    h1: str = ""


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta = PageMetadata()
        self.capture: str | None = None
        self.buffer: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        if lower == "html":
            language = values.get("lang", "ar").split("-", 1)[0].lower()
            self.meta.language = language if language in {"ar", "en", "es"} else "ar"
            self.meta.direction = values.get("dir") or ("rtl" if self.meta.language == "ar" else "ltr")
        elif lower == "meta":
            name = values.get("name", "").lower()
            content = clean(values.get("content", ""))
            if name == "description":
                self.meta.description = content
            elif name == "robots":
                self.meta.robots = content.lower()
            elif name == "keywords":
                self.meta.keywords = split_keywords(content)
        elif lower == "link":
            rels = values.get("rel", "").lower().split()
            if "canonical" in rels:
                self.meta.canonical = clean(values.get("href", ""))
        elif lower in {"script", "style", "template", "noscript"}:
            self.skip_depth += 1
        elif lower == "title":
            self.capture = "title"
            self.buffer = []
        elif lower == "h1" and not self.meta.h1:
            self.capture = "h1"
            self.buffer = []

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "template", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        if self.capture == lower:
            value = clean(" ".join(self.buffer))
            if lower == "title":
                self.meta.title = value
            else:
                self.meta.h1 = value
            self.capture = None
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not self.capture:
            return
        value = clean(data)
        if value:
            self.buffer.append(value)


def clean(value: object) -> str:
    return SPACE_RE.sub(" ", html.unescape(str(value))).strip()


def split_keywords(value: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in KEYWORD_SPLIT_RE.split(value):
        item = clean(raw).strip(" .,:;،؛|-—_")
        key = item.casefold()
        if 2 <= len(item) <= 100 and key not in seen:
            seen.add(key)
            result.append(item)
    return result[:16]


def parse_page(source: str) -> PageMetadata:
    parser = PageParser()
    parser.feed(source)
    parser.close()
    return parser.meta


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContentDiscoveryError(f"invalid JSON: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ContentDiscoveryError(f"expected object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def generated_date() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def relative_route(page: Path, site: Path) -> str:
    relative = page.relative_to(site).as_posix()
    if relative == "index.html":
        return ""
    if relative.endswith("/index.html"):
        return relative[: -len("index.html")]
    return relative


def section_id(route: str) -> str:
    parts = [part for part in route.strip("/").split("/") if part]
    if not parts:
        return "home"
    if parts[0] == "sectors" and len(parts) > 1:
        return f"sectors-{parts[1]}"
    return parts[0]


def section_labels(identifier: str) -> dict[str, str]:
    if identifier in SECTION_LABELS:
        return SECTION_LABELS[identifier]
    label = identifier.replace("-", " ").title()
    return {"ar": label, "en": label, "es": label}


def canonical_is_public(url: str) -> bool:
    parsed = urlparse(url)
    base = urlparse(BASE_URL)
    return (
        parsed.scheme == "https"
        and parsed.netloc == base.netloc
        and parsed.path.startswith(base.path)
        and parsed.query == ""
        and parsed.fragment == ""
    )


def topic_id(label: str) -> str:
    normalized = clean(label).casefold().encode("utf-8")
    return "topic-" + hashlib.sha1(normalized).hexdigest()[:12]


def collect_items(site: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ids: set[str] = set()
    canonicals: set[str] = set()
    for page in sorted(site.rglob("*.html")):
        relative = page.relative_to(site).as_posix()
        if page.name in SKIP_FILES or relative.startswith(SKIP_PREFIXES):
            continue
        meta = parse_page(page.read_text(encoding="utf-8"))
        if "noindex" in meta.robots:
            continue
        missing = [
            name
            for name, value in {
                "title": meta.title,
                "description": meta.description,
                "canonical": meta.canonical,
                "keywords": meta.keywords,
            }.items()
            if not value
        ]
        if missing:
            raise ContentDiscoveryError(f"{relative}: missing {', '.join(missing)}")
        if not canonical_is_public(meta.canonical):
            raise ContentDiscoveryError(f"{relative}: invalid public canonical {meta.canonical}")
        route = relative_route(page, site)
        identifier = route.strip("/") or "home"
        if identifier in ids:
            raise ContentDiscoveryError(f"duplicate content id: {identifier}")
        if meta.canonical in canonicals:
            raise ContentDiscoveryError(f"duplicate canonical: {meta.canonical}")
        ids.add(identifier)
        canonicals.add(meta.canonical)
        section = section_id(route)
        items.append(
            {
                "id": identifier,
                "path": "/" + route.lstrip("/"),
                "url": meta.canonical,
                "language": meta.language,
                "direction": meta.direction,
                "section": section,
                "section_label": section_labels(section).get(meta.language, section_labels(section)["en"]),
                "title": meta.title,
                "description": meta.description,
                "h1": meta.h1,
                "keywords": meta.keywords,
            }
        )
    return sorted(items, key=lambda item: (str(item["language"]), str(item["path"])))


def patch_openapi(openapi_path: Path) -> None:
    document = read_json(openapi_path)
    paths = document.setdefault("paths", {})
    paths["/api/v1/content-index.json"] = {
        "get": {
            "summary": "فهرس المحتوى العام المقسم إلى دفعات",
            "description": "بيانات وصفية للصفحات العامة القابلة للفهرسة دون بيانات مستخدمين أو سجلات صحية.",
            "responses": {
                "200": {
                    "description": "بيان الفهرس وروابط الدفعات",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ContentIndexManifest"}}},
                }
            },
        }
    }
    paths["/api/v1/taxonomy.json"] = {
        "get": {
            "summary": "تصنيف اللغات والأقسام والموضوعات",
            "responses": {
                "200": {
                    "description": "التصنيف الموضوعي للمحتوى العام",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ContentTaxonomy"}}},
                }
            },
        }
    }
    schemas = document.setdefault("components", {}).setdefault("schemas", {})
    schemas["ContentIndexManifest"] = {
        "type": "object",
        "required": ["api_version", "schema_version", "generated_at", "total", "shards"],
        "properties": {
            "api_version": {"const": "v1"},
            "schema_version": {"const": SCHEMA_VERSION},
            "generated_at": {"type": "string", "format": "date"},
            "total": {"type": "integer", "minimum": 0},
            "shard_size": {"type": "integer", "minimum": 1},
            "shards": {"type": "array", "items": {"type": "object"}},
        },
    }
    schemas["ContentItem"] = {
        "type": "object",
        "required": ["id", "path", "url", "language", "section", "title", "description", "keywords"],
        "properties": {
            "id": {"type": "string"},
            "path": {"type": "string"},
            "url": {"type": "string", "format": "uri"},
            "language": {"type": "string"},
            "direction": {"enum": ["rtl", "ltr"]},
            "section": {"type": "string"},
            "section_label": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "h1": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
        },
    }
    schemas["ContentTaxonomy"] = {
        "type": "object",
        "required": ["api_version", "schema_version", "generated_at", "total_pages", "languages", "sections", "topics"],
        "properties": {
            "api_version": {"const": "v1"},
            "schema_version": {"const": SCHEMA_VERSION},
            "generated_at": {"type": "string", "format": "date"},
            "total_pages": {"type": "integer", "minimum": 0},
            "languages": {"type": "array", "items": {"type": "object"}},
            "sections": {"type": "array", "items": {"type": "object"}},
            "topics": {"type": "array", "items": {"type": "object"}},
        },
    }
    write_json(openapi_path, document)


def developer_rows() -> str:
    return (
        '<tr data-content-discovery-v219><td><code>'
        + API_BASE
        + 'content-index.json</code></td><td>بيان فهرس الصفحات العامة وروابط الدفعات</td></tr>'
        '<tr data-content-discovery-v219><td><code>'
        + API_BASE
        + 'taxonomy.json</code></td><td>تصنيف اللغات والأقسام والموضوعات</td></tr>'
    )


def patch_developers_page(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if "data-content-discovery-v219" not in source:
        if "</tbody>" not in source:
            raise ContentDiscoveryError("developers page table is missing")
        source = source.replace("</tbody>", developer_rows() + "</tbody>", 1)
        card = (
            '<section class="panel" data-content-discovery-v219><h2>اكتشاف المحتوى</h2>'
            '<p>يوفر الفهرس بيانات وصفية للصفحات العامة في دفعات محدودة الحجم، مع تصنيف موضوعي يساعد المواقع والتطبيقات على بناء بحث وقوائم دون جمع بيانات مستخدمين.</p>'
            '<p><a href="content-discovery/">توثيق فهرس المحتوى والتصنيف</a></p></section>'
        )
        if "</main>" not in source:
            raise ContentDiscoveryError("developers page main landmark is missing")
        source = source.replace("</main>", card + "</main>", 1)
        path.write_text(source, encoding="utf-8")


def build_discovery_page() -> str:
    canonical = BASE_URL + "developers/content-discovery/"
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": "فهرس المحتوى والتصنيف الموضوعي",
            "description": "توثيق فهرس الصفحات العامة وتصنيف اللغات والأقسام والموضوعات.",
            "inLanguage": "ar",
            "url": canonical,
            "publisher": {"@type": "Organization", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة"},
        },
        ensure_ascii=False,
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>فهرس المحتوى والتصنيف الموضوعي | واجهة المطورين</title>
<meta name="description" content="توثيق فهرس API للصفحات العامة: دفعات محدودة الحجم، لغات وأقسام وموضوعات، دون بيانات شخصية أو سجلات صحية.">
<meta name="keywords" content="فهرس المحتوى,API عربي,تصنيف موضوعي,بيانات منظمة,الصحة النفسية,علم النفس,تكامل المواقع">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#075f5b">
<link rel="canonical" href="{canonical}"><link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="../../assets/brand/logo-mark.svg" type="image/svg+xml">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta property="og:title" content="فهرس المحتوى والتصنيف الموضوعي"><meta property="og:description" content="بيانات وصفية منظمة للصفحات العامة في دفعات قابلة للاستهلاك."><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE_URL}assets/brand/social-card.svg">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="فهرس المحتوى والتصنيف الموضوعي"><meta name="twitter:description" content="واجهة قراءة عامة للصفحات واللغات والأقسام والموضوعات."><meta name="twitter:image" content="{BASE_URL}assets/brand/social-card.svg">
<script type="application/ld+json">{schema}</script>
<style>:root{{--ink:#143f44;--muted:#527275;--brand:#0b6b66;--line:#b9ddd8;--soft:#e5faf7}}*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.85;color:var(--ink);background:linear-gradient(145deg,#fff,var(--soft))}}a{{color:#076b65}}.wrap{{width:min(980px,92%);margin:auto}}header{{background:#fff;border-bottom:1px solid var(--line)}}header .wrap{{display:flex;align-items:center;gap:12px;padding:15px 0}}header img{{width:48px;height:48px}}main{{padding:54px 0}}h1{{font-size:clamp(2.2rem,6vw,4rem);line-height:1.2}}.lead{{color:var(--muted);font-size:1.1rem}}.panel{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:22px;margin:18px 0;box-shadow:0 16px 40px rgba(31,105,104,.09)}}code,pre{{direction:ltr;text-align:left;unicode-bidi:embed;word-break:break-word}}pre{{overflow:auto;background:#f5fbfa;border:1px solid var(--line);padding:14px;border-radius:14px}}footer{{border-top:1px solid var(--line);padding:30px 0}}</style></head><body>
<header><div class="wrap"><a href="../"><img src="../../assets/brand/logo-mark.svg" alt="شعار المنصة"></a><strong>واجهة المطورين</strong></div></header><main class="wrap"><p><a href="../../">الرئيسية</a> ← <a href="../">واجهة المطورين</a> ← فهرس المحتوى</p>
<h1>فهرس المحتوى والتصنيف الموضوعي</h1><p class="lead">تتيح الواجهة اكتشاف الصفحات العامة القابلة للفهرسة دون نسخ محتواها الكامل ودون معالجة بيانات مستخدمين أو حالات أو جلسات.</p>
<section class="panel"><h2>بيان الفهرس</h2><p><code>{API_BASE}content-index.json</code></p><p>يعرض العدد الإجمالي، حجم الدفعة، وروابط ملفات الدفعات. تحتوي كل دفعة على العنوان والوصف والرابط القانوني واللغة والقسم والكلمات الموضوعية.</p></section>
<section class="panel"><h2>التصنيف الموضوعي</h2><p><code>{API_BASE}taxonomy.json</code></p><p>يعرض أعداد الصفحات حسب اللغة والقسم والموضوع، ويمكن استخدامه لبناء مرشحات وقوائم بحث.</p></section>
<section class="panel"><h2>مثال قراءة</h2><pre><code>const manifest = await fetch('{API_BASE}content-index.json').then(r =&gt; r.json());
const firstShard = await fetch(manifest.shards[0].url).then(r =&gt; r.json());
console.log(firstShard.items);</code></pre></section>
<section class="panel"><h2>حدود الاستخدام</h2><ul><li>الواجهة للقراءة العامة ولا تمنح حق إعادة نشر النصوص الكاملة.</li><li>لا تتضمن بيانات شخصية أو نتائج تقييم أو سجلات صحية.</li><li>المحتوى للتثقيف ولا يثبت تشخيصًا ولا يستبدل المختص.</li><li>استخدم التخزين المؤقت ومعدل طلبات معقولًا.</li></ul></section></main>
<footer><div class="wrap"><a href="../">واجهة المطورين</a> · <a href="../../trust/">الثقة والمنهجية</a> · <a href="../../">الرئيسية</a></div></footer></body></html>'''


def build_sitemap() -> str:
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    url = ET.SubElement(root, "url")
    ET.SubElement(url, "loc").text = BASE_URL + "developers/content-discovery/"
    ET.SubElement(url, "lastmod").text = generated_date()
    ET.SubElement(url, "changefreq").text = "monthly"
    ET.SubElement(url, "priority").text = "0.6"
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def prepare(site: Path, root: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ContentDiscoveryError(f"site output does not exist: {site}")
    api = site / "api" / "v1"
    openapi = api / "openapi.json"
    developers = site / "developers" / "index.html"
    if not openapi.is_file() or not developers.is_file():
        raise ContentDiscoveryError("public API v215 must run before content discovery preparation")
    patch_openapi(openapi)
    patch_developers_page(developers)
    detail = site / "developers" / "content-discovery" / "index.html"
    detail.parent.mkdir(parents=True, exist_ok=True)
    detail.write_text(build_discovery_page(), encoding="utf-8")
    (site / "sitemap-content-discovery.xml").write_text(build_sitemap(), encoding="utf-8")
    write_json(
        api / "content-index.json",
        {
            "api_version": "v1",
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_date(),
            "total": 0,
            "shard_size": SHARD_SIZE,
            "shards": [],
            "query_fields": ["title", "description", "keywords", "section", "language"],
            "usage_notice": "بيانات وصفية للصفحات العامة؛ لا تتضمن بيانات شخصية أو سجلات صحية.",
        },
    )
    write_json(
        api / "taxonomy.json",
        {
            "api_version": "v1",
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_date(),
            "total_pages": 0,
            "languages": [],
            "sections": [],
            "topics": [],
        },
    )
    report = {"schema_version": SCHEMA_VERSION, "prepared": True, "openapi": True, "developers_page": True}
    write_json(root / ".build" / "reports" / "content-discovery-prepare-v219.json", report)
    return report


def publish(site: Path, root: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ContentDiscoveryError(f"site output does not exist: {site}")
    api = site / "api" / "v1"
    openapi = api / "openapi.json"
    if not openapi.is_file():
        raise ContentDiscoveryError("openapi.json is missing")
    patch_openapi(openapi)
    items = collect_items(site)
    for stale in api.glob("content-index-*.json"):
        stale.unlink()

    shard_entries: list[dict[str, Any]] = []
    for offset in range(0, len(items), SHARD_SIZE):
        number = offset // SHARD_SIZE + 1
        chunk = items[offset : offset + SHARD_SIZE]
        filename = f"content-index-{number:03d}.json"
        write_json(
            api / filename,
            {
                "api_version": "v1",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_date(),
                "shard": number,
                "count": len(chunk),
                "items": chunk,
            },
        )
        shard_entries.append(
            {
                "id": number,
                "url": API_BASE + filename,
                "count": len(chunk),
                "first_path": chunk[0]["path"],
                "last_path": chunk[-1]["path"],
            }
        )

    language_counts: Counter[str] = Counter()
    section_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    topic_labels: dict[str, str] = {}
    for item in items:
        language_counts[str(item["language"])] += 1
        section_counts[str(item["section"])] += 1
        for keyword in item["keywords"]:
            identifier = topic_id(str(keyword))
            topic_counts[identifier] += 1
            topic_labels.setdefault(identifier, str(keyword))

    manifest = {
        "api_version": "v1",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_date(),
        "total": len(items),
        "shard_size": SHARD_SIZE,
        "shards": shard_entries,
        "query_fields": ["title", "description", "keywords", "section", "language"],
        "usage_notice": "بيانات وصفية للصفحات العامة؛ لا تتضمن بيانات شخصية أو نتائج تقييم أو سجلات صحية.",
    }
    taxonomy = {
        "api_version": "v1",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_date(),
        "total_pages": len(items),
        "languages": [
            {"code": key, "pages": language_counts[key]}
            for key in sorted(language_counts)
        ],
        "sections": [
            {"id": key, "labels": section_labels(key), "pages": section_counts[key]}
            for key in sorted(section_counts)
        ],
        "topics": [
            {"id": key, "label": topic_labels[key], "pages": topic_counts[key]}
            for key in sorted(topic_counts, key=lambda value: (-topic_counts[value], topic_labels[value].casefold()))
        ],
    }
    write_json(api / "content-index.json", manifest)
    write_json(api / "taxonomy.json", taxonomy)
    report = {
        "schema_version": SCHEMA_VERSION,
        "pages": len(items),
        "shards": len(shard_entries),
        "languages": len(language_counts),
        "sections": len(section_counts),
        "topics": len(topic_counts),
        "personal_data": False,
        "clinical_records": False,
        "openapi": True,
    }
    write_json(root / ".build" / "reports" / "content-discovery-v219.json", report)
    return report
