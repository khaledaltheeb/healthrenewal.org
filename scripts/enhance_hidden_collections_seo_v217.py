#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
NAV_ID = "hidden-collection-links-v217"
BREADCRUMB_MARKER = "data-hidden-collection-breadcrumb-v217"
BANNED_PUBLIC_COPY = (
    "مولدة أثناء البناء", "مولّد أثناء البناء", "لا تظهر في القوائم",
    "خطة العمل", "ما تم إنجازه", "سيتم إنجازه", "قيد التطوير",
    "قيد الإعداد", "قيد التوسع", "لا نشر قبل البوابات",
)

COLLECTIONS: OrderedDict[str, dict[str, object]] = OrderedDict([
    ("comparisons", {
        "name": "مكتبة المقارنات النفسية",
        "keywords": ["مقارنات نفسية", "الفرق بين الاضطرابات النفسية", "الفروق بين الحالات النفسية", "التشخيص التفريقي التثقيفي"],
        "related": [("encyclopedia/", "الموسوعة النفسية"), ("library/", "المكتبة الأكاديمية"), ("guided-assessment/", "الأسئلة الموجهة")],
    }),
    ("library", {
        "name": "المكتبة الأكاديمية",
        "keywords": ["المكتبة النفسية", "المكتبة الأكاديمية", "مصادر علم النفس", "دراسات الصحة النفسية"],
        "related": [("magazine/", "المجلة والأبحاث"), ("encyclopedia/", "الموسوعة النفسية"), ("comparisons/", "المقارنات")],
    }),
    ("guided-assessment", {
        "name": "الأسئلة الموجهة للاستكشاف",
        "keywords": ["أسئلة التقييم النفسي", "الاستكشاف النفسي", "تنظيم الملاحظة", "الاستعداد للتقييم"],
        "related": [("assessment-lab/", "مختبر المقاييس"), ("care-guides/", "أدلة التعامل"), ("comparisons/", "المقارنات")],
    }),
    ("hubs", {
        "name": "المراكز الموضوعية",
        "keywords": ["مراكز موضوعية نفسية", "موضوعات علم النفس", "روابط الصحة النفسية", "مسارات المعرفة النفسية"],
        "related": [("encyclopedia/", "الموسوعة النفسية"), ("care-guides/", "أدلة التعامل"), ("sections/", "جميع الأقسام")],
    }),
    ("assessments", {
        "name": "المقاييس التثقيفية",
        "keywords": ["المقاييس النفسية", "الاختبارات النفسية", "التقييم النفسي", "الفحص النفسي التثقيفي"],
        "related": [("assessment-lab/", "مختبر المقاييس"), ("guided-assessment/", "الأسئلة الموجهة"), ("trust/", "الثقة والمنهجية")],
    }),
    ("cognitive-tests", {
        "name": "المهام المعرفية التثقيفية",
        "keywords": ["الاختبارات المعرفية", "القدرات المعرفية", "اختبارات الانتباه والذاكرة", "الاستدلال المعرفي"],
        "related": [("cognitive-lab/", "مختبر القدرات"), ("assessment-lab/", "مختبر المقاييس"), ("trust/", "الثقة والمنهجية")],
    }),
    ("sections", {
        "name": "دليل جميع أقسام المنصة",
        "keywords": ["أقسام الصحة النفسية", "دليل منصة الصحة النفسية", "مكتبة علم النفس", "موارد ذوي الاحتياجات الخاصة"],
        "related": [("encyclopedia/", "الموسوعة النفسية"), ("special-needs/", "ذوو الاحتياجات الخاصة"), ("library/", "المكتبة الأكاديمية")],
    }),
])

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean(value: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", value))).strip()


def extract(source: str, pattern: str, fallback: str = "") -> str:
    match = re.search(pattern, source, re.I | re.S)
    return clean(match.group(1)) if match else fallback


def canonical_for(page: Path) -> str:
    relative = page.relative_to(SITE).as_posix()
    if relative == "index.html":
        route = ""
    elif relative.endswith("/index.html"):
        route = relative[:-len("index.html")]
    else:
        route = relative
    return BASE_URL + quote(route, safe="/-._~")


def replace_meta(source: str, name: str, content: str) -> str:
    pattern = rf'<meta\b[^>]*name=(["\']){re.escape(name)}\1[^>]*>'
    replacement = f'<meta name="{name}" content="{html.escape(content, quote=True)}">'
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.I | re.S)
    if count:
        return updated
    return re.sub(r"</head>", replacement + "</head>", source, count=1, flags=re.I)


def ensure_head_link(source: str, markup: str, identity: str) -> str:
    if identity in source:
        return source
    return re.sub(r"</head>", markup + "</head>", source, count=1, flags=re.I)


def keyword_list(source: str, config: dict[str, object], topic: str) -> list[str]:
    match = re.search(r'<meta\b[^>]*name=(["\'])keywords\1[^>]*content=(["\'])(.*?)\2', source, re.I | re.S)
    existing = [item.strip() for item in match.group(3).replace("،", ",").split(",") if item.strip()] if match else []
    candidates = [topic, *list(config["keywords"]), "الصحة النفسية", "علم النفس", "مصطلحات علم النفس"]
    result: list[str] = []
    for value in [*existing, *candidates]:
        value = SPACE_RE.sub(" ", value).strip(" ,،")
        if not value or value in result or len(value) > 100:
            continue
        if len(", ".join([*result, value])) > 470:
            break
        result.append(value)
        if len(result) >= 15:
            break
    return result


def related_navigation(root: str, config: dict[str, object]) -> str:
    links = [(root + "/", str(config["name"])), *list(config["related"]), ("sections/", "جميع الأقسام")]
    unique: list[tuple[str, str]] = []
    for route, label in links:
        if route not in {item[0] for item in unique}:
            unique.append((route, label))
    anchors = "".join(
        f'<a href="{BASE_PATH}{html.escape(route, quote=True)}">{html.escape(label)}</a>'
        for route, label in unique
    )
    return (
        f'<nav id="{NAV_ID}" class="related-platform-sections-v217" aria-label="أقسام مرتبطة">'
        '<strong>استكشف أيضًا:</strong>' + anchors + '</nav>'
    )


def breadcrumb_json(page: Path, root: str, config: dict[str, object], topic: str) -> str:
    canonical = canonical_for(page)
    section_url = BASE_URL + root + "/"
    items = [
        {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE_URL},
        {"@type": "ListItem", "position": 2, "name": config["name"], "item": section_url},
    ]
    if canonical != section_url:
        items.append({"@type": "ListItem", "position": 3, "name": topic, "item": canonical})
    payload = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}
    return (
        f'<script type="application/ld+json" {BREADCRUMB_MARKER}>'
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        + "</script>"
    )


def enhance_page(page: Path, root: str, config: dict[str, object]) -> bool:
    source = page.read_text(encoding="utf-8")
    original = source
    topic = extract(source, r"<h1\b[^>]*>(.*?)</h1>") or extract(source, r"<title\b[^>]*>(.*?)</title>") or str(config["name"])
    keywords = keyword_list(source, config, topic)
    source = replace_meta(source, "keywords", ", ".join(keywords))
    source = replace_meta(source, "subject", f'{config["name"]}: {topic}')
    source = replace_meta(source, "audience", "الأفراد والأسر والمعلمون والمرشدون والمختصون ومقدمو الخدمات")
    source = ensure_head_link(
        source,
        f'<link rel="up" href="{BASE_URL}{root}/">',
        f'rel="up" href="{BASE_URL}{root}/"',
    )
    source = ensure_head_link(
        source,
        f'<link rel="alternate" type="application/json" title="دليل أقسام المنصة" href="{BASE_URL}api/v1/sections.json">',
        'title="دليل أقسام المنصة"',
    )
    source = re.sub(
        rf'<nav\b[^>]*id=(["\']){NAV_ID}\1.*?</nav>',
        "",
        source,
        flags=re.I | re.S,
    )
    navigation = related_navigation(root, config)
    source, count = re.subn(r"</main>", navigation + "</main>", source, count=1, flags=re.I)
    if count != 1:
        raise SystemExit(f"Main landmark missing in {page.relative_to(SITE)}")
    source = re.sub(
        rf'<script\b[^>]*{BREADCRUMB_MARKER}[^>]*>.*?</script>',
        "",
        source,
        flags=re.I | re.S,
    )
    source = re.sub(r"</head>", breadcrumb_json(page, root, config, topic) + "</head>", source, count=1, flags=re.I)
    if any(phrase in source for phrase in BANNED_PUBLIC_COPY):
        raise SystemExit(f"Operational copy leaked into {page.relative_to(SITE)}")
    if source.count(f'id="{NAV_ID}"') != 1 or source.count(BREADCRUMB_MARKER) != 1:
        raise SystemExit(f"SEO interlink contract duplicated in {page.relative_to(SITE)}")
    if len(keywords) < 7:
        raise SystemExit(f"Keyword coverage too narrow in {page.relative_to(SITE)}: {keywords}")
    if source != original:
        page.write_text(source, encoding="utf-8")
        return True
    return False


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing generated site: {SITE}")
    counts: dict[str, int] = {}
    changed = 0
    total = 0
    missing: list[str] = []
    for root, config in COLLECTIONS.items():
        directory = SITE / root
        if not directory.is_dir() or not (directory / "index.html").is_file():
            missing.append(root)
            continue
        pages = sorted(directory.rglob("*.html"))
        counts[root] = len(pages)
        for page in pages:
            changed += int(enhance_page(page, root, config))
            total += 1
    if missing:
        raise SystemExit(f"Required hidden/public collections are missing: {missing}")
    report = {
        "version": 217,
        "status": "passed",
        "collections": len(COLLECTIONS),
        "pages_scanned": total,
        "pages_changed": changed,
        "page_counts": counts,
        "keywords_specialized": True,
        "breadcrumb_schema": True,
        "related_navigation": True,
        "sections_api_linked": True,
        "operational_copy_absent": True,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "hidden-collections-seo-v217.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
