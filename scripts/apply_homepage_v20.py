from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
SOURCE = ROOT / "index.html"
TARGET = SITE / "index.html"
LAB_TOOL_COUNT = 93
BASE_URL = "https://healthrenewal.org/"


def run_publisher(script: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), str(SITE)],
        check=True,
    )


def restore_static_route(route: str) -> int:
    source = ROOT / route
    target = SITE / route
    if not source.is_dir():
        raise SystemExit(f"Missing repository static route: {route}")
    shutil.copytree(source, target, dirs_exist_ok=True)
    pages = list(target.rglob("*.html"))
    if not pages:
        raise SystemExit(f"Restored static route has no HTML pages: {route}")
    return len(pages)


def restore_static_tree(route: str) -> int:
    source = ROOT / route
    target = SITE / route
    if not source.is_dir():
        raise SystemExit(f"Missing repository static tree: {route}")
    shutil.copytree(source, target, dirs_exist_ok=True)
    files = [path for path in target.rglob("*") if path.is_file()]
    if not files:
        raise SystemExit(f"Restored static tree is empty: {route}")
    return len(files)


def restore_static_file(relative_path: str) -> None:
    source = ROOT / relative_path
    target = SITE / relative_path
    if not source.is_file():
        raise SystemExit(f"Missing repository static file: {relative_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def synchronize_homepage_lab_inventory(text: str) -> str:
    pattern = re.compile(
        r'(<article class="stat"><strong>)[\d,]+'
        r'(</strong><span>مقياسًا وأداة وقدرة معرفية[^<]*</span></article>)'
    )
    text, count = pattern.subn(rf"\g<1>{LAB_TOOL_COUNT}\g<2>", text, count=1)
    if count != 1:
        raise SystemExit("Homepage laboratory inventory card is missing or ambiguous")
    return text


def synchronize_care_guides_report() -> None:
    report_path = SITE / "api" / "care-guides-v21.json"
    sitemap_path = SITE / "sitemap-care-guides.xml"
    guide_root = SITE / "care-guides"
    expected_page = guide_root / "choosing-mental-health-professional" / "index.html"
    expected_url = BASE_URL + "care-guides/choosing-mental-health-professional/"

    if not report_path.is_file():
        raise SystemExit("Missing care-guides-v21.json after guide publication")
    if not sitemap_path.is_file() or not expected_page.is_file():
        raise SystemExit("Choosing-professional guide or care-guide sitemap is missing")

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(sitemap_path).getroot()
    urls = [node.text for node in root.findall("sm:url/sm:loc", namespace) if node.text]
    if expected_url not in urls:
        raise SystemExit("Choosing-professional guide is absent from care-guide sitemap")
    if len(urls) != len(set(urls)):
        raise SystemExit("Duplicate URLs detected in care-guide sitemap")

    html_pages = sorted(guide_root.rglob("index.html"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["version"] = 178
    report["guides"] = max(int(report.get("guides", 0)), len(urls) - 1)
    report["pages"] = len(html_pages)
    report["sitemap_urls"] = len(urls)
    report["choosing_professional_guide"] = True
    report["choosing_professional_route"] = expected_url
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def register_sitemap(sitemap_name: str) -> None:
    sitemap_path = SITE / sitemap_name
    sitemap_index = SITE / "sitemap.xml"
    if not sitemap_path.is_file() or not sitemap_index.is_file():
        raise SystemExit(f"Missing sitemap integration input: {sitemap_name}")

    target = BASE_URL + sitemap_name
    tree = ET.parse(sitemap_index)
    root = tree.getroot()
    root_type = local_name(root.tag)

    if root_type == "sitemapindex":
        existing = [
            (node.text or "").strip()
            for node in root.findall("{*}sitemap/{*}loc")
        ]
        if target not in existing:
            sitemap = ET.SubElement(root, qualify(root, "sitemap"))
            ET.SubElement(sitemap, qualify(root, "loc")).text = target
    elif root_type == "urlset":
        child_root = ET.parse(sitemap_path).getroot()
        child_urls = [
            (node.text or "").strip()
            for node in child_root.findall("{*}url/{*}loc")
            if node.text and node.text.strip()
        ]
        existing = {
            (node.text or "").strip()
            for node in root.findall("{*}url/{*}loc")
            if node.text and node.text.strip()
        }
        for url in child_urls:
            if url in existing:
                continue
            item = ET.SubElement(root, qualify(root, "url"))
            ET.SubElement(item, qualify(root, "loc")).text = url
            existing.add(url)
    else:
        raise SystemExit(
            f"Unsupported sitemap root while registering {sitemap_name}: {root_type}"
        )

    tree.write(sitemap_index, encoding="utf-8", xml_declaration=True)


def publish_api_sitemap() -> None:
    sitemap = SITE / "sitemap-api.xml"
    sitemap.write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{BASE_URL}api/</loc><lastmod>2026-07-25</lastmod>"
        "<changefreq>monthly</changefreq><priority>0.7</priority></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    register_sitemap("sitemap-api.xml")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit("Missing source homepage index.html")
    if not SITE.exists():
        raise SystemExit(f"Missing site output: {SITE}")

    source_text = SOURCE.read_text(encoding="utf-8")
    text = synchronize_homepage_lab_inventory(source_text)
    required = [
        '<html lang="ar" dir="rtl">',
        '<h1>',
        'href="encyclopedia/"',
        'href="tips/"',
        'href="assessment-lab/"',
        'href="cognitive-lab/"',
        'href="sectors/family/"',
        'href="sectors/child/"',
        'href="sectors/home/"',
        'href="special-needs/"',
        'href="care-guides/"',
        'href="api/"',
        'rel="manifest"',
        'rel="icon"',
        'rel="search"',
        'property="og:image"',
        'name="twitter:image"',
        'application/ld+json',
        'color-scheme" content="light"',
        'منصة الصحة النفسية وذوي الاحتياجات الخاصة',
        'معرفة تحترم الإنسان. دعم يوسّع الإمكانات.',
        f'<strong>{LAB_TOOL_COUNT}</strong><span>مقياسًا وأداة وقدرة معرفية',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Homepage source missing required markers: {missing}")

    forbidden = [
        'background:linear-gradient(145deg,var(--navy),var(--navy2))',
        'background:#071827',
        'background:#000',
        'background:black',
        'خطة نمو قابلة للقياس',
        'الأهداف الدنيا للمحتوى',
        'هدف معلن للموسوعة النفسية العربية',
        'هدف أدنى لكل مسار رئيسي',
        'هدف توسع',
        'خط أساس المصدر الحالي',
        'يُحسب العدد من حزمة الإنتاج',
        'مسار مستقبلي للحسابات المؤسسية',
        'ما سيتم إنجازه',
        'لا نشر قبل البوابات',
        'built-not-published',
        'قيد الإعداد',
        'قيد التوسع',
    ]
    found = [item for item in forbidden if item in text]
    if found:
        raise SystemExit(f"Homepage regression or operational copy detected: {found}")

    h1_count = len(re.findall(r'<h1\b', text))
    h2_count = len(re.findall(r'<h2\b', text))
    h3_count = len(re.findall(r'<h3\b', text))
    if h1_count != 1:
        raise SystemExit(f"Expected exactly one H1, found {h1_count}")
    if h2_count < 4:
        raise SystemExit("Homepage must contain at least four H2 sections")
    if h3_count < 16:
        raise SystemExit("Homepage must contain at least sixteen H3 cards")

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8")
    restored_routes = {
        "provider-assessment-demo": restore_static_route("provider-assessment-demo"),
        "brand_assets": restore_static_tree("assets/brand"),
        "api_v1": restore_static_tree("api/v1"),
    }
    for relative_path in ("api/index.html", "manifest.webmanifest", "opensearch.xml"):
        restore_static_file(relative_path)

    expected_target_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    report = {
        "version": 219,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "source_transformed": True,
        "lab_tool_count": LAB_TOOL_COUNT,
        "lab_inventory_updated": True,
        "lab_inventory_metadata_updated": True,
        "h1": h1_count,
        "h2": h2_count,
        "h3": h3_count,
        "brand": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
        "founding_name": "مصطلحات علم النفس",
        "slogan": "معرفة تحترم الإنسان. دعم يوسّع الإمكانات.",
        "target_counts_are_labeled": False,
        "production_counts_are_contextualized": True,
        "operational_copy_hidden": True,
        "public_api_publisher": 215,
        "authorized_course_importer": 215,
        "course_security_contract": 218,
        "course_permission_policy": "deny-by-default",
        "content_discovery_publisher": 219,
        "special_needs_guides_publisher": 217,
        "outside_the_box_publisher": 254,
        "outside_the_box_ten_plan_publisher": 302,
        "outside_the_box_reference_assets_publisher": 303,
        "outside_the_box_review_governance_publisher": 305,
        "outside_the_box_quality_audit": 306,
        "light_palette": True,
        "core_sections_linked": True,
        "api_v1_published": True,
        "brand_assets_published": True,
        "restored_static_routes": restored_routes,
        "trust_center_publisher": 201,
        "partners_publisher": 201,
        "magazine_publisher": 201,
        "homepage_i18n_publisher": 72,
        "care_guides_publisher": 73,
        "special_needs_publisher": 201,
        "start_here_publisher": 176,
        "choose_professional_publisher": 176,
        "care_guides_report_sync": 178,
        "inclusive_disability_language_publisher": 186,
        "inclusive_disability_language_sitemap_sync": 187,
        "caregiver_wellbeing_publisher": 188,
        "caregiver_wellbeing_sitemap_sync": 189,
        "accessible_arabic_content_publisher": 190,
        "accessible_arabic_content_sitemap_sync": 191,
        "health_publication_gate": 192,
        "internal_base_path_normalizer": 198,
        "cognitive_lab_inventory_publisher": 210,
        "sitewide_seo_publisher": 216,
        "daily_tools_publisher": 219,
    }
    if report["target_sha256"] != expected_target_sha:
        raise SystemExit("Homepage transformed output hash mismatch")

    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "homepage-v20.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run_publisher("publish_trust_center_v201.py")
    run_publisher("finalize_trust_center_links_v71.py")
    run_publisher("publish_partners_v201.py")
    run_publisher("publish_magazine_v201.py")

    run_publisher("import_authorized_courses_v215.py")
    run_publisher("publish_public_api_v215.py")
    register_sitemap("sitemap-developers.xml")
    run_publisher("prepare_content_discovery_v219.py")
    register_sitemap("sitemap-content-discovery.xml")

    run_publisher("publish_care_guides_v21.py")
    run_publisher("link_care_guides_v201.py")

    run_publisher("publish_special_needs_v73.py")
    run_publisher("publish_special_needs_guides_v217.py")
    run_publisher("publish_youth_sector_v353.py")
    run_publisher("publish_outside_the_box_v254.py")
    run_publisher("publish_outside_the_box_ten_plans_v302.py")
    restore_static_route("outside-the-box/evidence-standard")
    run_publisher("publish_outside_the_box_reference_assets_v303.py")
    run_publisher("publish_outside_the_box_review_governance_v305.py")
    run_publisher("audit_outside_the_box_quality_v306.py")
    run_publisher("publish_choose_professional_v176.py")
    synchronize_care_guides_report()
    run_publisher("publish_homepage_i18n_v72.py")
    run_publisher("publish_start_here_v176.py")
    run_publisher("publish_inclusive_disability_language_v186.py")
    register_sitemap("sitemap-inclusive-disability-language.xml")
    run_publisher("publish_caregiver_wellbeing_v188.py")
    register_sitemap("sitemap-caregiver-wellbeing.xml")
    run_publisher("publish_accessible_arabic_content_v190.py")
    register_sitemap("sitemap-accessible-arabic-content.xml")
    run_publisher("publish_daily_tools_v24.py")
    publish_api_sitemap()
    run_publisher("enhance_sitewide_seo_v216.py")
    run_publisher("publish_content_catalog_v219.py")
    run_publisher("verify_sitewide_seo_v216.py")
    run_publisher("enforce_health_publication_gate_v192.py")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()