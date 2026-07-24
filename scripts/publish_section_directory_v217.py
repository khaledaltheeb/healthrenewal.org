#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
DIRECTORY_ROUTE = "sections/"
BLOCK_ID = "institutional-section-directory-v217"
TECHNICAL_ROOTS = {
    ".well-known", "assets", "css", "downloads", "fonts", "images", "js",
    "media", "node_modules", "scripts", "sections", "styles",
}
BANNED_PUBLIC_COPY = (
    "مولدة أثناء البناء", "مولّد أثناء البناء", "لا تظهر في القوائم",
    "خطة العمل", "ما تم إنجازه", "سيتم إنجازه", "قيد التطوير",
)

SECTION_DEFINITIONS: OrderedDict[str, tuple[str, str, str]] = OrderedDict([
    ("start-here/", ("ابدأ من هنا", "مسارات موجهة تساعدك على اختيار القسم أو الدليل أو الأداة الأنسب.", "البداية")),
    ("encyclopedia/", ("الموسوعة النفسية العربية", "مفاهيم وفروق وعلامات وخيارات دعم وروابط مترابطة بين الموضوعات.", "المعرفة")),
    ("hubs/", ("المراكز الموضوعية", "بوابات تجمع الموضوعات والأدلة المتقاربة في مسارات واضحة.", "المعرفة")),
    ("comparisons/", ("مكتبة المقارنات النفسية", "مقارنات منظمة توضّح الفروق بين المفاهيم والحالات المتشابهة.", "المعرفة")),
    ("library/", ("المكتبة الأكاديمية", "مصادر ودراسات وقراءات منظمة في الصحة النفسية والتقييم والدعم.", "المصادر")),
    ("magazine/", ("المجلة والأبحاث", "ملخصات منضبطة للدراسات ونتائجها وقيودها ومصادرها.", "المصادر")),
    ("guided-assessment/", ("الأسئلة الموجهة", "أسئلة تثقيفية لتنظيم الملاحظة والاستعداد لطلب المساعدة دون تشخيص آلي.", "الأدوات")),
    ("assessments/", ("المقاييس التثقيفية", "مقاييس استرشادية منشورة بحدود استخدام واضحة.", "الأدوات")),
    ("assessment-lab/", ("مختبر المقاييس الاستكشافية", "أدوات استكشاف ومتابعة مع تفسير وحدود مهنية واضحة.", "الأدوات")),
    ("cognitive-tests/", ("المهام المعرفية التثقيفية", "مهام للانتباه والذاكرة والاستدلال لا تمثل تشخيصًا أو درجة ذكاء سريرية.", "الأدوات")),
    ("cognitive-lab/", ("مختبر القدرات المعرفية", "مهام متدرجة للانتباه والذاكرة والوظائف التنفيذية والاستدلال.", "الأدوات")),
    ("care-guides/", ("أدلة التعامل العملي", "أدلة موسعة للأسرة والمدرسة ومقدم الخدمة حول التواصل والدعم والمتابعة.", "الدعم")),
    ("tips/", ("النصائح النفسية العملية", "خطوات يومية وأخطاء شائعة ومؤشرات لطلب دعم متخصص.", "الدعم")),
    ("special-needs/", ("ذوو الاحتياجات الخاصة والتربية الدامجة", "أدلة للتعليم والتواصل والحواس والحركة والاستقلال والحماية ودعم الأسرة.", "الدعم")),
    ("sectors/", ("الأقسام المتخصصة", "بوابات للصحة النفسية للطفل والأسرة والمرأة وفئات الاستخدام المختلفة.", "الدعم")),
    ("provider-assessment-demo/", ("منصة التقييم المؤسسية", "إدارة الحالات والجلسات والسجلات والتقييمات ضمن حدود الخصوصية والحقوق.", "المؤسسات")),
    ("trust/", ("الثقة والمنهجية", "سياسة المصادر والمراجعة والتصحيح وحدود المحتوى والمسؤولية.", "الحوكمة")),
    ("partners/", ("الشركاء والشفافية", "سجل العلاقات الموثقة وسياسة عدم ادعاء شراكات غير مثبتة.", "الحوكمة")),
    ("developers/", ("واجهة المطورين", "توثيق التكامل وعقود البيانات والاستيراد المصرح به.", "التكامل")),
    ("api/", ("واجهة API", "ملفات JSON وOpenAPI وعقود بيانات للربط الآمن والمصرح به.", "التكامل")),
    ("en/", ("English homepage", "English-language entry point to the platform's principal resources.", "اللغات")),
    ("es/", ("Página en español", "Punto de entrada en español a los recursos principales de la plataforma.", "اللغات")),
])
FEATURED_ROUTES = (
    "encyclopedia/", "special-needs/", "care-guides/", "comparisons/",
    "library/", "assessment-lab/", "cognitive-lab/", "magazine/",
)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def title_of(text: str, fallback: str) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, re.I | re.S)
    title = clean(match.group(1)) if match else fallback
    return re.split(r"\s*[|—]\s*", title, maxsplit=1)[0].strip() or fallback


def description_of(text: str, fallback: str) -> str:
    match = re.search(
        r'<meta\b[^>]*name=(["\'])description\1[^>]*content=(["\'])(.*?)\2',
        text, re.I | re.S,
    )
    description = clean(match.group(3)) if match else ""
    return description or fallback


def public_roots() -> list[str]:
    roots: list[str] = []
    for entry in sorted(SITE.iterdir(), key=lambda item: item.name.casefold()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in TECHNICAL_ROOTS:
            continue
        if (entry / "index.html").is_file():
            roots.append(entry.name + "/")
    return roots


def section_record(route: str, homepage: str) -> dict[str, object]:
    path = SITE / route / "index.html"
    source = path.read_text(encoding="utf-8")
    predefined = SECTION_DEFINITIONS.get(route)
    if predefined:
        name, summary, category = predefined
    else:
        fallback = route.rstrip("/").replace("-", " ").replace("_", " ")
        name = title_of(source, fallback)
        summary = description_of(source, f"قسم منشور ضمن {BRAND}.")
        category = "أقسام أخرى"
    linked = bool(re.search(
        rf'href=(["\'])/?(?:pterminology-site/)?{re.escape(route)}', homepage, re.I
    ))
    return {
        "route": route,
        "url": BASE_URL + route,
        "name": name,
        "summary": summary,
        "category": category,
        "page_count": len(list((SITE / route).rglob("*.html"))),
        "linked_from_home": linked,
        "featured": route in FEATURED_ROUTES,
    }


def cards(records: list[dict[str, object]], *, absolute: bool = False) -> str:
    output: list[str] = []
    for record in records:
        href = str(record["url"] if absolute else record["route"])
        output.append(
            '<article class="section-card-v217">'
            f'<p class="section-category-v217">{html.escape(str(record["category"]))}</p>'
            f'<h3><a href="{html.escape(href, quote=True)}">{html.escape(str(record["name"]))}</a></h3>'
            f'<p>{html.escape(str(record["summary"]))}</p>'
            f'<span>{int(record["page_count"])} صفحة</span>'
            '</article>'
        )
    return "".join(output)


def homepage_block(records: list[dict[str, object]]) -> str:
    featured = [record for record in records if record["featured"]]
    return (
        f'<section class="section" id="{BLOCK_ID}" aria-labelledby="section-directory-title-v217">'
        '<p class="eyebrow">دليل الوصول</p>'
        '<h2 id="section-directory-title-v217">استكشف جميع أقسام المنصة</h2>'
        '<p class="section-intro">انتقل مباشرة إلى الموسوعة والأدلة والمقارنات والمكتبة والمقاييس والمهام المعرفية والموارد المؤسسية.</p>'
        f'<div class="section-grid-v217">{cards(featured)}</div>'
        '<p><a class="button secondary" href="sections/">عرض دليل الأقسام الكامل</a></p>'
        '</section>'
    )


def inject_homepage(records: list[dict[str, object]]) -> tuple[str, int]:
    path = SITE / "index.html"
    source = path.read_text(encoding="utf-8")
    source = re.sub(
        rf'<section\b[^>]*id=(["\']){BLOCK_ID}\1.*?</section>',
        "", source, flags=re.I | re.S,
    )
    if 'href="sections/"' not in source:
        source, count = re.subn(
            r"</nav>", '<a href="sections/">جميع الأقسام</a></nav>',
            source, count=1, flags=re.I,
        )
        if count != 1:
            raise SystemExit("Primary navigation could not be extended")
    style = (
        '<style id="section-directory-style-v217">'
        '.section-grid-v217{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px}'
        '.section-card-v217{background:#fff;border:1px solid #c6e3df;border-radius:20px;padding:20px;box-shadow:0 12px 32px rgba(31,105,104,.09)}'
        '.section-card-v217 h3{margin:.2rem 0}.section-card-v217 p{color:#526f73}'
        '.section-card-v217 span,.section-category-v217{font-weight:800;color:#7f3659}'
        '@media(max-width:1050px){.section-grid-v217{grid-template-columns:repeat(2,minmax(0,1fr))}}'
        '@media(max-width:620px){.section-grid-v217{grid-template-columns:1fr}}'
        '</style>'
    )
    if 'id="section-directory-style-v217"' not in source:
        source = re.sub(r"</head>", style + "</head>", source, count=1, flags=re.I)
    source, count = re.subn(r"</main>", homepage_block(records) + "</main>", source, count=1, flags=re.I)
    if count != 1:
        raise SystemExit("Homepage main landmark could not be extended")
    path.write_text(source, encoding="utf-8")
    return source, sum(1 for record in records if record["featured"])


def directory_page(records: list[dict[str, object]]) -> str:
    grouped: OrderedDict[str, list[dict[str, object]]] = OrderedDict()
    for record in records:
        grouped.setdefault(str(record["category"]), []).append(record)
    groups: list[str] = []
    for index, (category, items) in enumerate(grouped.items()):
        groups.append(
            f'<section aria-labelledby="section-group-{index}"><h2 id="section-group-{index}">{html.escape(category)}</h2>'
            f'<div class="grid">{cards(items, absolute=True)}</div></section>'
        )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "دليل أقسام منصة الصحة النفسية وذوي الاحتياجات الخاصة",
        "description": "دليل منظم للوصول إلى الموسوعة والأدلة والأدوات والمصادر والأقسام المتخصصة.",
        "url": BASE_URL + DIRECTORY_ROUTE,
        "inLanguage": "ar",
        "hasPart": [
            {"@type": "CollectionPage", "name": item["name"], "url": item["url"]}
            for item in records
        ],
    }
    schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>دليل جميع أقسام المنصة | {BRAND}</title><meta name="description" content="دليل منظم للموسوعة والأدلة والمقارنات والمكتبة والمقاييس والمهام المعرفية وجميع أقسام المنصة."><meta name="keywords" content="أقسام الصحة النفسية, موسوعة علم النفس, أدلة ذوي الاحتياجات الخاصة, المقاييس النفسية, المكتبة النفسية, أدلة الأسرة"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#075f5b"><link rel="canonical" href="{BASE_URL}{DIRECTORY_ROUTE}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><link rel="icon" href="{BASE_PATH}assets/brand/logo-mark.svg" type="image/svg+xml"><meta property="og:type" content="website"><meta property="og:site_name" content="{BRAND}"><meta property="og:url" content="{BASE_URL}{DIRECTORY_ROUTE}"><meta property="og:title" content="دليل جميع أقسام المنصة"><meta property="og:description" content="وصول مباشر إلى أقسام المعرفة والدعم والأدوات والمصادر والتكامل."><meta property="og:image" content="{BASE_URL}assets/brand/social-card.svg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="دليل جميع أقسام المنصة"><meta name="twitter:description" content="وصول مباشر إلى أقسام المعرفة والدعم والأدوات والمصادر والتكامل."><meta name="twitter:image" content="{BASE_URL}assets/brand/social-card.svg"><script type="application/ld+json">{schema_json}</script><style>:root{{--ink:#103e43;--muted:#526f73;--brand:#075f5b;--line:#c6e3df;--bg:#effaf8}}*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.85;color:var(--ink);background:linear-gradient(145deg,#fff,var(--bg))}}a{{color:#066b65}}a:focus-visible{{outline:3px solid #0a8b82;outline-offset:4px}}.wrap{{width:min(1200px,92%);margin:auto}}header,footer{{padding:18px 0;background:#fff;border-color:var(--line);border-style:solid;border-width:0 0 1px}}footer{{border-width:1px 0 0;margin-top:40px}}main{{padding:50px 0}}h1{{font-size:clamp(2.2rem,6vw,4rem);line-height:1.2}}h2{{margin-top:2.5rem}}.lead{{font-size:1.15rem;color:var(--muted);max-width:900px}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}}.section-card-v217{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:0 12px 32px rgba(31,105,104,.09)}}.section-card-v217 h3{{margin:.2rem 0}}.section-card-v217 p{{color:var(--muted)}}.section-card-v217 span,.section-category-v217{{font-weight:800;color:#7f3659}}@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:620px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><header><div class="wrap"><a href="../">{BRAND}</a></div></header><main><div class="wrap"><p><a href="../">الرئيسية</a> / دليل الأقسام</p><h1>دليل جميع أقسام المنصة</h1><p class="lead">اختر المسار الأقرب إلى حاجتك: المعرفة، الأدوات، الدعم العملي، المصادر، الحوكمة، أو التكامل المؤسسي.</p>{''.join(groups)}</div></main><footer><div class="wrap">{len(records)} قسمًا عامًا · {sum(int(item['page_count']) for item in records)} صفحة داخل الأقسام</div></footer></body></html>'''


def update_sitemap() -> None:
    child_name = "sitemap-sections-v217.xml"
    (SITE / child_name).write_text(
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
    target = BASE_URL + child_name
    if root.tag.endswith("sitemapindex"):
        for child in list(root):
            loc = child.find("{*}loc")
            if loc is not None and (loc.text or "").strip() == target:
                root.remove(child)
        sitemap = ET.SubElement(root, tag("sitemap"))
        ET.SubElement(sitemap, tag("loc")).text = target
    elif root.tag.endswith("urlset"):
        existing = {(node.text or "").strip() for node in root.findall("{*}url/{*}loc")}
        if BASE_URL + DIRECTORY_ROUTE not in existing:
            url = ET.SubElement(root, tag("url"))
            ET.SubElement(url, tag("loc")).text = BASE_URL + DIRECTORY_ROUTE
    else:
        raise SystemExit("Unsupported sitemap root")
    if namespace:
        ET.register_namespace("", namespace)
    tree.write(index, encoding="utf-8", xml_declaration=True)


def update_api(records: list[dict[str, object]]) -> None:
    api_dir = SITE / "api" / "v1"
    api_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "api_version": "v1",
        "release": 217,
        "section_count": len(records),
        "html_page_count": sum(int(item["page_count"]) for item in records),
        "directory_url": BASE_URL + DIRECTORY_ROUTE,
        "items": records,
    }
    (api_dir / "sections.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    openapi_path = api_dir / "openapi.json"
    if openapi_path.is_file():
        openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
        existing = next(iter(openapi.get("paths", {})), "")
        prefix = "/pterminology-site" if existing.startswith("/pterminology-site/") else ""
        openapi.setdefault("paths", {})[prefix + "/api/v1/sections.json"] = {
            "get": {
                "summary": "قائمة أقسام المنصة العامة",
                "operationId": "getPlatformSections",
                "responses": {"200": {"description": "الأقسام وروابطها وعدد الصفحات"}},
            }
        }
        openapi_path.write_text(json.dumps(openapi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    platform_path = api_dir / "platform.json"
    if platform_path.is_file():
        platform = json.loads(platform_path.read_text(encoding="utf-8"))
        resources = platform.setdefault("resources", [])
        route = BASE_URL + "api/v1/sections.json"
        if isinstance(resources, list) and not any(
            (isinstance(item, dict) and (item.get("url") == route or item.get("href") == route))
            or item == route for item in resources
        ):
            resources.append({"name": "دليل الأقسام", "url": route})
        platform_path.write_text(json.dumps(platform, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    homepage_path = SITE / "index.html"
    if not homepage_path.is_file():
        raise SystemExit("Homepage is missing")
    homepage_before = homepage_path.read_text(encoding="utf-8")
    roots = public_roots()
    records = [section_record(route, homepage_before) for route in roots]
    order = {route: index for index, route in enumerate(SECTION_DEFINITIONS)}
    records.sort(key=lambda item: (order.get(str(item["route"]), 10_000), str(item["name"])))
    required = {"encyclopedia/", "special-needs/", "care-guides/", "api/"}
    missing = sorted(required - {str(item["route"]) for item in records})
    if missing:
        raise SystemExit(f"Required public sections disappeared: {missing}")
    directory = SITE / DIRECTORY_ROUTE
    directory.mkdir(parents=True, exist_ok=True)
    page_source = directory_page(records)
    if any(phrase in page_source for phrase in BANNED_PUBLIC_COPY):
        raise SystemExit("Operational copy leaked into the public directory")
    (directory / "index.html").write_text(page_source, encoding="utf-8")
    homepage_after, featured_count = inject_homepage(records)
    if any(phrase in homepage_after for phrase in BANNED_PUBLIC_COPY):
        raise SystemExit("Operational copy leaked into the homepage")
    update_sitemap()
    update_api(records)
    featured_status = {
        route: bool(re.search(rf'href=(["\'])/?(?:pterminology-site/)?{re.escape(route)}', homepage_after, re.I))
        for route in FEATURED_ROUTES
    }
    if not all(featured_status.values()):
        raise SystemExit(f"Featured sections are not directly linked: {featured_status}")
    report = {
        "version": 217,
        "status": "passed",
        "section_count": len(records),
        "html_page_count": sum(int(item["page_count"]) for item in records),
        "featured_on_home": featured_count,
        "directory_created": True,
        "sections_api_created": True,
        "sitemap_registered": True,
        "operational_copy_absent": True,
        "unlinked_from_home_before": [item["route"] for item in records if not item["linked_from_home"]],
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "section-directory-v217.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
