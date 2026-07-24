from __future__ import annotations

import json
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
VERSION = 215


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_brand_assets() -> list[str]:
    target = SITE / "assets"
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in ("logo-mark-v215.svg", "logo-card-v215.svg"):
        source = ROOT / "assets" / name
        if not source.is_file():
            raise SystemExit(f"Missing brand asset: {source}")
        shutil.copy2(source, target / name)
        copied.append(f"assets/{name}")
    return copied


def route_for(page: Path) -> str:
    relative = page.relative_to(SITE)
    if relative.name == "index.html":
        parent = relative.parent.as_posix()
        return "" if parent == "." else f"{parent}/"
    return relative.as_posix()


def build_catalog() -> dict:
    pages = sorted(SITE.rglob("*.html"))
    routes = [route_for(page) for page in pages]
    categories = Counter()
    for route in routes:
        first = route.split("/", 1)[0] if route else "home"
        categories[first or "home"] += 1
    public_routes = [route for route in routes if not route.startswith("google")]
    return {
        "api_version": "v1",
        "release": VERSION,
        "generated_from_commit": os.environ.get("GITHUB_SHA", "local-build"),
        "base_url": BASE,
        "language": "ar",
        "direction": "rtl",
        "page_count": len(public_routes),
        "categories": dict(sorted(categories.items())),
        "core_sections": [
            {"id": "encyclopedia", "name": "الموسوعة النفسية العربية", "url": f"{BASE}encyclopedia/"},
            {"id": "special-needs", "name": "ذوو الاحتياجات الخاصة والتربية الدامجة", "url": f"{BASE}special-needs/"},
            {"id": "care-guides", "name": "أدلة التعامل العملي", "url": f"{BASE}care-guides/"},
            {"id": "assessment-lab", "name": "المقاييس الاستكشافية", "url": f"{BASE}assessment-lab/"},
            {"id": "cognitive-lab", "name": "القدرات والمهام المعرفية", "url": f"{BASE}cognitive-lab/"},
            {"id": "magazine", "name": "المجلة والأبحاث", "url": f"{BASE}magazine/"},
            {"id": "developers", "name": "واجهة المطورين", "url": f"{BASE}developers/"},
        ],
        "endpoints": {
            "catalog": f"{BASE}api/v1/catalog.json",
            "courses": f"{BASE}api/v1/courses.json",
            "course_import_schema": f"{BASE}api/v1/course-import.schema.json",
            "openapi": f"{BASE}api/v1/openapi.json",
        },
    }


def validate_courses(payload: dict) -> dict:
    allowed = set(payload.get("policy", {}).get("allowed_rights_status", []))
    if allowed != {"written_permission_verified"}:
        raise SystemExit("Courses policy must allow only written_permission_verified")
    providers = payload.get("providers", [])
    items = payload.get("items", [])
    if not isinstance(providers, list) or not isinstance(items, list):
        raise SystemExit("Courses providers and items must be lists")
    provider_ids = {item.get("id") for item in providers}
    if None in provider_ids or len(provider_ids) != len(providers):
        raise SystemExit("Course provider IDs must be unique and non-empty")
    course_ids = set()
    for item in items:
        course_id = item.get("id")
        if not course_id or course_id in course_ids:
            raise SystemExit("Course IDs must be unique and non-empty")
        course_ids.add(course_id)
        if item.get("rights_status") != "written_permission_verified":
            raise SystemExit(f"Course lacks verified written permission: {course_id}")
        if item.get("provider_id") not in provider_ids:
            raise SystemExit(f"Unknown course provider: {course_id}")
        if not item.get("source_url") or not item.get("permission_reference"):
            raise SystemExit(f"Course permission evidence is incomplete: {course_id}")
    return {
        "api_version": "v1",
        "release": VERSION,
        "updated": payload.get("updated"),
        "policy": payload.get("policy"),
        "provider_count": len(providers),
        "course_count": len(items),
        "providers": providers,
        "items": items,
    }


def course_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}api/v1/course-import.schema.json",
        "title": "Authorized Arabic course import",
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "provider_id", "title_ar", "source_url", "rights_status", "permission_reference"],
        "properties": {
            "id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{2,80}$"},
            "provider_id": {"type": "string", "minLength": 2, "maxLength": 80},
            "title_ar": {"type": "string", "minLength": 5, "maxLength": 180},
            "title_en": {"type": "string", "maxLength": 180},
            "summary_ar": {"type": "string", "minLength": 40, "maxLength": 1200},
            "source_url": {"type": "string", "format": "uri"},
            "language": {"type": "string", "default": "ar"},
            "delivery_mode": {"enum": ["link", "embed", "metadata", "licensed-copy"]},
            "rights_status": {"const": "written_permission_verified"},
            "permission_reference": {"type": "string", "minLength": 4, "maxLength": 240},
            "permission_scope": {"type": "string", "minLength": 10, "maxLength": 1200},
            "reviewed_at": {"type": "string", "format": "date"},
            "expires_at": {"type": ["string", "null"], "format": "date"},
            "tags": {"type": "array", "items": {"type": "string", "minLength": 2, "maxLength": 60}, "uniqueItems": True},
        },
    }


def openapi_spec() -> dict:
    json_response = {"description": "ملف JSON ثابت للقراءة", "content": {"application/json": {"schema": {"type": "object"}}}}
    paths = {}
    for route, summary in (
        ("/api/v1/catalog.json", "جرد أقسام المنصة ومساراتها الأساسية"),
        ("/api/v1/courses.json", "الدورات المصرح بها كتابيًا فقط"),
        ("/api/v1/course-import.schema.json", "عقد التحقق من بيانات الدورة قبل الاستيراد"),
        ("/api/v1/openapi.json", "وصف OpenAPI لواجهة القراءة"),
    ):
        paths[route] = {"get": {"summary": summary, "operationId": route.strip("/").replace("/", "_").replace(".", "_"), "responses": {"200": json_response}}}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "واجهة منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "version": "1.0.0",
            "description": "واجهة قراءة ثابتة. لا تُضاف دورة أو مادة خارجية إلا بعد إثبات إذن كتابي ومراجعة المصدر والنطاق.",
        },
        "servers": [{"url": BASE.rstrip("/")}],
        "paths": paths,
    }


def developers_page(catalog: dict, courses: dict) -> str:
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>واجهة المطورين وAPI | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="توثيق واجهة قراءة JSON لمنصة الصحة النفسية وذوي الاحتياجات الخاصة، مع عقد آمن لاستيراد الدورات بعد التحقق من الإذن الكتابي.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{BASE}developers/">
<link rel="icon" href="../assets/logo-mark-v215.svg" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_AR">
<meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<meta property="og:title" content="واجهة المطورين وAPI">
<meta property="og:description" content="ملفات JSON موثقة للربط، وجرد أقسام، وعقد استيراد يحمي الحقوق والمصدر.">
<meta property="og:image" content="{BASE}assets/logo-card-v215.svg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps({"@context":"https://schema.org","@type":"TechArticle","name":"واجهة المطورين وAPI","inLanguage":"ar","url":f"{BASE}developers/","publisher":{"@type":"Organization","name":"منصة الصحة النفسية وذوي الاحتياجات الخاصة","logo":{"@type":"ImageObject","url":f"{BASE}assets/logo-mark-v215.svg"}}}, ensure_ascii=False)}</script>
<style>
:root{{--ink:#143f44;--muted:#527275;--brand:#0b6b66;--rose:#7f3659;--line:#c7e6e2;--bg:#f7fffd}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(145deg,#fff,var(--bg));color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.85}}a{{color:#076b65}}a:focus-visible{{outline:3px solid #168f88;outline-offset:4px}}.wrap{{width:min(1080px,92%);margin:auto}}header,footer{{border-color:var(--line);border-style:solid;border-width:0 0 1px;padding:18px 0}}footer{{border-width:1px 0 0;margin-top:40px}}.brand{{display:flex;align-items:center;gap:12px;text-decoration:none;font-weight:900;color:var(--ink)}}.brand img{{width:48px;height:48px}}main{{padding:54px 0}}h1{{font-size:clamp(2.2rem,6vw,4.4rem);line-height:1.2}}h2{{margin-top:2.2rem}}.lead{{font-size:1.18rem;color:var(--muted);max-width:850px}}.notice,.card{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px;margin:16px 0}}.notice{{border-right:6px solid var(--rose)}}code{{direction:ltr;display:inline-block;background:#eef8f6;border-radius:8px;padding:2px 7px}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}ul{{padding-right:22px}}@media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><div class="wrap"><a class="brand" href="../"><img src="../assets/logo-mark-v215.svg" alt=""><span>منصة الصحة النفسية وذوي الاحتياجات الخاصة</span></a></div></header>
<main><div class="wrap">
<p><a href="../">الصفحة الرئيسية</a> / واجهة المطورين</p>
<h1>واجهة قراءة واضحة وقابلة للتوسع</h1>
<p class="lead">توفر المنصة ملفات JSON ثابتة ومنظمة لاكتشاف الأقسام والبيانات المصرح بنشرها. الواجهة الحالية للقراءة فقط؛ ولا تنشر بيانات شخصية أو نتائج تقييم أو مواد محمية.</p>
<div class="notice"><strong>قاعدة الدورات:</strong> لا تُدرج أي دورة من موقع آخر إلا بعد توثيق إذن كتابي يحدد طريقة الربط أو التضمين أو الترجمة أو النسخ، مع حفظ مرجع الإذن ونطاقه وتاريخه.</div>
<h2>نقاط النهاية</h2>
<div class="grid">
<article class="card"><h3>جرد المنصة</h3><p><code>/api/v1/catalog.json</code></p><p>عدد الصفحات والفئات وروابط الأقسام الأساسية. العدد الحالي في البناء: {catalog['page_count']} صفحة HTML.</p></article>
<article class="card"><h3>الدورات المصرح بها</h3><p><code>/api/v1/courses.json</code></p><p>عدد المزودين: {courses['provider_count']}، وعدد الدورات المنشورة: {courses['course_count']}.</p></article>
<article class="card"><h3>عقد الاستيراد</h3><p><code>/api/v1/course-import.schema.json</code></p><p>JSON Schema يتحقق من الهوية والمصدر وحالة الحقوق ومرجع الإذن.</p></article>
<article class="card"><h3>وصف OpenAPI</h3><p><code>/api/v1/openapi.json</code></p><p>وصف آلي لنقاط القراءة الحالية لتسهيل التكامل والتوثيق.</p></article>
</div>
<h2>مبادئ التكامل</h2>
<ul><li>المصدر والرابط الأصلي والنسبة عناصر إلزامية.</li><li>الإذن الكتابي يسبق الاستيراد أو الترجمة أو التضمين.</li><li>لا تُعرض بنود المقاييس المحمية أو مفاتيح التصحيح أو المواد المرخصة خارج نطاقها.</li><li>تُراجع البيانات قبل النشر، ويُوقف العنصر عند انتهاء الإذن أو تغيّر المصدر.</li><li>لا تتضمن الواجهة بيانات مستخدمين أو سجلات صحية أو نتائج فردية.</li></ul>
</div></main>
<footer><div class="wrap"><a href="../trust/">الثقة والمنهجية</a> · <a href="../partners/">الشركاء والشفافية</a> · <a href="../api/v1/openapi.json">OpenAPI</a></div></footer>
</body></html>'''


def register_developers_sitemap() -> None:
    sitemap = SITE / "sitemap-developers.xml"
    sitemap.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{BASE}developers/</loc></url>\n'
        '</urlset>\n',
        encoding="utf-8",
    )
    index = SITE / "sitemap.xml"
    if not index.is_file():
        raise SystemExit("Missing sitemap index")
    tree = ET.parse(index)
    root = tree.getroot()
    target = f"{BASE}sitemap-developers.xml"
    existing = [(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")]
    if target not in existing:
        node = ET.SubElement(root, "sitemap")
        ET.SubElement(node, "loc").text = target
        tree.write(index, encoding="utf-8", xml_declaration=True)


def patch_homepage() -> None:
    page = SITE / "index.html"
    text = page.read_text(encoding="utf-8")
    if 'logo-mark-v215.svg' not in text:
        text = text.replace(
            '<span class="brand-mark" aria-hidden="true">ن</span>',
            '<span class="brand-mark"><img src="assets/logo-mark-v215.svg" alt="" width="48" height="48"></span>',
            1,
        )
    if '.brand-mark img{' not in text:
        text = text.replace('.brand-mark{display:grid;', '.brand-mark img{display:block;width:100%;height:100%}.brand-mark{display:grid;', 1)
    head_additions = (
        f'<link rel="icon" href="{BASE}assets/logo-mark-v215.svg" type="image/svg+xml">\n'
        f'<link rel="alternate" type="application/json" title="واجهة جرد المنصة" href="{BASE}api/v1/catalog.json">\n'
        f'<meta property="og:image" content="{BASE}assets/logo-card-v215.svg">\n'
        f'<meta property="og:image:alt" content="شعار منصة الصحة النفسية وذوي الاحتياجات الخاصة">\n'
        f'<meta name="twitter:image" content="{BASE}assets/logo-card-v215.svg">\n'
    )
    if 'logo-card-v215.svg' not in text:
        text = text.replace('<meta name="color-scheme" content="light">', '<meta name="color-scheme" content="light">\n' + head_additions, 1)
    if 'href="developers/"' not in text:
        text = text.replace('<a href="partners/">الشركاء</a>', '<a href="partners/">الشركاء</a><a href="developers/">واجهة API</a>', 1)
    page.write_text(text, encoding="utf-8")


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing generated site: {SITE}")
    assets = copy_brand_assets()
    api_dir = SITE / "api" / "v1"
    api_dir.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    source_courses = json.loads((ROOT / "content" / "courses-v215.json").read_text(encoding="utf-8"))
    courses = validate_courses(source_courses)
    write_json(api_dir / "catalog.json", catalog)
    write_json(api_dir / "courses.json", courses)
    write_json(api_dir / "course-import.schema.json", course_schema())
    write_json(api_dir / "openapi.json", openapi_spec())
    developer_dir = SITE / "developers"
    developer_dir.mkdir(parents=True, exist_ok=True)
    (developer_dir / "index.html").write_text(developers_page(catalog, courses), encoding="utf-8")
    register_developers_sitemap()
    patch_homepage()
    report = {
        "version": VERSION,
        "status": "built",
        "brand_assets": assets,
        "page_count": catalog["page_count"],
        "api_endpoints": len(catalog["endpoints"]),
        "course_count": courses["course_count"],
        "course_rights_gate": "written_permission_verified",
        "developers_page": True,
        "developers_sitemap": True,
    }
    write_json(SITE / "api" / "enterprise-platform-v215.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
