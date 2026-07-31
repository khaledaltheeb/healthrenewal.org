from __future__ import annotations

import html
import json
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
SOURCE_MANIFEST = ROOT / "content" / "integrations" / "course-sources-v215.json"
FALLBACK_IMPORT = ROOT / "content" / "integrations" / "imported-courses-v215.json"
BUILD_IMPORT = ROOT / ".build" / "authorized-courses-v215.json"
SCHEMA_VERSION = 215
BASE_URL = "https://healthrenewal.org/"
API_BASE = f"{BASE_URL}api/v1/"


class PublicApiError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PublicApiError(f"Expected an object in {path}")
    return data


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def public_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in manifest.get("sources") or []:
        if (
            not isinstance(source, dict)
            or not source.get("enabled")
            or source.get("permission_status") != "approved"
        ):
            continue
        result.append(
            {
                "id": source.get("id"),
                "provider": source.get("provider"),
                "license_url": source.get("license_url"),
                "permission_status": "approved",
                "allowed_actions": sorted(set(source.get("allowed_actions") or [])),
            }
        )
    return sorted(result, key=lambda item: str(item.get("id") or ""))


def validate_courses(
    imported: dict[str, Any],
    approved_ids: set[str],
) -> list[dict[str, Any]]:
    if imported.get("schema_version") != SCHEMA_VERSION:
        raise PublicApiError("course import schema version mismatch")
    courses = imported.get("courses")
    if not isinstance(courses, list):
        raise PublicApiError("courses must be a list")

    ids: set[str] = set()
    urls: set[str] = set()
    clean: list[dict[str, Any]] = []
    for item in courses:
        if not isinstance(item, dict):
            raise PublicApiError("each course must be an object")
        required = {"id", "source_id", "provider", "url", "permission_status"}
        if not required.issubset(item):
            raise PublicApiError(
                f"course is missing required fields: {sorted(required - set(item))}"
            )
        if item["source_id"] not in approved_ids:
            raise PublicApiError(
                f"course references a source without active permission: {item['source_id']}"
            )
        if item["permission_status"] != "approved":
            raise PublicApiError(
                "published course must have approved permission status"
            )
        if not (item.get("title_ar") or item.get("title")):
            raise PublicApiError(
                "published course requires an Arabic or source title"
            )
        if item["id"] in ids or item["url"] in urls:
            raise PublicApiError("duplicate course id or URL")
        ids.add(str(item["id"]))
        urls.add(str(item["url"]))
        clean.append(item)

    return sorted(
        clean,
        key=lambda item: (
            str(item.get("provider") or ""),
            str(item.get("title_ar") or item.get("title") or ""),
        ),
    )


def course_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["id", "source_id", "provider", "url", "permission_status"],
        "properties": {
            "id": {"type": "string"},
            "source_id": {"type": "string"},
            "provider": {"type": "string"},
            "title_ar": {"type": "string"},
            "title": {"type": "string"},
            "description_ar": {"type": "string"},
            "description": {"type": "string"},
            "url": {"type": "string", "format": "uri"},
            "language": {"type": "string"},
            "format": {"type": "string"},
            "duration": {"type": "string"},
            "price_text": {"type": "string"},
            "updated_at": {"type": ["string", "null"]},
            "license_url": {"type": "string", "format": "uri"},
            "permission_status": {"const": "approved"},
        },
    }


def build_openapi(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    document = deepcopy(existing) if existing else {}
    document["openapi"] = "3.1.0"
    info = document.setdefault("info", {})
    info.update(
        {
            "title": "واجهة منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "version": "1.0.0",
            "description": (
                "واجهة قراءة عامة ثابتة لاكتشاف المنصة والبيانات المنشورة "
                "والدورات ذات الإذن الموثق. لا تمنح حق إعادة نشر مواد محمية "
                "ولا تتضمن تشخيصًا أو بيانات شخصية."
            ),
            "license": {
                "name": "Rights vary by resource — راجع ترخيص كل مورد",
                "url": f"{BASE_URL}developers/",
            },
        }
    )
    document["servers"] = [{"url": BASE_URL, "description": "الموقع العام"}]
    paths = document.setdefault("paths", {})
    additions = {
        "/api/v1/health.json": ("حالة واجهة القراءة", "الواجهة متاحة"),
        "/api/v1/site.json": ("بيانات تعريف المنصة", "بيانات المنصة والإصدار"),
        "/api/v1/sections.json": ("فهرس أقسام المنصة", "قائمة الأقسام العامة"),
        "/api/v1/courses.json": (
            "الدورات المصرح باستيراد فهارسها",
            "قائمة الدورات ذات الإذن النشط",
        ),
        "/api/v1/sources.json": (
            "مصادر الدورات المصرح بها",
            "بيانات عامة عن المصادر ذات الإذن النشط",
        ),
    }
    for path, (summary, description) in additions.items():
        paths[path] = {
            "get": {
                "summary": summary,
                "responses": {"200": {"description": description}},
            }
        }
    schemas = document.setdefault("components", {}).setdefault("schemas", {})
    schemas["Course"] = course_schema()
    return document


def build_developers_html(course_count: int, source_count: int) -> str:
    endpoints = [
        ("platform.json", "اكتشاف المنصة والموارد الأصلية"),
        ("courses.schema.json", "مخطط تغذية الدورات"),
        ("health.json", "حالة الواجهة وإصدار العقد"),
        ("site.json", "بيانات تعريف المنصة"),
        ("sections.json", "فهرس الأقسام"),
        ("courses.json", "الدورات ذات الإذن النشط"),
        ("sources.json", "المصادر المصرح بها"),
        ("openapi.json", "عقد OpenAPI 3.1 الموحد"),
    ]
    rows = "".join(
        (
            f'<tr><td><code>{html.escape(API_BASE + path)}</code></td>'
            f'<td>{html.escape(description)}</td></tr>'
        )
        for path, description in endpoints
    )
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": "واجهة المطورين وAPI",
            "inLanguage": "ar",
            "url": BASE_URL + "developers/",
            "description": "توثيق واجهات JSON العامة وسياسة استيراد الدورات المصرح بها.",
            "publisher": {
                "@type": "Organization",
                "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            },
        },
        ensure_ascii=False,
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>واجهة المطورين وAPI | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="توثيق واجهة API العامة: اكتشاف الأقسام، بيانات المنصة، ومصادر الدورات المصرح بها وفق إذن مكتوب ورفض افتراضي.">
<meta name="keywords" content="واجهة API,API عربي,بيانات الصحة النفسية,تكامل المواقع,OpenAPI,فهرس الدورات,ترخيص المحتوى,مصادر موثقة">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#075f5b">
<link rel="canonical" href="{BASE_URL}developers/"><link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="../assets/brand/logo-mark.svg" type="image/svg+xml"><link rel="search" type="application/opensearchdescription+xml" title="البحث في المنصة" href="../opensearch.xml">
<meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta property="og:title" content="واجهة المطورين وAPI"><meta property="og:description" content="واجهات JSON وعقد OpenAPI وسياسة تمنع استيراد أي دورة بلا إذن موثق."><meta property="og:url" content="{BASE_URL}developers/"><meta property="og:image" content="{BASE_URL}assets/brand/social-card.svg">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="واجهة المطورين وAPI"><meta name="twitter:description" content="واجهة قراءة عامة وعقد تكامل موحد وسياسة إذن موثق."><meta name="twitter:image" content="{BASE_URL}assets/brand/social-card.svg">
<script type="application/ld+json">{schema}</script>
<style>:root{{--ink:#143f44;--muted:#527275;--brand:#0b6b66;--line:#b9ddd8;--soft:#e5faf7}}*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.85;color:var(--ink);background:linear-gradient(145deg,#fff,var(--soft))}}a{{color:#076b65}}.wrap{{width:min(1080px,92%);margin:auto}}header{{background:#fff;border-bottom:1px solid var(--line)}}header .wrap{{display:flex;align-items:center;gap:12px;padding:15px 0}}header img{{width:48px;height:48px}}main{{padding:54px 0}}h1{{font-size:clamp(2.2rem,6vw,4.4rem);line-height:1.2}}h2{{margin-top:2.2rem}}.lead,.note{{color:var(--muted)}}.panel{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:22px;margin:18px 0;box-shadow:0 16px 40px rgba(31,105,104,.09)}}table{{width:100%;border-collapse:collapse;background:#fff}}th,td{{padding:12px;border:1px solid var(--line);text-align:right;vertical-align:top}}code{{direction:ltr;unicode-bidi:embed;word-break:break-all}}.status{{display:flex;gap:12px;flex-wrap:wrap}}.status span{{background:var(--soft);padding:8px 12px;border-radius:999px;font-weight:800}}footer{{border-top:1px solid var(--line);padding:30px 0;margin-top:40px}}@media(max-width:720px){{table,thead,tbody,tr,th,td{{display:block}}th{{background:var(--soft)}}}}</style></head><body>
<header><div class="wrap"><a href="../"><img src="../assets/brand/logo-mark.svg" alt="شعار المنصة"></a><strong>منصة الصحة النفسية وذوي الاحتياجات الخاصة</strong></div></header><main class="wrap"><p><a href="../">الرئيسية</a> ← واجهة المطورين</p><h1>واجهة المطورين وAPI</h1>
<p class="lead">واجهة قراءة عامة ثابتة تساعد المواقع والتطبيقات على اكتشاف أقسام المنصة وقراءة الفهارس المصرح بها. لا تحتوي على بنود مقاييس محمية، ولا تمنح ترخيصًا تلقائيًا لإعادة النشر، ولا تُستخدم لبناء تشخيص آلي.</p>
<div class="status"><span>الإصدار: v1</span><span>المصادر المصرح بها: {source_count}</span><span>الدورات المنشورة: {course_count}</span><span>السياسة: رفض افتراضي</span></div>
<section class="panel"><h2>نقاط النهاية</h2><table><thead><tr><th>الرابط</th><th>الغرض</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="panel"><h2>سياسة استيراد الدورات</h2><p>لا يُفعّل أي مصدر لمجرد أن بياناته متاحة للعامة. يتطلب التفعيل إذنًا مكتوبًا ومرجعًا داخليًا قابلًا للتدقيق وتاريخ منح الإذن ورابط الترخيص وتصريحًا صريحًا باستيراد الفهرس. يقتصر النقل على JSON أو CSV من نطاقات HTTPS مدرجة في قائمة السماح، مع حدود للحجم وعدد السجلات ومنع التحويل إلى نطاق غير مصرح به.</p><p class="note">عرض دورة في الفهرس لا يعني اعتمادها علميًا أو ضمان جودتها أو منح حق نسخ موادها. تبقى شروط الجهة المالكة هي المرجع.</p></section>
<section class="panel"><h2>الحفاظ على التوافق</h2><p>تُدمج نقاط القراءة الجديدة مع عقد API الأصلي بدل استبداله؛ لذلك تبقى ملفات اكتشاف المنصة ومخطط الدورات والمثال التوضيحي متاحة، وتضاف إليها الصحة والأقسام والمصادر والدورات ذات الإذن النشط.</p></section>
<section class="panel"><h2>الاستخدام المسؤول</h2><ul><li>احتفظ برابط المصدر والترخيص عند عرض البيانات.</li><li>لا تستخدم الواجهة لتشخيص أو قرار علاجي أو تعليمي.</li><li>لا تنسخ بنود المقاييس أو مفاتيح التصحيح أو المواد المقيدة.</li><li>طبّق التخزين المؤقت ومعدل طلبات معقولًا.</li></ul></section>
<section class="panel"><h2>مثال قراءة</h2><pre><code>fetch('{API_BASE}sections.json')
  .then(response =&gt; response.json())
  .then(data =&gt; console.log(data.sections));</code></pre></section></main>
<footer><div class="wrap"><a href="../trust/">الثقة والمنهجية</a> · <a href="../api/">واجهة API</a> · <a href="../">الصفحة الرئيسية</a></div></footer></body></html>'''


def build_sitemap() -> str:
    root = ET.Element(
        "urlset",
        xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
    )
    url = ET.SubElement(root, "url")
    ET.SubElement(url, "loc").text = f"{BASE_URL}developers/"
    ET.SubElement(url, "lastmod").text = datetime.now(timezone.utc).date().isoformat()
    ET.SubElement(url, "changefreq").text = "monthly"
    ET.SubElement(url, "priority").text = "0.7"
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def publish(
    site: Path = SITE,
    manifest_path: Path = SOURCE_MANIFEST,
    import_path: Path | None = None,
) -> dict[str, Any]:
    if not site.is_dir():
        raise PublicApiError(f"site output does not exist: {site}")
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("policy") != "deny-by-default"
    ):
        raise PublicApiError("course source manifest contract mismatch")
    sources = public_sources(manifest)
    approved_ids = {str(item["id"]) for item in sources}
    selected_import = import_path or (
        BUILD_IMPORT if BUILD_IMPORT.is_file() else FALLBACK_IMPORT
    )
    courses = validate_courses(read_json(selected_import), approved_ids)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    api = site / "api" / "v1"
    existing_openapi = (
        read_json(api / "openapi.json")
        if (api / "openapi.json").is_file()
        else None
    )
    merged_openapi = build_openapi(existing_openapi)
    write_json(
        api / "health.json",
        {
            "status": "ok",
            "api_version": "v1",
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
        },
    )
    write_json(
        api / "site.json",
        {
            "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "founding_name": "مصطلحات علم النفس",
            "language": "ar",
            "direction": "rtl",
            "url": BASE_URL,
            "api_version": "v1",
            "openapi": f"{API_BASE}openapi.json",
            "usage_notice": (
                "المحتوى للتثقيف العام ولا يُستخدم لتشخيص آلي أو قرار علاجي "
                "أو تعليمي."
            ),
        },
    )
    sections = [
        {
            "id": "encyclopedia",
            "name_ar": "الموسوعة النفسية العربية",
            "url": f"{BASE_URL}encyclopedia/",
        },
        {
            "id": "special-needs",
            "name_ar": "ذوو الاحتياجات الخاصة والتربية الدامجة",
            "url": f"{BASE_URL}special-needs/",
        },
        {
            "id": "care-guides",
            "name_ar": "أدلة التعامل العملي",
            "url": f"{BASE_URL}care-guides/",
        },
        {
            "id": "tips",
            "name_ar": "النصائح النفسية العملية",
            "url": f"{BASE_URL}tips/",
        },
        {
            "id": "assessment-lab",
            "name_ar": "المقاييس والاستكشاف",
            "url": f"{BASE_URL}assessment-lab/",
        },
        {
            "id": "cognitive-lab",
            "name_ar": "القدرات المعرفية",
            "url": f"{BASE_URL}cognitive-lab/",
        },
        {
            "id": "magazine",
            "name_ar": "المجلة والأبحاث",
            "url": f"{BASE_URL}magazine/",
        },
    ]
    write_json(
        api / "sections.json",
        {"api_version": "v1", "count": len(sections), "sections": sections},
    )
    write_json(
        api / "sources.json",
        {"api_version": "v1", "count": len(sources), "sources": sources},
    )
    write_json(
        api / "courses.json",
        {
            "api_version": "v1",
            "generated_at": generated_at,
            "count": len(courses),
            "courses": courses,
        },
    )
    write_json(api / "openapi.json", merged_openapi)

    developers = site / "developers"
    developers.mkdir(parents=True, exist_ok=True)
    (developers / "index.html").write_text(
        build_developers_html(len(courses), len(sources)),
        encoding="utf-8",
    )
    (site / "sitemap-developers.xml").write_text(
        build_sitemap(),
        encoding="utf-8",
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "api_version": "v1",
        "generated_at": generated_at,
        "endpoints": len(merged_openapi.get("paths", {})),
        "preserved_existing_paths": bool(existing_openapi),
        "sections": len(sections),
        "approved_sources": len(sources),
        "courses": len(courses),
        "permission_policy": "deny-by-default",
        "openapi": True,
        "developers_page": True,
    }
    write_json(ROOT / ".build" / "reports" / "public-api-v215.json", report)
    return report


def main() -> int:
    print(json.dumps(publish(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
