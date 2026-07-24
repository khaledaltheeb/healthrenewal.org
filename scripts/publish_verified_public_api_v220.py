from __future__ import annotations

import json
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import import_authorized_courses_v215 as importer
from scripts import publish_public_api_v215 as api_publisher

BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
CONTRACT_VERSION = 220
CORE_SECTION_IDS = {
    "encyclopedia",
    "special-needs",
    "care-guides",
    "tips",
    "assessment-lab",
    "cognitive-lab",
    "magazine",
}
OPTIONAL_SECTIONS = (
    ("trust", "الثقة والمنهجية", "trust/"),
    ("partners", "الشركاء والتعاون", "partners/"),
    ("provider-assessment", "منصة التقييم المهنية", "provider-assessment-demo/"),
    ("daily-tools", "الأدوات النفسية التفاعلية", "daily-tools/"),
    ("learning-paths", "مسارات تعلم الصحة النفسية", "learning-paths/"),
    ("start-here", "ابدأ من هنا", "start-here/"),
    ("family", "الصحة النفسية للأسرة", "sectors/family/"),
    ("child", "الصحة النفسية للطفل", "sectors/child/"),
    ("home", "الصحة النفسية في الحياة اليومية", "sectors/home/"),
    ("guided-assessment", "الاستكشاف الموجّه", "guided-assessment/"),
    ("library", "المكتبة الأكاديمية العربية", "library/"),
    ("comparisons", "المقارنات المنهجية", "comparisons/"),
    ("journeys", "مسارات الاستخدام", "journeys/"),
    ("decisions", "أدلة اتخاذ القرار", "decisions/"),
)


class VerifiedApiError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VerifiedApiError(f"Expected a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def route_from_url(url: str) -> str:
    if not url.startswith(BASE_URL):
        raise VerifiedApiError(f"Section URL escaped the public base: {url}")
    parsed = urllib.parse.urlparse(url)
    if parsed.query or parsed.fragment:
        raise VerifiedApiError(f"Section URL must not contain query or fragment: {url}")
    route = parsed.path.removeprefix("/pterminology-site/").strip("/")
    if not route or any(part in {".", ".."} for part in route.split("/")):
        raise VerifiedApiError(f"Invalid section route: {url}")
    return route + "/"


def verify_html_route(site: Path, route: str) -> dict[str, Any]:
    page = site / route / "index.html"
    if not page.is_file():
        raise VerifiedApiError(f"Published section route is missing: {route}")
    text = page.read_text(encoding="utf-8")
    required = ('<html', '<title>', '<h1', 'rel="canonical"')
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise VerifiedApiError(f"Section route {route} lacks institutional HTML markers: {missing}")
    return {
        "route": route,
        "page": page.relative_to(site).as_posix(),
        "bytes": page.stat().st_size,
    }


def register_developers_sitemap(site: Path) -> None:
    child = site / "sitemap-developers.xml"
    parent = site / "sitemap.xml"
    if not child.is_file() or not parent.is_file():
        raise VerifiedApiError("Developer sitemap integration inputs are missing")
    target = BASE_URL + "sitemap-developers.xml"
    tree = ET.parse(parent)
    root = tree.getroot()
    local = root.tag.rsplit("}", 1)[-1]
    namespace = root.tag.split("}", 1)[0] + "}" if root.tag.startswith("{") else ""
    if local == "sitemapindex":
        existing = {
            (node.text or "").strip()
            for node in root.findall("{*}sitemap/{*}loc")
            if node.text
        }
        if target not in existing:
            sitemap = ET.SubElement(root, namespace + "sitemap")
            ET.SubElement(sitemap, namespace + "loc").text = target
    elif local == "urlset":
        child_root = ET.parse(child).getroot()
        existing = {
            (node.text or "").strip()
            for node in root.findall("{*}url/{*}loc")
            if node.text
        }
        for location in child_root.findall("{*}url/{*}loc"):
            url = (location.text or "").strip()
            if not url or url in existing:
                continue
            item = ET.SubElement(root, namespace + "url")
            ET.SubElement(item, namespace + "loc").text = url
            existing.add(url)
    else:
        raise VerifiedApiError(f"Unsupported main sitemap type: {local}")
    tree.write(parent, encoding="utf-8", xml_declaration=True)


def verify_and_expand_sections(site: Path) -> dict[str, Any]:
    sections_path = site / "api" / "v1" / "sections.json"
    payload = read_json(sections_path)
    sections = payload.get("sections")
    if not isinstance(sections, list):
        raise VerifiedApiError("sections.json must contain a sections list")

    ids: set[str] = set()
    urls: set[str] = set()
    verified: list[dict[str, Any]] = []
    for item in sections:
        if not isinstance(item, dict):
            raise VerifiedApiError("Each section must be an object")
        section_id = str(item.get("id") or "")
        url = str(item.get("url") or "")
        if not section_id or section_id in ids or not url or url in urls:
            raise VerifiedApiError("Section identifiers and URLs must be unique and non-empty")
        ids.add(section_id)
        urls.add(url)
        verified.append(verify_html_route(site, route_from_url(url)))

    missing_core = CORE_SECTION_IDS - ids
    if missing_core:
        raise VerifiedApiError(f"Core API sections are missing: {sorted(missing_core)}")

    optional_added: list[str] = []
    for section_id, name_ar, route in OPTIONAL_SECTIONS:
        page = site / route / "index.html"
        if not page.is_file() or section_id in ids:
            continue
        verification = verify_html_route(site, route)
        item = {
            "id": section_id,
            "name_ar": name_ar,
            "url": BASE_URL + route,
        }
        sections.append(item)
        ids.add(section_id)
        urls.add(item["url"])
        verified.append(verification)
        optional_added.append(section_id)

    payload.update(
        {
            "contract_version": CONTRACT_VERSION,
            "count": len(sections),
            "sections": sections,
            "all_routes_verified": True,
            "verified_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
    )
    write_json(sections_path, payload)

    site_path = site / "api" / "v1" / "site.json"
    site_payload = read_json(site_path)
    site_payload["sections_endpoint"] = BASE_URL + "api/v1/sections.json"
    site_payload["verified_section_count"] = len(sections)
    site_payload["section_route_contract"] = CONTRACT_VERSION
    write_json(site_path, site_payload)

    return {
        "contract_version": CONTRACT_VERSION,
        "sections": len(sections),
        "core_sections": len(CORE_SECTION_IDS),
        "optional_sections_added": optional_added,
        "verified_routes": verified,
        "all_routes_verified": True,
    }


def publish_verified(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise VerifiedApiError(f"Missing site output: {site}")
    imported = ROOT / ".build" / "authorized-courses-v215.json"
    import_report = importer.import_courses(importer.DEFAULT_MANIFEST, imported)
    api_report = api_publisher.publish(
        site=site,
        manifest_path=importer.DEFAULT_MANIFEST,
        import_path=imported,
    )
    section_report = verify_and_expand_sections(site)
    register_developers_sitemap(site)
    report = {
        **api_report,
        "verification_contract_version": CONTRACT_VERSION,
        "course_import_status": import_report["status"],
        "sources_processed": import_report["sources_processed"],
        "courses_imported": len(import_report["courses"]),
        **section_report,
        "developers_sitemap_registered": True,
    }
    report_path = ROOT / ".build" / "reports" / "verified-public-api-v220.json"
    write_json(report_path, report)
    return report


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    print(json.dumps(publish_verified(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
