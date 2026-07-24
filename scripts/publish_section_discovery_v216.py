#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
BLOCK_ID = "platform-directory-v216"
DIRECTORY_ROUTE = "sections/"
TECHNICAL_ROOTS = {
    "assets", "downloads", "fonts", "images", "media", "scripts", "styles",
    "css", "js", ".well-known", "node_modules",
}

SECTION_DEFINITIONS: OrderedDict[str, tuple[str, str, str]] = OrderedDict([
    ("start-here/", ("ابدأ من هنا", "مسارات موجهة لاختيار القسم أو الدليل أو الأداة الأنسب للحاجة الحالية.", "البداية")),
    ("encyclopedia/", ("الموسوعة النفسية العربية", "مفاهيم وتعريفات وفروق وعلامات ودعم عملي وروابط بين الموضوعات.", "المعرفة")),
    ("hubs/", ("المراكز الموضوعية", "صفحات تجمع المفاهيم والأدلة المتقاربة في مسارات موضوعية مترابطة.", "المعرفة")),
    ("comparisons/", ("مكتبة المقارنات النفسية", "مقارنات منظمة توضّح الفروق بين المفاهيم والحالات والمصطلحات المتشابهة.", "المعرفة")),
    ("library/", ("المكتبة الأكاديمية", "مصادر وأبحاث وقراءات منظمة في علم النفس والصحة النفسية والتقييم.", "المصادر")),
    ("guided-assessment/", ("الأسئلة الموجهة", "أسئلة تثقيفية تساعد على تنظيم الملاحظة والاستعداد لطلب المساعدة دون تشخيص آلي.", "الأدوات")),
    ("assessments/", ("المقاييس التثقيفية", "صفحات مقاييس استرشادية منشورة بحدود استخدام واضحة وتحذير من التشخيص الذاتي.", "الأدوات")),
    ("cognitive-tests/", ("المهام المعرفية التثقيفية", "مهام للانتباه والذاكرة والاستدلال ليست درجة ذكاء سريرية أو بديلًا عن التقييم.", "الأدوات")),
    ("assessment-lab/", ("مختبر المقاييس الاستكشافية", "مقاييس وأدوات متابعة واستكشاف مع تفسير وحدود مهنية واضحة.", "الأدوات")),
    ("cognitive-lab/", ("مختبر القدرات المعرفية", "مهام معرفية متدرجة للانتباه والذاكرة والوظائف التنفيذية والاستدلال.", "الأدوات")),
    ("care-guides/", ("أدلة التعامل العملي", "أدلة موسعة للأسرة ومقدم الخدمة والمدرسة حول التواصل والدعم والمتابعة.", "الدعم")),
    ("tips/", ("النصائح النفسية العملية", "خطوات يومية وجمل مساعدة وأخطاء شائعة ومؤشرات لطلب الدعم المتخصص.", "الدعم")),
    ("special-needs/", ("ذوو الاحتياجات الخاصة والتربية الدامجة", "مسارات للتعليم والتواصل والحواس والحركة والاستقلال والحماية ودعم الأسرة.", "الدعم")),
    ("sectors/", ("الأقسام المتخصصة", "بوابات للصحة النفسية للطفل والأسرة والعائلة والمرأة وفئات الاستخدام المختلفة.", "الدعم")),
    ("magazine/", ("المجلة والأبحاث", "قراءة منضبطة للدراسات ونتائجها وقيودها ومصادرها دون مبالغة.", "المصادر")),
    ("trust/", ("الثقة والمنهجية", "سياسة المصادر والمراجعة والتصحيح وحدود المحتوى والمسؤولية.", "الحوكمة")),
    ("partners/", ("الشركاء والشفافية", "سجل العلاقات والشراكات الموثقة وسياسة عدم الادعاء بعلاقات غير مثبتة.", "الحوكمة")),
    ("provider-assessment-demo/", ("منصة التقييم المؤسسية", "واجهة إدارة حالات وجلسات وسجلات وتقييمات ضمن حدود الخصوصية والحقوق.", "المؤسسات")),
    ("developers/", ("واجهة المطورين", "توثيق التكامل وواجهات القراءة وعقود استيراد الدورات المصرح بها.", "التكامل")),
    ("api/", ("واجهة API", "ملفات JSON وOpenAPI وعقود بيانات للربط الآمن والمصرح به.", "التكامل")),
])

FEATURED_ROUTES = (
    "comparisons/", "library/", "guided-assessment/", "hubs/",
    "assessments/", "cognitive-tests/",
)


class TextExtractor(HTMLParser):
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


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def title_of(text: str, fallback: str) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, re.I | re.S)
    if not match:
        return fallback
    title = clean(match.group(1))
    return re.split(r"\s*[|—]\s*", title, maxsplit=1)[0].strip() or fallback


def description_of(text: str, fallback: str) -> str:
    match = re.search(r'<meta\b[^>]*name=(["\'])description\1[^>]*content=(["\'])(.*?)\2', text, re.I | re.S)
    return clean(match.group(3)) if match and clean(match.group(3)) else fallback


def public_roots() -> list[str]:
    roots: list[str] = []
    for entry in sorted(SITE.iterdir(), key=lambda item: item.name.casefold()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in TECHNICAL_ROOTS:
            continue
        if (entry / "index.html").is_file():
            roots.append(entry.name + "/")
    return roots


def count_pages(route: str) -> int:
    return len(list((SITE / route).rglob("*.html")))


def section_record(route: str, homepage_before: str) -> dict[str, object]:
    path = SITE / route / "index.html"
    text = path.read_text(encoding="utf-8")
    predefined = SECTION_DEFINITIONS.get(route)
    if predefined:
        name, summary, category = predefined
    else:
        fallback = route.rstrip("/").replace("-", " ").replace("_", " ")
        name = title_of(text, fallback)
        summary = description_of(text, f"قسم منشور ضمن {BRAND}.")
        category = "أقسام أخرى"
    return {
        "route": route,
        "url": BASE_URL + route,
        "name": name,
        "summary": summary,
        "category": category,
        "page_count": count_pages(route),
        "linked_from_home_before": bool(re.search(rf'href=(["\'])/?(?:pterminology-site/)?{re.escape(route)}', homepage_before)),
        "featured_on_home": route in FEATURED_ROUTES,
    }


def section_cards(records: list[dict[str, object]], *, featured_only: bool) -> str:
    selected = [record for record in records if bool(record["featured_on_home"])] if featured_only else records
    cards = []
    for record in selected:
        cards.append(
            '<article class="directory-card-v216">'
            f'<p class="directory-category-v216">{html.escape(str(record["category"]))}</p>'
            f'<h3><a href="{html.escape(str(record["route"]), quote=True)}">{html.escape(str(record["name"]))}</a></h3>'
            f'<p>{html.escape(str(record["summary"]))}</p>'
            f'<span>{int(record["page_count"])} صفحة منشورة</span>'
            '</article>'
        )
    return "".join(cards)


def inject_homepage(records: list[dict[str, object]]) -> tuple[str, int]:
    path = SITE / "index.html"
    text = path.read_text(encoding="utf-8")
    text = re.sub(rf'<section\b[^>]*id=(["\']){BLOCK_ID}\1.*?</section>', "", text, flags=re.I | re.S)
    if 'href="sections/"' not in text:
        text, nav_count = re.subn(r"</nav>", '<a href="sections/">جميع الأقسام</a></nav>', text, count=1, flags=re.I)
        if not nav_count:
            raise SystemExit("Homepage primary navigation could not be extended")
    style = (
        '<style id="directory-style-v216">'
        '.directory-grid-v216{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}'
        '.directory-card-v216{background:#fff;border:1px solid #c7e6e2;border-radius:20px;padding:20px;box-shadow:0 12px 32px rgba(31,105,104,.09)}'
        '.directory-card-v216 h3{margin:.2rem 0}.directory-card-v216 p{color:#527275}.directory-card-v216 span,.directory-category-v216{font-weight:800;color:#7f3659}'
        '@media(max-width:900px){.directory-grid-v216{grid-template-columns:repeat(2,minmax(0,1fr))}}'
        '@media(max-width:620px){.directory-grid-v216{grid-template-columns:1fr}}'
        '</style>'
    )
    if 'id="directory-style-v216"' not in text:
        text = re.sub(r"</head>", style + "</head>", text, count=1, flags=re.I)
    block = (
        f'<section class="section" id="{BLOCK_ID}" aria-labelledby="directory-title-v216">'
        '<p class="eyebrow">أقسام منشورة قد لا تظهر في القوائم المختصرة</p>'
        '<h2 id="directory-title-v216">المقارنات والمكتبة والأدوات الإضافية</h2>'
        '<p class="section-intro">تضم المنصة أقسامًا مولدة أثناء البناء إلى جانب الأقسام الرئيسية. أُضيفت هنا روابط مباشرة لأهمها، مع دليل كامل يُحدّث تلقائيًا عند ظهور قسم جديد.</p>'
        f'<div class="directory-grid-v216">{section_cards(records, featured_only=True)}</div>'
        '<p><a class="button secondary" href="sections/">عرض جميع الأقسام والصفحات المنشورة</a></p>'
        '</section>'
    )
    updated, count = re.subn(r"</main>", block + "</main>", text, count=1, flags=re.I)
    if count != 1:
        raise SystemExit("Homepage main landmark could not be extended")
    path.write_text(updated, encoding="utf-8")
    return updated, len([record for record in records if record["featured_on_home"]])


def directory_page(records: list[dict[str, object]]) -> str:
    grouped: OrderedDict[str, list[dict[str, object]]] = OrderedDict()
    for record in records:
        grouped.setdefault(str(record["category"]), []).append(record)
    groups = []
    for category, items in grouped.items():
        groups.append(
            f'<section aria-labelledby="cat-{len(groups)}"><h2 id="cat-{len(groups)}">{html.escape(category)}</h2>'
            f'<div class="grid">{section_cards(items, featured_only=False)}</div></section>'
        )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "دليل جميع أقسام المنصة",
        "description": "جرد محدث تلقائيًا للأقسام والصفحات المنشورة في منصة الصحة النفسية وذوي الاحتياجات الخاصة.",
        "url": BASE_URL + DIRECTORY_ROUTE,
        "inLanguage": "ar",
        "hasPart": [{"@type": "CollectionPage", "name": item["name"], "url": item["url"]} for item in records],
    }
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>دليل جميع أقسام المنصة | {BRAND}</title><meta name="description" content="جرد محدث تلقائيًا للموسوعة والمقارنات والمكتبة والأدلة والمقاييس والمهام المعرفية وجميع الأقسام المنشورة."><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE_URL}{DIRECTORY_ROUTE}"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script><style>:root{{--ink:#143f44;--muted:#527275;--brand:#0b6b66;--line:#c7e6e2;--bg:#f7fffd}}*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.85;color:var(--ink);background:linear-gradient(145deg,#fff,var(--bg))}}a{{color:#076b65}}a:focus-visible{{outline:3px solid #168f88;outline-offset:4px}}.wrap{{width:min(1180px,92%);margin:auto}}header,footer{{padding:18px 0;border-color:var(--line);border-style:solid;border-width:0 0 1px}}footer{{border-width:1px 0 0;margin-top:40px}}main{{padding:50px 0}}h1{{font-size:clamp(2.2rem,6vw,4rem);line-height:1.2}}h2{{margin-top:2.4rem}}.lead{{font-size:1.15rem;color:var(--muted);max-width:900px}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}}.directory-card-v216{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:0 12px 32px rgba(31,105,104,.09)}}.directory-card-v216 h3{{margin:.2rem 0}}.directory-card-v216 p{{color:var(--muted)}}.directory-card-v216 span,.directory-category-v216{{font-weight:800;color:#7f3659}}@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:620px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><header><div class="wrap"><a href="../">{BRAND}</a></div></header><main><div class="wrap"><p><a href="../">الرئيسية</a> / جميع الأقسام</p><h1>دليل جميع أقسام المنصة</h1><p class="lead">هذه الصفحة تُبنى من محتوى النسخة المنشورة نفسها، لذلك تُظهر الأقسام المولدة مثل المقارنات والمكتبة والأسئلة الموجهة حتى إن لم تكن ملفاتها موجودة بصورة ثابتة في المستودع.</p>{''.join(groups)}</div></main><footer><div class="wrap">عدد الأقسام العامة: {len(records)} · عدد صفحات HTML داخلها: {sum(int(item['page_count']) for item in records)}</div></footer></body></html>'''


def update_sitemap() -> None:
    sitemap_name = "sitemap-sections-v216.xml"
    sitemap_path = SITE / sitemap_name
    sitemap_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{BASE_URL}{DIRECTORY_ROUTE}</loc></url>\n'
        '</urlset>\n',
        encoding="utf-8",
    )
    index = SITE / "sitemap.xml"
    if not index.is_file():
        raise SystemExit("Sitemap index is missing")
    tree = ET.parse(index)
    root = tree.getroot()
    namespace = root.tag.split("}", 1)[0].strip("{") if "}" in root.tag else ""
    tag = lambda name: f"{{{namespace}}}{name}" if namespace else name
    target = BASE_URL + sitemap_name
    matches = []
    for child in list(root):
        loc = child.find("{*}loc")
        if loc is not None and (loc.text or "").strip() == target:
            matches.append(child)
    for child in matches:
        root.remove(child)
    sitemap = ET.SubElement(root, tag("sitemap"))
    ET.SubElement(sitemap, tag("loc")).text = target
    if namespace:
        ET.register_namespace("", namespace)
    tree.write(index, encoding="utf-8", xml_declaration=True)


def update_openapi() -> None:
    path = SITE / "api" / "v1" / "openapi.json"
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    existing = next(iter(payload.get("paths", {})), "")
    prefix = "/pterminology-site" if existing.startswith("/pterminology-site/") else ""
    route = prefix + "/api/v1/sections.json"
    payload.setdefault("paths", {})[route] = {
        "get": {
            "summary": "جرد أقسام المنصة المنشورة",
            "operationId": "getPublishedSections",
            "responses": {"200": {"description": "قائمة الأقسام العامة وعدد الصفحات والروابط"}},
        }
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    homepage_path = SITE / "index.html"
    if not homepage_path.is_file():
        raise SystemExit("Homepage is missing")
    homepage_before = homepage_path.read_text(encoding="utf-8")
    roots = public_roots()
    records = [section_record(route, homepage_before) for route in roots]
    records.sort(key=lambda item: (list(SECTION_DEFINITIONS).index(str(item["route"])) if item["route"] in SECTION_DEFINITIONS else 10_000, str(item["name"])))
    required_routes = {"comparisons/", "library/"}
    missing = sorted(required_routes - {str(item["route"]) for item in records})
    if missing:
        raise SystemExit(f"Published generated sections disappeared: {missing}")
    directory = SITE / DIRECTORY_ROUTE
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.html").write_text(directory_page(records), encoding="utf-8")
    homepage_after, featured_count = inject_homepage(records)
    update_sitemap()
    api_dir = SITE / "api" / "v1"
    api_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "api_version": "v1",
        "release": 216,
        "generated_from_published_build": True,
        "section_count": len(records),
        "html_page_count": sum(int(item["page_count"]) for item in records),
        "homepage_featured_routes": list(FEATURED_ROUTES),
        "unlinked_from_home_before": [item["route"] for item in records if not item["linked_from_home_before"]],
        "directory_route": DIRECTORY_ROUTE,
        "items": records,
    }
    (api_dir / "sections.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_openapi()
    direct_after = {route: bool(re.search(rf'href=(["\'])/?(?:pterminology-site/)?{re.escape(route)}', homepage_after)) for route in FEATURED_ROUTES}
    if not all(direct_after.values()):
        raise SystemExit(f"Featured generated sections are still hidden from homepage: {direct_after}")
    report = {
        "version": 216,
        "status": "passed",
        "sections": len(records),
        "pages": payload["html_page_count"],
        "featured_on_home": featured_count,
        "comparisons_linked": direct_after["comparisons/"],
        "library_linked": direct_after["library/"],
        "directory_created": True,
        "sections_api_created": True,
        "sitemap_registered": True,
    }
    (SITE / "api" / "section-discovery-v216.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
