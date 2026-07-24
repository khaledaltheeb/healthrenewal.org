#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
HOST = "khaledaltheeb.github.io"
VERIFY = "google644f1f7a8b7aaa2b.html"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
DEFAULT_IMAGE = BASE_URL + "assets/icons/icon-512.png"
HIDDEN_STYLE = ".visually-hidden-v215{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}"
OPERATIONAL_TOKENS = (
    "built-not-published", "published-unverified", "current_confirmed_count",
    "pending-production-audit", "ما تم إنجازه", "ما سيتم إنجازه",
    "خطة العمل الحالية", "خارطة الطريق", "قيد الإعداد", "قيد التوسع",
    "سيتم الإضافة لاحقًا",
)
SECTION_KEYWORDS = (
    ("special-needs/", ("ذوو الاحتياجات الخاصة", "التربية الدامجة", "الإتاحة", "الدعم الأسري")),
    ("encyclopedia/", ("علم النفس", "الصحة النفسية", "الموسوعة النفسية العربية", "مصطلحات علم النفس")),
    ("assessment-lab/", ("المقاييس النفسية", "التقييم النفسي الاسترشادي", "المتابعة النفسية")),
    ("cognitive-lab/", ("الاختبارات المعرفية", "الوظائف التنفيذية", "الانتباه والذاكرة")),
    ("guided-assessment/", ("أسئلة التقييم النفسي", "التثقيف النفسي", "طلب المساعدة")),
    ("comparisons/", ("الفروق النفسية", "مقارنة المفاهيم النفسية", "علم النفس")),
    ("care-guides/", ("أدلة التعامل", "الدعم النفسي", "الأسرة")),
    ("tips/", ("نصائح نفسية", "جودة الحياة", "مهارات عملية")),
    ("sectors/child/", ("الصحة النفسية للطفل", "تربية الأطفال", "دعم الطفل")),
    ("sectors/family/", ("الصحة النفسية للأسرة", "العلاقات الأسرية", "الدعم الأسري")),
    ("sectors/home/", ("الصحة النفسية للعائلة", "المنزل الداعم", "الترابط الأسري")),
    ("sectors/women/", ("الصحة النفسية للمرأة", "دعم المرأة", "جودة الحياة")),
    ("library/", ("مكتبة علم النفس", "أبحاث علم النفس", "مصادر الصحة النفسية")),
    ("provider-assessment-demo/", ("منصة التقييم المؤسسية", "إدارة الحالات", "المقاييس المهنية")),
    ("api/", ("واجهة API", "تكامل البيانات", "OpenAPI", "استيراد الدورات المخولة")),
)


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


def attr(tag: str, key: str) -> str:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
    return html.unescape(match.group(2)).strip() if match else ""


def tags(text: str, name: str) -> list[str]:
    return re.findall(rf"<{name}\b[^>]*>", text, re.I)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def title_of(text: str) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, re.I | re.S)
    return clean(match.group(1)) if match else BRAND


def description_of(text: str, title: str) -> str:
    for tag in tags(text, "meta"):
        if attr(tag, "name").lower() == "description":
            value = attr(tag, "content")
            if value:
                return value
    return f"{title} — محتوى عربي موثوق ومنظم يشرح المفهوم والفروق والخطوات العملية والحدود المهنية."


def canonical_of(text: str, page: Path) -> str:
    for tag in tags(text, "link"):
        if "canonical" in attr(tag, "rel").lower().split() and attr(tag, "href"):
            return attr(tag, "href")
    rel = page.relative_to(SITE).as_posix()
    return BASE_URL + ("" if rel == "index.html" else rel.removesuffix("index.html"))


def meta_value(text: str, key: str, *, prop: bool = False) -> str:
    field = "property" if prop else "name"
    for tag in tags(text, "meta"):
        if attr(tag, field).lower() == key.lower():
            return attr(tag, "content")
    return ""


def has_meta(text: str, key: str, *, prop: bool = False) -> bool:
    return bool(meta_value(text, key, prop=prop))


def before_head(text: str, payload: str) -> str:
    if not payload:
        return text
    updated, count = re.subn(r"</head\s*>", payload + "</head>", text, count=1, flags=re.I)
    if count != 1:
        raise ValueError("head_close_missing")
    return updated


def page_keywords(page: Path, text: str, title: str) -> list[str]:
    rel = page.relative_to(SITE).as_posix()
    values: list[str] = []
    core = re.split(r"\s*[|—]\s*", title, maxsplit=1)[0].strip()
    if 2 <= len(core) <= 100:
        values.append(core)
    for match in re.finditer(r"<h[12]\b[^>]*>(.*?)</h[12]>", text, re.I | re.S):
        value = re.sub(r"^\s*\d+[.)-]?\s*", "", clean(match.group(1)))
        if 3 <= len(value) <= 90:
            values.append(value)
        if len(values) >= 7:
            break
    for prefix, group in SECTION_KEYWORDS:
        if rel.startswith(prefix):
            values.extend(group)
            break
    values.extend(("مصطلحات علم النفس", "الصحة النفسية", "علم النفس بالعربي"))
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = re.sub(r"\s+", " ", value).strip(" ،؛:.-")
        key = value.casefold()
        if not value or key in seen or len(value) > 100:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= 12 or len(", ".join(result)) >= 330:
            break
    return result


def ensure_metadata(text: str, page: Path, title: str, description: str, canonical: str) -> tuple[str, dict[str, int]]:
    image = meta_value(text, "og:image", prop=True) or DEFAULT_IMAGE
    article = bool(re.search(r'"@type"\s*:\s*"(?:Article|MedicalWebPage|DefinedTerm|TechArticle)"', text))
    og_type = meta_value(text, "og:type", prop=True) or ("article" if article else "website")
    required = (
        ("property", "og:title", title), ("property", "og:description", description),
        ("property", "og:url", canonical), ("property", "og:type", og_type),
        ("property", "og:image", image), ("property", "og:locale", "ar_AR"),
        ("name", "twitter:card", "summary_large_image"), ("name", "twitter:title", title),
        ("name", "twitter:description", description), ("name", "twitter:image", image),
    )
    additions: list[str] = []
    stats = {"og": 0, "twitter": 0, "keywords": 0, "article_tags": 0, "jsonld": 0, "robots_404": 0}
    for field, key, value in required:
        if not has_meta(text, key, prop=field == "property"):
            additions.append(f'<meta {field}="{key}" content="{html.escape(value, quote=True)}">')
            stats["twitter" if key.startswith("twitter:") else "og"] += 1
    keywords = page_keywords(page, text, title)
    if not has_meta(text, "keywords"):
        additions.append(f'<meta name="keywords" content="{html.escape(", ".join(keywords), quote=True)}">')
        stats["keywords"] = 1
    if article and not has_meta(text, "article:tag", prop=True):
        for value in keywords[:5]:
            additions.append(f'<meta property="article:tag" content="{html.escape(value, quote=True)}">')
            stats["article_tags"] += 1
    if not re.search(r'<script\b[^>]*type=(["\'])application/ld\+json\1', text, re.I):
        node = {
            "@context": "https://schema.org", "@type": "WebPage", "name": title,
            "description": description, "url": canonical, "inLanguage": "ar",
            "keywords": keywords, "isPartOf": {"@type": "WebSite", "name": BRAND, "url": BASE_URL},
        }
        additions.append('<script type="application/ld+json">' + json.dumps(node, ensure_ascii=False, separators=(",", ":")) + "</script>")
        stats["jsonld"] = 1
    rel = page.relative_to(SITE).as_posix()
    if rel == "404.html":
        robot_pattern = re.compile(r'<meta\b[^>]*name=(["\'])robots\1[^>]*>', re.I)
        replacement = '<meta name="robots" content="noindex,follow,max-image-preview:large">'
        if robot_pattern.search(text):
            text = robot_pattern.sub(replacement, text, count=1)
        else:
            additions.append(replacement)
        stats["robots_404"] = 1
    return before_head(text, "".join(additions)), stats


def protected_parts(text: str) -> list[str]:
    return re.split(r"(<(?:script|style)\b[^>]*>.*?</(?:script|style)>)", text, flags=re.I | re.S)


def normalize_headings(text: str) -> tuple[str, int]:
    parts = protected_parts(text)
    previous = 0
    changed = 0
    pattern = re.compile(r"<h([1-6])(\b[^>]*)>(.*?)</h\1>", re.I | re.S)
    for index in range(0, len(parts), 2):
        def replace(match: re.Match[str]) -> str:
            nonlocal previous, changed
            level = int(match.group(1))
            target = previous + 1 if previous and level > previous + 1 else level
            previous = target
            changed += int(target != level)
            return f"<h{target}{match.group(2)}>{match.group(3)}</h{target}>"
        parts[index] = pattern.sub(replace, parts[index])
    return "".join(parts), changed


def link_label(tag: str, body: str) -> str:
    for key in ("aria-label", "title", "data-label"):
        value = attr(tag, key)
        if value:
            return value
    image = re.search(r'<img\b[^>]*alt=(["\'])(.*?)\1', body, re.I | re.S)
    if image and html.unescape(image.group(2)).strip():
        return html.unescape(image.group(2)).strip()
    href = attr(tag, "href")
    parsed = urlparse(href)
    slug = unquote(parsed.path).rstrip("/").rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").strip()
    return f"فتح {slug}" if slug and slug not in {"index.html", "pterminology-site"} else "فتح الرابط"


def label_empty_links(text: str) -> tuple[str, int]:
    parts = protected_parts(text)
    count = 0
    pattern = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
    for index in range(0, len(parts), 2):
        def replace(match: re.Match[str]) -> str:
            nonlocal count
            attrs, body = match.group(1), match.group(2)
            if clean(body):
                return match.group(0)
            label = link_label(attrs, body)
            if not attr(attrs, "aria-label"):
                attrs = f' aria-label="{html.escape(label, quote=True)}"' + attrs
            count += 1
            return f'<a{attrs}>{body}<span class="visually-hidden-v215">{html.escape(label)}</span></a>'
        parts[index] = pattern.sub(replace, parts[index])
    updated = "".join(parts)
    if count and 'id="a11y-v215"' not in updated:
        updated = before_head(updated, f'<style id="a11y-v215">{HIDDEN_STYLE}</style>')
    return updated, count


def image_size(path: Path) -> tuple[int, int] | None:
    try:
        if path.suffix.lower() == ".svg":
            root = ET.parse(path).getroot()
            width = re.sub(r"[^0-9.]", "", root.attrib.get("width", ""))
            height = re.sub(r"[^0-9.]", "", root.attrib.get("height", ""))
            if width and height:
                return max(1, round(float(width))), max(1, round(float(height)))
            view = root.attrib.get("viewBox", "").replace(",", " ").split()
            if len(view) == 4:
                return max(1, round(float(view[2]))), max(1, round(float(view[3])))
        if path.suffix.lower() == ".png":
            data = path.read_bytes()[:24]
            if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
                return struct.unpack(">II", data[16:24])
    except Exception:
        return None
    return None


def local_asset(page: Path, source: str) -> Path | None:
    parsed = urlparse(html.unescape(source).strip())
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc != HOST or not parsed.path.startswith(BASE_PATH):
            return None
        relative = parsed.path[len(BASE_PATH):]
    elif parsed.scheme or source.startswith("data:") or parsed.path.startswith("/") and not parsed.path.startswith(BASE_PATH):
        return None
    elif parsed.path.startswith(BASE_PATH):
        relative = parsed.path[len(BASE_PATH):]
    else:
        relative = (page.parent.relative_to(SITE) / unquote(parsed.path)).as_posix()
    target = (SITE / unquote(relative).lstrip("/")).resolve()
    try:
        target.relative_to(SITE)
    except ValueError:
        return None
    return target if target.is_file() else None


def add_image_dimensions(text: str, page: Path) -> tuple[str, int]:
    count = 0
    pattern = re.compile(r"<img\b([^>]*)>", re.I)
    def replace(match: re.Match[str]) -> str:
        nonlocal count
        attrs = match.group(1)
        if re.search(r"\bwidth\s*=", attrs, re.I) and re.search(r"\bheight\s*=", attrs, re.I):
            return match.group(0)
        target = local_asset(page, attr(attrs, "src"))
        size = image_size(target) if target else None
        if not size:
            return match.group(0)
        count += 1
        return f'<img width="{size[0]}" height="{size[1]}"{attrs}>'
    return pattern.sub(replace, text), count


def visible_text(text: str) -> str:
    parser = VisibleText()
    parser.feed(text)
    return " ".join(parser.parts)


def threshold(rel: str) -> int:
    if rel == "index.html": return 350
    if rel.startswith("encyclopedia/concept-"): return 500
    if rel.startswith("tips/") and rel != "tips/index.html": return 500
    if rel.startswith("care-guides/") and rel != "care-guides/index.html": return 650
    if rel.startswith("special-needs/") and rel != "special-needs/index.html": return 750
    if rel.startswith("sectors/"): return 300 if rel.count("/") == 2 else 450
    if rel.startswith("library/"): return 350 if rel == "library/index.html" else 400
    if rel.startswith(("comparisons/", "guided-assessment/")): return 300
    return 150


def process(page: Path) -> tuple[dict[str, int], list[str], int, int]:
    text = page.read_text(encoding="utf-8")
    title = title_of(text)
    description = description_of(text, title)
    canonical = canonical_of(text, page)
    text, stats = ensure_metadata(text, page, title, description, canonical)
    text, stats["heading_repairs"] = normalize_headings(text)
    text, stats["empty_link_names"] = label_empty_links(text)
    text, stats["image_dimensions"] = add_image_dimensions(text, page)
    page.write_text(text, encoding="utf-8")
    plain = visible_text(text)
    words = len(re.findall(r"[\w\u0600-\u06ff]+", plain, re.UNICODE))
    tokens = [token for token in OPERATIONAL_TOKENS if token in plain]
    return stats, tokens, words, threshold(page.relative_to(SITE).as_posix())


def main() -> int:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site directory: {SITE}")
    keys = ("pages", "og", "twitter", "keywords", "article_tags", "jsonld", "robots_404", "heading_repairs", "empty_link_names", "image_dimensions")
    totals = {key: 0 for key in keys}
    operational: list[dict[str, object]] = []
    short: list[dict[str, object]] = []
    for page in sorted(SITE.rglob("*.html")):
        if page.name == VERIFY:
            continue
        totals["pages"] += 1
        stats, tokens, words, minimum = process(page)
        for key, value in stats.items():
            totals[key] += value
        rel = page.relative_to(SITE).as_posix()
        if tokens:
            operational.append({"page": rel, "tokens": tokens})
        if words < minimum:
            short.append({"page": rel, "words": words, "minimum_words": minimum, "gap": minimum - words})
    report = {
        "version": 215, "status": "passed", **totals,
        "operational_copy_pages": len(operational), "operational_copy_examples": operational[:100],
        "short_page_count": len(short),
        "short_pages": sorted(short, key=lambda item: (-int(item["gap"]), str(item["page"])))[:250],
        "content_expansion_required": bool(short),
        "keyword_policy": "topic-phrases-from-title-headings-and-taxonomy-no-keyword-stuffing",
        "external_review": "not-applicable-technical-seo-layer",
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "institutional-seo-v215.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
