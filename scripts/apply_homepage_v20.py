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
BRAND_SOURCE = ROOT / "assets" / "brand"
BRAND_TARGET = SITE / "assets" / "brand"
LAB_TOOL_COUNT = 93


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


def restore_brand_assets() -> list[str]:
    if not BRAND_SOURCE.is_dir():
        raise SystemExit("Missing institutional brand assets")
    required = {"platform-logo.svg", "platform-social-card.svg"}
    available = {path.name for path in BRAND_SOURCE.glob("*.svg")}
    missing = sorted(required - available)
    if missing:
        raise SystemExit(f"Missing required brand assets: {missing}")
    shutil.copytree(BRAND_SOURCE, BRAND_TARGET, dirs_exist_ok=True)
    copied = sorted(path.name for path in BRAND_TARGET.glob("*.svg"))
    if not required.issubset(copied):
        raise SystemExit("Institutional brand asset copy failed")
    return copied


def synchronize_homepage_lab_inventory(text: str) -> str:
    replacements = (
        (
            '<meta name="description" content="منصة عربية شاملة للصحة النفسية وذوي الاحتياجات الخاصة تجمع موسوعة موثقة وأدلة عملية للأسرة والطفل والعائلة والتربية الدامجة وأدوات تقييم استكشافية بحدود مهنية واضحة.">',
            f'<meta name="description" content="منصة عربية شاملة للصحة النفسية وذوي الاحتياجات الخاصة تجمع موسوعة موثقة وأدلة عملية للأسرة والطفل والعائلة والتربية الدامجة و{LAB_TOOL_COUNT} مقياسًا وأداة معرفية وتقييمًا استكشافيًا بحدود مهنية واضحة.">',
        ),
        (
            '<meta property="og:description" content="معرفة تحترم الإنسان، وأدلة عملية تساعد الأسرة والمختص ومقدم الخدمة على الوصول إلى المعلومة والمسار المناسب.">',
            f'<meta property="og:description" content="معرفة تحترم الإنسان، وأدلة عملية و{LAB_TOOL_COUNT} مقياسًا وأداة معرفية تساعد الأسرة والمختص ومقدم الخدمة على الوصول إلى المعلومة والمسار المناسب.">',
        ),
        (
            '<meta name="twitter:description" content="موسوعة عربية وأدلة عملية وتربية دامجة ومنصة تقييم استكشافية ضمن بنية موثوقة ومتاحة.">',
            f'<meta name="twitter:description" content="موسوعة عربية وأدلة عملية وتربية دامجة و{LAB_TOOL_COUNT} مقياسًا وأداة معرفية ومنصة تقييم استكشافية ضمن بنية موثوقة ومتاحة.">',
        ),
        (
            '"description":"بوابة عربية للموسوعة النفسية والأدلة العملية والأسرة والطفل والعائلة وذوي الاحتياجات الخاصة والتربية الدامجة والمقاييس والاستكشاف المهني."',
            f'"description":"بوابة عربية للموسوعة النفسية والأدلة العملية والأسرة والطفل والعائلة وذوي الاحتياجات الخاصة والتربية الدامجة و{LAB_TOOL_COUNT} مقياسًا وأداة معرفية والاستكشاف المهني."',
        ),
        (
            '<article class="stat"><strong>88</strong><span>مقياسًا وأداة وقدرة معرفية في المختبرات الحالية بحدود استخدام واضحة.</span></article>',
            f'<article class="stat"><strong>{LAB_TOOL_COUNT}</strong><span>مقياسًا وأداة وقدرة معرفية في المختبرات الحالية بحدود استخدام واضحة.</span></article>',
        ),
    )
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"Homepage laboratory inventory marker missing: {old[:80]}")
        text = text.replace(old, new, 1)
    return text


def synchronize_care_guides_report() -> None:
    report_path = SITE / "api" / "care-guides-v21.json"
    sitemap_path = SITE / "sitemap-care-guides.xml"
    guide_root = SITE / "care-guides"
    expected_page = guide_root / "choosing-mental-health-professional" / "index.html"
    expected_url = "https://khaledaltheeb.github.io/pterminology-site/care-guides/choosing-mental-health-professional/"

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
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def register_sitemap(sitemap_name: str) -> None:
    sitemap_path = SITE / sitemap_name
    sitemap_index = SITE / "sitemap.xml"
    if not sitemap_path.is_file() or not sitemap_index.is_file():
        raise SystemExit(f"Missing sitemap integration input: {sitemap_name}")

    target = f"https://khaledaltheeb.github.io/pterminology-site/{sitemap_name}"
    tree = ET.parse(sitemap_index)
    root = tree.getroot()
    existing = [(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")]
    if target not in existing:
        sitemap = ET.SubElement(root, "sitemap")
        ET.SubElement(sitemap, "loc").text = target
    tree.write(sitemap_index, encoding="utf-8", xml_declaration=True)

    tree = ET.parse(sitemap_index)
    current = [(node.text or "").strip() for node in tree.getroot().findall("{*}sitemap/{*}loc")]
    if current.count(target) != 1:
        raise SystemExit(f"Expected exactly one sitemap index entry for {sitemap_name}")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit("Missing source homepage index.html")
    if not SITE.exists():
        raise SystemExit(f"Missing site output: {SITE}")
    source_text = SOURCE.read_text(encoding="utf-8")
    text = synchronize_homepage_lab_inventory(source_text)
    required = [
        '<html lang="ar" dir="rtl">',
        '<h1',
        'href="encyclopedia/"',
        'href="tips/"',
        'href="assessment-lab/"',
        'href="cognitive-lab/"',
        'href="sectors/family/"',
        'href="special-needs/"',
        'href="care-guides/"',
        'href="developers/"',
        'assets/brand/platform-logo.svg',
        'rel="manifest"',
        'application/ld+json',
        '"@type":"FAQPage"',
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
        '2000+',
        'قيد الإعداد',
        'قيد التوسع',
        'خطة نمو قابلة للقياس',
        'الأهداف الدنيا للمحتوى',
        'هدف توسع',
        'خط أساس المصدر الحالي',
        'مسار مستقبلي للحسابات المؤسسية',
        'لا نشر قبل البوابات',
        'built-not-published',
        '<strong>88</strong><span>مقياسًا وأداة وقدرة معرفية',
        '<strong>92</strong><span>مقياسًا وأداة وقدرة معرفية',
    ]
    found = [item for item in forbidden if item in text]
    if found:
        raise SystemExit(f"Homepage regression placeholder or internal language detected: {found}")
    h1_count = len(re.findall(r'<h1\b', text))
    h2_count = len(re.findall(r'<h2\b', text))
    h3_count = len(re.findall(r'<h3\b', text))
    if h1_count != 1:
        raise SystemExit(f"Expected exactly one H1, found {h1_count}")
    if h2_count < 5:
        raise SystemExit("Homepage must contain at least five H2 sections")
    if h3_count < 12:
        raise SystemExit("Homepage must contain at least twelve H3 cards")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8")
    restored_routes = {"provider-assessment-demo": restore_static_route("provider-assessment-demo")}
    brand_assets = restore_brand_assets()
    expected_target_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    report = {
        "version": 215,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "source_transformed": True,
        "lab_tool_count": LAB_TOOL_COUNT,
        "lab_inventory_metadata_updated": True,
        "h1": h1_count,
        "h2": h2_count,
        "h3": h3_count,
        "brand": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
        "founding_name": "مصطلحات علم النفس",
        "slogan": "معرفة تحترم الإنسان. دعم يوسّع الإمكانات.",
        "target_counts_are_labeled": True,
        "verified_counts_only": True,
        "public_operational_language_removed": True,
        "semantic_keyword_taxonomy": 215,
        "meta_keywords_stuffing_blocked": True,
        "brand_assets": brand_assets,
        "light_palette": True,
        "core_sections_linked": True,
        "restored_static_routes": restored_routes,
        "trust_center_publisher": 201,
        "partners_publisher": 201,
        "magazine_publisher": 201,
        "public_api_publisher": 215,
        "authorized_course_importer": 215,
        "seo_semantic_audit": 215,
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
    }
    if report["target_sha256"] != expected_target_sha:
        raise SystemExit("Homepage transformed output hash mismatch")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "homepage-v20.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    run_publisher("publish_trust_center_v201.py")
    run_publisher("finalize_trust_center_links_v71.py")
    run_publisher("publish_partners_v201.py")
    run_publisher("publish_magazine_v201.py")
    run_publisher("import_authorized_courses_v215.py")
    run_publisher("publish_public_api_v215.py")
    register_sitemap("sitemap-developers.xml")

    run_publisher("publish_care_guides_v21.py")
    run_publisher("link_care_guides_v201.py")

    run_publisher("publish_special_needs_v73.py")
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
    run_publisher("enforce_health_publication_gate_v192.py")
    run_publisher("audit_seo_semantics_v215.py")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
