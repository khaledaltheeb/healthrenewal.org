from __future__ import annotations

"""توحيد بيان المنصة وفهرس الأقسام العامة في عقد API إضافي ومتوافق مع v1.

لا يغيّر الناشر ملفات الدورات أو المصادر، ولا يفتح أي مصدر غير مخول، ولا
ينشر بيانات مستخدمين أو سجلات صحية أو مواد مقاييس محمية.
"""

import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = 231
API_VERSION = "1.1.0"
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
API_BASE = BASE_URL + "api/v1/"
INSTITUTIONAL_NAME = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
FOUNDING_NAME = "مصطلحات علم النفس"
DEVELOPERS_MARKER = "data-platform-manifest-v231"
PROHIBITED_PUBLIC_TERMS = ("معاقين", "المعاقين", "ذوو الإعاقة", "ذوي الإعاقة")

# id, route, Arabic name, type, audiences, tags
_SECTION_ROWS: tuple[tuple[Any, ...], ...] = (
    ("sections", "sections/", "دليل أقسام المنصة", "directory", ["الجمهور", "الأسر", "المختصون"], ["أقسام المنصة", "دليل المحتوى", "التصفح"]),
    ("encyclopedia", "encyclopedia/", "الموسوعة النفسية العربية", "collection", ["الجمهور", "الطلاب", "المختصون"], ["علم النفس", "الصحة النفسية", "الموسوعة"]),
    ("terms", "terms/", "المعجم النفسي", "collection", ["الجمهور", "الطلاب"], ["مصطلحات علم النفس", "معجم عربي", "تعريفات"]),
    ("hubs", "hubs/", "المراكز الموضوعية", "collection", ["الجمهور", "الباحثون"], ["موضوعات نفسية", "روابط داخلية", "مراكز معرفية"]),
    ("special-needs", "special-needs/", "ذوو الاحتياجات الخاصة والتربية الدامجة", "collection", ["الأسر", "المعلمون", "مقدمو الخدمة"], ["التربية الدامجة", "التدخل المبكر", "الدعم الأسري"]),
    ("care-guides", "care-guides/", "أدلة التعامل العملي", "collection", ["الأسر", "مقدمو الرعاية", "المختصون"], ["أدلة عملية", "الأسرة", "مقدم الخدمة"]),
    ("tips", "tips/", "النصائح النفسية العملية", "collection", ["الجمهور", "الأسر"], ["نصائح نفسية", "جودة الحياة", "التثقيف"]),
    ("daily-tools", "daily-tools/", "الأدوات اليومية", "application", ["الجمهور", "الأسر"], ["أدوات تفاعلية", "تنظيم يومي", "تخزين محلي"]),
    ("learning-paths", "learning-paths/", "مسارات التعلم", "collection", ["الجمهور", "الطلاب", "مقدمو الرعاية"], ["تعلم نفسي", "مسارات عملية", "مهارات"]),
    ("assessment-lab", "assessment-lab/", "مختبر المقاييس والاستكشاف", "application", ["الجمهور", "المختصون"], ["مقاييس استكشافية", "تثقيف", "حدود التفسير"]),
    ("cognitive-lab", "cognitive-lab/", "مختبر القدرات المعرفية", "application", ["الجمهور", "الطلاب", "المختصون"], ["قدرات معرفية", "مهام تفاعلية", "تعلم"]),
    ("provider-assessment-demo", "provider-assessment-demo/", "منصة التقييم والسجل المهني", "application", ["المختصون", "مقدمو الخدمة"], ["التقييم المهني", "سجل الحالات", "حقوق الأدوات"]),
    ("magazine", "magazine/", "المجلة والأبحاث", "collection", ["الجمهور", "الباحثون", "المختصون"], ["أبحاث", "دراسات", "تحليل"]),
    ("comparisons", "comparisons/", "المقارنات المنهجية", "collection", ["الجمهور", "الطلاب", "المختصون"], ["مقارنة المفاهيم", "الفروق", "التعلم"]),
    ("library", "library/", "المكتبة العربية", "collection", ["الجمهور", "الأسر", "الباحثون"], ["مكتبة", "أدلة", "مصادر"]),
    ("trust", "trust/", "الثقة والمنهجية", "governance", ["الجمهور", "الباحثون", "الشركاء"], ["المنهجية", "المراجعة", "الشفافية"]),
    ("partners", "partners/", "الشركاء والشفافية", "governance", ["الشركاء", "الجهات", "الجمهور"], ["الشراكات", "الشفافية", "السجل العام"]),
    ("developers", "developers/", "واجهة المطورين والتكامل", "documentation", ["المطورون", "الشركاء التقنيون"], ["API", "OpenAPI", "تكامل المواقع"]),
)

SECTION_DEFINITIONS: tuple[dict[str, Any], ...] = tuple(
    {
        "id": row[0],
        "route": row[1],
        "name_ar": row[2],
        "type": row[3],
        "audiences": row[4],
        "tags": row[5],
    }
    for row in _SECTION_ROWS
)

ENDPOINTS: dict[str, str] = {
    "platform": API_BASE + "platform.json",
    "health": API_BASE + "health.json",
    "site": API_BASE + "site.json",
    "sections": API_BASE + "sections.json",
    "openapi": API_BASE + "openapi.json",
    "contentIndex": API_BASE + "content-index.json",
    "taxonomy": API_BASE + "taxonomy.json",
    "courses": API_BASE + "courses.json",
    "sources": API_BASE + "sources.json",
    "courseSchema": API_BASE + "courses.schema.json",
    "courseExample": API_BASE + "courses.example.json",
}
ENDPOINT_FILES = tuple(url.removeprefix(API_BASE) for url in ENDPOINTS.values())


class PublicApiManifestError(ValueError):
    pass


def generated_date() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PublicApiManifestError(f"invalid JSON: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise PublicApiManifestError(f"expected object: {path}")
    return payload


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def validate_registry() -> None:
    ids: set[str] = set()
    routes: set[str] = set()
    for item in SECTION_DEFINITIONS:
        identifier = str(item["id"])
        route = str(item["route"])
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
            raise PublicApiManifestError(f"invalid section id: {identifier}")
        if not re.fullmatch(r"[a-z0-9][a-z0-9./-]*/", route):
            raise PublicApiManifestError(f"invalid section route: {route}")
        if identifier in ids or route in routes:
            raise PublicApiManifestError(f"duplicate section id or route: {identifier} {route}")
        ids.add(identifier)
        routes.add(route)
        if not item["name_ar"] or not item["type"] or not item["audiences"] or not item["tags"]:
            raise PublicApiManifestError(f"incomplete section definition: {identifier}")


def public_sections() -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "name_ar": item["name_ar"],
            "url": BASE_URL + item["route"],
            "type": item["type"],
            "audiences": list(item["audiences"]),
            "tags": list(item["tags"]),
        }
        for item in SECTION_DEFINITIONS
    ]


def build_platform(existing: dict[str, Any], date_value: str) -> dict[str, Any]:
    integration = deepcopy(existing.get("integrationPolicy"))
    if not isinstance(integration, dict):
        integration = {}
    integration.update(
        {
            "externalCourseImport": "permission_required",
            "defaultDecision": "deny",
            "metadataOnly": True,
            "requiredEvidence": [
                "source authorization",
                "content license",
                "provider identity",
                "canonical source URL",
                "permission validity window",
            ],
            "prohibited": [
                "circumventing access controls",
                "copying protected course materials",
                "copying protected assessment items or scoring keys",
                "removing attribution",
                "publishing unverified provider claims",
                "publishing personal or clinical records",
            ],
        }
    )
    return {
        "apiVersion": API_VERSION,
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": date_value,
        "name": INSTITUTIONAL_NAME,
        "alternateName": FOUNDING_NAME,
        "baseUrl": BASE_URL,
        "defaultLanguage": "ar",
        "languages": ["ar", "en", "es"],
        "direction": "rtl",
        "licenseNotice": existing.get("licenseNotice")
        or "تختلف حقوق المحتوى والأدوات والدورات حسب المصدر. لا يعاد نشر محتوى خارجي أو استيراده إلا بإذن موثق وترخيص متوافق.",
        "disclaimer": existing.get("disclaimer")
        or "البيانات للتثقيف والتكامل المعلوماتي ولا تثبت تشخيصًا ولا تستبدل التقييم أو العلاج الفردي.",
        "capabilities": [
            "institutional-section-discovery",
            "content-index-shards",
            "topic-taxonomy",
            "authorized-course-metadata",
            "openapi-3.1",
            "multilingual-page-metadata",
        ],
        "resources": [
            {
                "id": item["id"],
                "type": item["type"],
                "title": item["name_ar"],
                "url": item["url"],
                "tags": list(item["tags"]),
            }
            for item in public_sections()
        ],
        "endpoints": deepcopy(ENDPOINTS),
        "integrationPolicy": integration,
        "privacyBoundary": {
            "personalData": False,
            "clinicalRecords": False,
            "assessmentResponses": False,
            "publicMetadataOnly": True,
        },
        "compatibility": {
            "major": "v1",
            "additiveFields": True,
            "sectionCoreFieldsPreserved": ["id", "name_ar", "url"],
        },
    }


def build_sections(date_value: str) -> dict[str, Any]:
    sections = public_sections()
    return {
        "api_version": "v1",
        "schema_version": SCHEMA_VERSION,
        "generated_at": date_value,
        "count": len(sections),
        "sections": sections,
        "usage_notice": "فهرس وصفي للأقسام العامة؛ لا يتضمن بيانات مستخدمين أو سجلات صحية.",
    }


def _response(schema: str, description: str) -> dict[str, Any]:
    return {
        "200": {
            "description": description,
            "content": {"application/json": {"schema": {"$ref": schema}}},
        }
    }


def patch_openapi(document: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(document)
    result["openapi"] = "3.1.0"
    info = result.setdefault("info", {})
    info.update(
        {
            "title": "واجهة منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "version": API_VERSION,
            "description": (
                "واجهة قراءة عامة ثابتة لاكتشاف أقسام المنصة وفهرس المحتوى والتصنيف "
                "وفهارس الدورات ذات الإذن النشط، دون بيانات شخصية أو مواد مقاييس محمية."
            ),
        }
    )
    tags = result.setdefault("tags", [])
    known = {str(item.get("name")) for item in tags if isinstance(item, dict)}
    for item in (
        {"name": "Platform", "description": "هوية المنصة وقدرات التكامل"},
        {"name": "Discovery", "description": "الأقسام وفهرس المحتوى والتصنيف"},
        {"name": "Authorized courses", "description": "فهارس الدورات ذات الإذن النشط"},
    ):
        if item["name"] not in known:
            tags.append(item)
            known.add(item["name"])

    paths = result.setdefault("paths", {})
    paths["/api/v1/platform.json"] = {
        "get": {
            "tags": ["Platform"],
            "summary": "بيان المنصة والموارد ونقاط النهاية",
            "responses": _response("#/components/schemas/PlatformManifest", "بيان المنصة المؤسسي"),
        }
    }
    paths["/api/v1/sections.json"] = {
        "get": {
            "tags": ["Discovery"],
            "summary": "فهرس الأقسام العامة",
            "responses": _response("#/components/schemas/SectionsIndex", "قائمة الأقسام العامة المنشورة"),
        }
    }

    schemas = result.setdefault("components", {}).setdefault("schemas", {})
    section_types = ["directory", "collection", "application", "documentation", "governance"]
    schemas["Section"] = {
        "type": "object",
        "required": ["id", "name_ar", "url", "type", "audiences", "tags"],
        "properties": {
            "id": {"type": "string"},
            "name_ar": {"type": "string"},
            "url": {"type": "string", "format": "uri"},
            "type": {"enum": section_types},
            "audiences": {"type": "array", "items": {"type": "string"}},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
    }
    schemas["PlatformResource"] = {
        "type": "object",
        "required": ["id", "type", "title", "url", "tags"],
        "properties": {
            "id": {"type": "string"},
            "type": {"enum": section_types},
            "title": {"type": "string"},
            "url": {"type": "string", "format": "uri"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
    }
    schemas["SectionsIndex"] = {
        "type": "object",
        "required": ["api_version", "schema_version", "generated_at", "count", "sections"],
        "properties": {
            "api_version": {"const": "v1"},
            "schema_version": {"const": SCHEMA_VERSION},
            "generated_at": {"type": "string", "format": "date"},
            "count": {"type": "integer", "minimum": 1},
            "sections": {"type": "array", "items": {"$ref": "#/components/schemas/Section"}},
        },
    }
    schemas["PlatformManifest"] = {
        "type": "object",
        "required": [
            "apiVersion",
            "schemaVersion",
            "generatedAt",
            "name",
            "baseUrl",
            "languages",
            "resources",
            "endpoints",
            "integrationPolicy",
        ],
        "properties": {
            "apiVersion": {"const": API_VERSION},
            "schemaVersion": {"const": SCHEMA_VERSION},
            "generatedAt": {"type": "string", "format": "date"},
            "name": {"type": "string"},
            "baseUrl": {"type": "string", "format": "uri"},
            "languages": {"type": "array", "items": {"type": "string"}},
            "resources": {"type": "array", "items": {"$ref": "#/components/schemas/PlatformResource"}},
            "endpoints": {"type": "object", "additionalProperties": {"type": "string", "format": "uri"}},
            "integrationPolicy": {"type": "object"},
        },
    }
    return result


def patch_developers_page(path: Path, section_count: int) -> bool:
    source = path.read_text(encoding="utf-8")
    if DEVELOPERS_MARKER in source:
        return False
    block = f'''<section class="panel" {DEVELOPERS_MARKER}><h2>سجل المنصة والأقسام</h2>
<p>يعرض <code>{API_BASE}platform.json</code> هوية المنصة وقدراتها ونقاط النهاية، ويعرض <code>{API_BASE}sections.json</code> سجلًا موحدًا يضم {section_count} قسمًا عامًا مع نوع كل قسم وجمهوره وكلماته الموضوعية.</p>
<p>تتضمن نقاط الاكتشاف فهرس المحتوى المجزأ والتصنيف الموضوعي، بينما تبقى فهارس الدورات خاضعة لإذن نشط ورفض افتراضي.</p></section>'''
    if "</main>" not in source:
        raise PublicApiManifestError("developers page main landmark is missing")
    source = source.replace("</main>", block + "</main>", 1)
    source = source.replace("<span>الإصدار: v1</span>", "<span>الإصدار: v1.1</span>", 1)
    path.write_text(source, encoding="utf-8")
    return True


def validate_output(site: Path, platform: dict[str, Any], sections: dict[str, Any]) -> None:
    validate_registry()
    missing_routes = [
        item["route"]
        for item in SECTION_DEFINITIONS
        if not (site / item["route"] / "index.html").is_file()
    ]
    if missing_routes:
        raise PublicApiManifestError(f"published section routes are missing: {missing_routes}")
    api = site / "api" / "v1"
    missing_files = [name for name in ENDPOINT_FILES if not (api / name).is_file()]
    if missing_files:
        raise PublicApiManifestError(f"public API endpoint files are missing: {missing_files}")
    expected_ids = {str(item["id"]) for item in SECTION_DEFINITIONS}
    actual_ids = [str(item.get("id")) for item in sections.get("sections") or []]
    if sections.get("count") != len(expected_ids) or len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != expected_ids:
        raise PublicApiManifestError("section registry identity or count mismatch")
    for key, url in ENDPOINTS.items():
        if platform.get("endpoints", {}).get(key) != url:
            raise PublicApiManifestError(f"platform endpoint mismatch: {key}")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "khaledaltheeb.github.io":
            raise PublicApiManifestError(f"non-public endpoint URL: {url}")
    if platform.get("integrationPolicy", {}).get("defaultDecision") != "deny":
        raise PublicApiManifestError("course integration policy must remain deny-by-default")
    if platform.get("privacyBoundary", {}).get("publicMetadataOnly") is not True:
        raise PublicApiManifestError("public metadata privacy boundary is missing")
    serialized = json.dumps({"platform": platform, "sections": sections}, ensure_ascii=False)
    found = [term for term in PROHIBITED_PUBLIC_TERMS if term in serialized]
    if found:
        raise PublicApiManifestError(f"prohibited public terminology found: {found}")


def upgrade(site: Path, root: Path | None = None) -> dict[str, Any]:
    target = Path(site).resolve()
    project_root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    if not target.is_dir():
        raise PublicApiManifestError(f"site output does not exist: {target}")
    api = target / "api" / "v1"
    developers = target / "developers" / "index.html"
    for required in (api / "platform.json", api / "sections.json", api / "openapi.json", developers):
        if not required.is_file():
            raise PublicApiManifestError(f"required API publication input is missing: {required}")

    protected_before = {
        name: (api / name).read_bytes()
        for name in ("courses.json", "sources.json")
        if (api / name).is_file()
    }
    date_value = generated_date()
    platform = build_platform(read_object(api / "platform.json"), date_value)
    sections = build_sections(date_value)
    openapi = patch_openapi(read_object(api / "openapi.json"))

    write_json(api / "platform.json", platform)
    write_json(api / "sections.json", sections)
    write_json(api / "openapi.json", openapi)
    developers_changed = patch_developers_page(developers, len(SECTION_DEFINITIONS))
    validate_output(target, platform, sections)

    for name, content in protected_before.items():
        if (api / name).read_bytes() != content:
            raise PublicApiManifestError(f"protected authorized-course file changed unexpectedly: {name}")

    report = {
        "schema_version": SCHEMA_VERSION,
        "api_version": API_VERSION,
        "generated_at": date_value,
        "status": "passed",
        "sections": len(SECTION_DEFINITIONS),
        "endpoints": len(ENDPOINTS),
        "developers_page_changed": developers_changed,
        "deny_by_default": True,
        "authorized_course_files_unchanged": sorted(protected_before),
        "content_discovery": True,
        "taxonomy": True,
        "privacy_boundary": "public-metadata-only",
    }
    write_json(target / "api" / "public-api-manifest-v231.json", report)
    write_json(project_root / ".build" / "reports" / "public-api-manifest-v231.json", report)
    return report


def main() -> int:
    import sys

    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    print(json.dumps(upgrade(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
