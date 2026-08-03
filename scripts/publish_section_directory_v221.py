#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Any

BASE = "https://healthrenewal.org/"
BRAND = "منصة روافد"
VERSION = 221
START = "<!-- section-directory-v221:start -->"
END = "<!-- section-directory-v221:end -->"
TECHNICAL = {
    ".well-known", "assets", "css", "downloads", "fonts", "images", "js",
    "media", "node_modules", "scripts", "sections", "styles", "coverage",
    "reports", "tmp",
}
BANNED = (
    "مولدة أثناء البناء", "مولّد أثناء البناء", "لا تظهر في القوائم",
    "خطة العمل", "ما تم إنجازه", "سيتم إنجازه", "قيد التطوير",
    "built-not-published", "needs-external-review", "publication_block",
)
DEFINITIONS: OrderedDict[str, tuple[str, str, str]] = OrderedDict([
    ("start-here/", ("ابدأ من هنا", "مسارات موجهة لاختيار القسم أو الدليل أو الأداة الأقرب إلى حاجتك.", "البداية")),
    ("encyclopedia/", ("الموسوعة النفسية العربية", "مفاهيم وفروق وعلامات وخيارات دعم وروابط مترابطة.", "المعرفة")),
    ("terms/", ("المعجم النفسي", "مصطلحات نفسية عربية وإنجليزية منظمة للبحث والفهم.", "المعرفة")),
    ("hubs/", ("المراكز الموضوعية", "بوابات تجمع الموضوعات والأدلة المتقاربة في مسارات واضحة.", "المعرفة")),
    ("comparisons/", ("مكتبة المقارنات النفسية", "مقارنات منظمة توضّح الفروق بين المفاهيم والحالات المتشابهة.", "المعرفة")),
    ("library/", ("المكتبة الأكاديمية", "مصادر ودراسات وقراءات منظمة في الصحة النفسية والتقييم والدعم.", "المصادر")),
    ("magazine/", ("المجلة والأبحاث", "ملخصات منضبطة للدراسات ونتائجها وقيودها ومصادرها.", "المصادر")),
    ("guided-assessment/", ("الأسئلة الموجهة", "أسئلة تثقيفية لتنظيم الملاحظة دون تشخيص آلي.", "الأدوات")),
    ("assessments/", ("المقاييس التثقيفية", "مقاييس استرشادية منشورة بحدود استخدام واضحة.", "الأدوات")),
    ("assessment-lab/", ("مختبر المقاييس الاستكشافية", "أدوات استكشاف ومتابعة مع تفسير وحدود مهنية.", "الأدوات")),
    ("cognitive-tests/", ("المهام المعرفية التثقيفية", "مهام للانتباه والذاكرة والاستدلال غير التشخيصية.", "الأدوات")),
    ("cognitive-lab/", ("مختبر القدرات المعرفية", "مهام متدرجة للانتباه والذاكرة والوظائف التنفيذية.", "الأدوات")),
    ("daily-tools/", ("الأدوات النفسية التفاعلية", "أدوات محلية تعمل داخل المتصفح دون إرسال البيانات إلى خادم.", "الأدوات")),
    ("learning-paths/", ("مسارات التعلم القصيرة", "مسارات مترابطة تحول المعرفة إلى خطوات قابلة للمراجعة.", "الأدوات")),
    ("care-guides/", ("أدلة التعامل العملي", "أدلة موسعة للأسرة والمدرسة ومقدم الخدمة.", "الدعم")),
    ("tips/", ("النصائح النفسية العملية", "خطوات يومية وأخطاء شائعة ومؤشرات لطلب دعم متخصص.", "الدعم")),
    ("special-needs/", ("ذوو الاحتياجات الخاصة والتربية الدامجة", "أدلة للتعليم والتواصل والحواس والحركة والاستقلال والحماية.", "الدعم")),
    ("sectors/", ("الأقسام المتخصصة", "بوابات للصحة النفسية للطفل والأسرة وفئات الاستخدام المختلفة.", "الدعم")),
    ("provider-assessment-demo/", ("منصة التقييم المؤسسية", "إدارة الحالات والجلسات والسجلات ضمن حدود الخصوصية والحقوق.", "المؤسسات")),
    ("trust/", ("الثقة والمنهجية", "سياسة المصادر والمراجعة والتصحيح وحدود المحتوى.", "الحوكمة")),
    ("partners/", ("الشركاء والشفافية", "العلاقات الموثقة وسياسة عدم ادعاء شراكات غير مثبتة.", "الحوكمة")),
    ("developers/", ("واجهة المطورين", "توثيق التكامل وعقود البيانات والاستيراد المصرح به.", "التكامل")),
    ("api/", ("واجهة API", "ملفات JSON وOpenAPI للربط الآمن والمصرح به.", "التكامل")),
    ("en/", ("English homepage", "English entry point to the platform's principal resources.", "اللغات")),
    ("es/", ("Página en español", "Punto de entrada en español a los recursos principales.", "اللغات")),
])
FEATURED = (
    "encyclopedia/", "special-needs/", "care-guides/", "comparisons/",
    "library/", "daily-tools/", "assessment-lab/", "cognitive-lab/",
)


class SectionDirectoryError(ValueError):
    pass


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def noindex(source: str) -> bool:
    match = re.search(
        r'<meta\b[^>]*name=(["\'])robots\1[^>]*content=(["\'])(.*?)\2',
        source, re.I | re.S,
    )
    return bool(match and "noindex" in match.group(3).lower())


def title_description(source: str, route: str) -> tuple[str, str]:
    predefined = DEFINITIONS.get(route)
    if predefined:
        return predefined[0], predefined[1]
    title_match = re.search(r"<title\b[^>]*>(.*?)</title>", source, re.I | re.S)
    desc_match = re.search(
        r'<meta\b[^>]*name=(["\'])description\1[^>]*content=(["\'])(.*?)\2',
        source, re.I | re.S,
    )
    fallback = route.rstrip("/").replace("-", " ").replace("_", " ")
    title = clean(title_match.group(1)) if title_match else fallback
    description = clean(desc_match.group(3)) if desc_match else f"قسم منشور ضمن {BRAND}."
    return re.split(r"\s*[|—]\s*", title, maxsplit=1)[0].strip() or fallback, description


def page_count(root: Path) -> int:
    return sum(
        1
        for page in root.rglob("*.html")
        if page.name not in {"404.html", "offline.html"}
        and not noindex(page.read_text(encoding="utf-8"))
    )


def records(site: Path, homepage: str) -> list[dict[str, Any]]:
    output = []
    for entry in sorted(site.iterdir(), key=lambda item: item.name.casefold()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in TECHNICAL:
            continue
        index = entry / "index.html"
        if not index.is_file():
            continue
        source = index.read_text(encoding="utf-8")
        if noindex(source):
            continue
        route = entry.name + "/"
        title, description = title_description(source, route)
        category = DEFINITIONS.get(route, ("", "", "أقسام أخرى"))[2]
        output.append({
            "id": entry.name,
            "route": route,
            "url": BASE + route,
            "name": title,
            "summary": description,
            "category": category,
            "page_count": page_count(entry),
            "linked_from_home": bool(re.search(
                rf'href=(["\'])/?(?:pterminology-site/)?{re.escape(route)}',
                homepage, re.I,
            )),
            "featured": route in FEATURED,
        })
    order = {route: index for index, route in enumerate(DEFINITIONS)}
    return sorted(output, key=lambda item: (order.get(item["route"], 10_000), item["name"]))


def cards(items: list[dict[str, Any]], absolute: bool = False) -> str:
    return "".join(
        '<article class="section-card-v221">'
        f'<p class="section-category-v221">{html.escape(item["category"])}</p>'
        f'<h3><a href="{html.escape(item["url"] if absolute else item["route"], quote=True)}">{html.escape(item["name"])}</a></h3>'
        f'<p>{html.escape(item["summary"])}</p><span>{item["page_count"]} صفحة</span></article>'
        for item in items
    )


def inject_homepage(site: Path, items: list[dict[str, Any]]) -> int:
    path = site / "index.html"
    source = path.read_text(encoding="utf-8")
    source = re.sub(re.escape(START) + r".*?" + re.escape(END), "", source, flags=re.S)
    if 'href="sections/"' not in source:
        source, count = re.subn(
            r"</nav>", '<a href="sections/">جميع الأقسام</a></nav>',
            source, count=1, flags=re.I,
        )
        if count != 1:
            raise SectionDirectoryError("primary navigation could not be extended")
    style = (
        '<style id="section-directory-style-v221">'
        '.section-grid-v221{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px}'
        '.section-card-v221{background:#fff;border:1px solid #c6e3df;border-radius:20px;padding:20px;box-shadow:0 12px 32px rgba(31,105,104,.09)}'
        '.section-card-v221 h3{margin:.2rem 0}.section-card-v221 p{color:#526f73}'
        '.section-card-v221 span,.section-category-v221{font-weight:800;color:#7f3659}'
        '@media(max-width:1050px){.section-grid-v221{grid-template-columns:repeat(2,minmax(0,1fr))}}'
        '@media(max-width:620px){.section-grid-v221{grid-template-columns:1fr}}</style>'
    )
    if 'id="section-directory-style-v221"' not in source:
        source = source.replace("</head>", style + "</head>", 1)
    featured = [item for item in items if item["featured"]]
    block = (
        START
        + '<section class="section" data-section-directory-v221 aria-labelledby="section-directory-title-v221">'
        + '<p class="eyebrow">دليل الوصول</p><h2 id="section-directory-title-v221">استكشف أقسام المنصة</h2>'
        + '<p class="section-intro">وصول مباشر إلى المعرفة والأدلة والمقارنات والمكتبة والأدوات والموارد المؤسسية.</p>'
        + f'<div class="section-grid-v221">{cards(featured)}</div>'
        + '<p><a class="button secondary" href="sections/">عرض دليل الأقسام الكامل</a></p></section>'
        + END
    )
    if "</main>" not in source:
        raise SectionDirectoryError("homepage main landmark is missing")
    source = source.replace("</main>", block + "</main>", 1)
    if any(phrase in source for phrase in BANNED):
        raise SectionDirectoryError("operational copy leaked into homepage")
    path.write_text(source, encoding="utf-8")
    return len(featured)


def directory_html(items: list[dict[str, Any]]) -> str:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in items:
        groups.setdefault(item["category"], []).append(item)
    body = "".join(
        f'<section><h2>{html.escape(category)}</h2><div class="grid">{cards(group, True)}</div></section>'
        for category, group in groups.items()
    )
    canonical = BASE + "sections/"
    schema = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": "دليل أقسام منصة روافد",
                "description": "دليل منظم للوصول إلى أقسام المعرفة والدعم والأدوات والمصادر.",
                "url": canonical,
                "inLanguage": "ar",
                "hasPart": [
                    {"@type": "CollectionPage", "name": item["name"], "url": item["url"]}
                    for item in items
                ],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "دليل الأقسام", "item": canonical},
                ],
            },
        ],
    }, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    total = sum(item["page_count"] for item in items)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>دليل جميع أقسام المنصة | {BRAND}</title><meta name="description" content="دليل منظم للموسوعة والأدلة والمقارنات والمكتبة والمقاييس والمهام المعرفية وجميع أقسام المنصة."><meta name="keywords" content="أقسام الصحة النفسية,موسوعة علم النفس,أدلة ذوي الاحتياجات الخاصة,المقاييس النفسية,المكتبة النفسية,أدلة الأسرة"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><script type="application/ld+json">{schema}</script></head><body><header><a href="../">{BRAND}</a></header><main><p><a href="../">الرئيسية</a> / دليل الأقسام</p><h1>دليل جميع أقسام المنصة</h1><p>اختر المسار الأقرب إلى حاجتك: المعرفة، الأدوات، الدعم العملي، المصادر، الحوكمة، أو التكامل المؤسسي.</p>{body}</main><footer>{len(items)} قسمًا عامًا · {total} صفحة قابلة للفهرسة داخل الأقسام</footer><style>:root{{--ink:#103e43;--muted:#526f73;--line:#c6e3df;--bg:#effaf8}}*{{box-sizing:border-box}}body{{margin:0;padding:0 4%;font-family:Tahoma,Arial,sans-serif;line-height:1.85;color:var(--ink);background:linear-gradient(145deg,#fff,var(--bg))}}header,footer{{padding:20px 0}}main{{max-width:1200px;margin:auto}}h1{{font-size:clamp(2rem,6vw,4rem)}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}}.section-card-v221{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}</style></body></html>'''


def update_sitemap(site: Path) -> None:
    child = site / "sitemap-sections.xml"
    child.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{BASE}sections/</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>'
        '</urlset>\n',
        encoding="utf-8",
    )
    index = site / "sitemap.xml"
    tree = ET.parse(index)
    root = tree.getroot()
    namespace = root.tag.split("}", 1)[0].strip("{") if "}" in root.tag else ""
    tag = lambda name: f"{{{namespace}}}{name}" if namespace else name
    target = BASE + "sitemap-sections.xml"
    if root.tag.endswith("sitemapindex"):
        existing = {(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")}
        if target not in existing:
            node = ET.SubElement(root, tag("sitemap"))
            ET.SubElement(node, tag("loc")).text = target
    elif root.tag.endswith("urlset"):
        existing = {(node.text or "").strip() for node in root.findall("{*}url/{*}loc")}
        if BASE + "sections/" not in existing:
            node = ET.SubElement(root, tag("url"))
            ET.SubElement(node, tag("loc")).text = BASE + "sections/"
    else:
        raise SectionDirectoryError("unsupported sitemap root")
    if namespace:
        ET.register_namespace("", namespace)
    tree.write(index, encoding="utf-8", xml_declaration=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_api(site: Path, root: Path, items: list[dict[str, Any]]) -> None:
    api = site / "api/v1"
    endpoint = BASE + "api/v1/section-directory.json"
    write_json(api / "section-directory.json", {
        "api_version": "v1",
        "schema_version": VERSION,
        "section_count": len(items),
        "html_page_count": sum(item["page_count"] for item in items),
        "directory_url": BASE + "sections/",
        "items": items,
    })
    openapi_path = api / "openapi.json"
    openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
    openapi.setdefault("paths", {})["/api/v1/section-directory.json"] = {
        "get": {
            "summary": "الدليل المؤسسي لجميع أقسام المنصة",
            "responses": {"200": {"description": "الأقسام العامة وروابطها وأعداد صفحاتها"}},
        }
    }
    write_json(openapi_path, openapi)
    platform_path = api / "platform.json"
    platform = json.loads(platform_path.read_text(encoding="utf-8"))
    resources = platform.setdefault("resources", [])
    resource = {
        "id": "section-directory", "type": "collection", "title": "دليل أقسام المنصة",
        "url": endpoint, "tags": ["الأقسام", "التصفح", "واجهة API"],
    }
    platform["resources"] = [
        item for item in resources
        if not (isinstance(item, dict) and item.get("id") == "section-directory")
    ] + [resource]
    platform.setdefault("endpoints", {})["sectionDirectory"] = endpoint
    write_json(platform_path, platform)
    report_path = root / ".build/reports/public-api-v215.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report.update({
            "endpoints": len(openapi.get("paths", {})),
            "section_directory": True,
            "section_directory_schema_version": VERSION,
        })
        write_json(report_path, report)


def publish(site: Path, root: Path) -> dict[str, Any]:
    site = site.resolve()
    homepage = (site / "index.html").read_text(encoding="utf-8")
    items = records(site, homepage)
    required = {"encyclopedia/", "special-needs/", "care-guides/", "api/"}
    missing = sorted(required - {item["route"] for item in items})
    if missing:
        raise SectionDirectoryError(f"required public sections disappeared: {missing}")
    page = directory_html(items)
    if any(phrase in page for phrase in BANNED):
        raise SectionDirectoryError("operational copy leaked into directory")
    target = site / "sections/index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    featured = inject_homepage(site, items)
    update_sitemap(site)
    legacy = site / "api/v1/sections.json"
    legacy_hash = legacy.read_bytes() if legacy.is_file() else None
    update_api(site, root, items)
    if legacy_hash is not None and legacy.read_bytes() != legacy_hash:
        raise SectionDirectoryError("legacy sections endpoint was modified")
    report = {
        "schema_version": VERSION,
        "status": "passed",
        "section_count": len(items),
        "html_page_count": sum(item["page_count"] for item in items),
        "featured_on_home": featured,
        "directory_created": True,
        "separate_api_endpoint": True,
        "legacy_sections_endpoint_preserved": legacy.is_file(),
        "sitemap_registered": True,
        "operational_copy_absent": True,
    }
    write_json(site / "api/section-directory-v221.json", report)
    return report


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    print(json.dumps(publish(site, root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
