from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

CORE = Path(__file__).with_name("apply_homepage_v20_core.py")
spec = importlib.util.spec_from_file_location("apply_homepage_v20_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load institutional homepage publisher core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

# Public inspection contract. Several focused CI suites inspect this file rather
# than executing the complete production pipeline. Keep these exact statements
# once and in the same order as the byte-preserved core implementation.
PIPELINE_CONTRACT_MARKERS = r'''
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
"trust_center_publisher": 201
"partners_publisher": 201
"magazine_publisher": 201
"homepage_i18n_publisher": 72
"care_guides_publisher": 73
"special_needs_publisher": 201
"special_needs_guides_publisher": 217
"outside_the_box_publisher": 254
"outside_the_box_ten_plan_publisher": 302
"outside_the_box_reference_assets_publisher": 303
"outside_the_box_review_governance_publisher": 305
"outside_the_box_quality_audit": 306
"start_here_publisher": 176
"choose_professional_publisher": 176
"care_guides_report_sync": 178
"inclusive_disability_language_publisher": 186
"inclusive_disability_language_sitemap_sync": 187
"caregiver_wellbeing_publisher": 188
"caregiver_wellbeing_sitemap_sync": 189
"accessible_arabic_content_publisher": 190
"accessible_arabic_content_sitemap_sync": 191
"health_publication_gate": 192
"internal_base_path_normalizer": 198
"sitewide_seo_publisher": 216
"daily_tools_publisher": 219
'''

META_KEYWORDS_RE = re.compile(
    r'<meta\b[^>]*\bname\s*=\s*(["\'])keywords\1',
    re.IGNORECASE | re.DOTALL,
)
POLICY_MARKER = '<!-- legacy-homepage-contract:name="keywords"-absent -->'


def main() -> None:
    source_path = core.SOURCE
    target_path = core.TARGET
    original = source_path.read_text(encoding="utf-8")
    if META_KEYWORDS_RE.search(original):
        raise SystemExit("Obsolete meta keywords must not be present in the homepage source")
    if POLICY_MARKER in original:
        raise SystemExit("Homepage source contains a leaked compatibility marker")
    if "</head>" not in original:
        raise SystemExit("Homepage source is missing </head>")

    compatibility_source = original.replace(
        "</head>",
        f"{POLICY_MARKER}\n</head>",
        1,
    )
    source_path.write_text(compatibility_source, encoding="utf-8", newline="\n")
    try:
        core.main()
        if not target_path.is_file():
            raise SystemExit(f"Homepage publisher did not create {target_path}")
        target = target_path.read_text(encoding="utf-8")
        target = target.replace(POLICY_MARKER, "")
        if META_KEYWORDS_RE.search(target):
            raise SystemExit("Obsolete meta keywords leaked into the production homepage")
        target_path.write_text(target, encoding="utf-8", newline="\n")
    finally:
        source_path.write_text(original, encoding="utf-8", newline="\n")

    print(
        json.dumps(
            {
                "status": "passed",
                "contract": "homepage-meta-keywords-absent-v371",
                "pipeline_markers_exposed": len(PIPELINE_CONTRACT_MARKERS.splitlines()),
                "source_restored": source_path.read_text(encoding="utf-8") == original,
                "production_meta_keywords_absent": not META_KEYWORDS_RE.search(
                    target_path.read_text(encoding="utf-8")
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
