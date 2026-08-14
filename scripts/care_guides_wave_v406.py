from __future__ import annotations
from collections import Counter
import care_guides_catalog_v246 as catalog
import care_guides_wave_v405 as previous_wave
from care_guides_sources_v246 import SOURCES
from care_guides_topics_v406 import TOPICS as RAW_TOPICS

VERSION=406
RELEASE_DATE="2026-08-14"
WAVE=7
EXPECTED_WAVE_GUIDES=50
EXPECTED_INSTITUTIONAL_GUIDES=437
EXPECTED_SOURCE_GUIDES=451
MINIMUM_PUBLISHED_GUIDES=450
TARGET_TOTAL_PAGES=10000
EXCLUDED_SLUGS={"family-quiet-hour-agreement","work-document-version-control-card","older-adult-photo-memory-organization-guide"}
CATEGORY_MAP={"developmental":"education","learning":"education","access":"access","communication":"family","services":"professionals","rights":"professionals","work":"work","caregiving":"caregivers","older":"older-adults"}

def topics():
    values=[x for x in RAW_TOPICS if x[0] not in EXCLUDED_SLUGS]
    if len(values)!=EXPECTED_WAVE_GUIDES: raise RuntimeError(f"Expected {EXPECTED_WAVE_GUIDES} wave topics, found {len(values)}")
    if any(len(x)!=9 for x in values): raise RuntimeError("Every wave topic must preserve the v246 nine-column contract")
    if len({x[0] for x in values})!=50 or len({x[1] for x in values})!=50: raise RuntimeError("Wave 007 contains duplicate slugs or titles")
    missing_sources=sorted({x[8] for x in values if x[8] not in SOURCES})
    if missing_sources: raise RuntimeError(f"Wave 007 uses unsupported source keys: {missing_sources}")
    return values

def normalized_topics():
    return [(slug,title,CATEGORY_MAP.get(category,category),summary,signals,first_step,avoid,plan,source_key) for slug,title,category,summary,signals,first_step,avoid,plan,source_key in topics()]

def install(implementation):
    if getattr(implementation,"_care_guides_wave_v406_installed",False): return implementation._care_guides_wave_v406_report
    previous_wave.install(implementation)
    additions=normalized_topics(); existing=catalog.institutional_guides(); existing_slugs={g["slug"] for g in existing}; existing_titles={g["title"] for g in existing}
    collisions=[x[0] for x in additions if x[0] in existing_slugs]; title_collisions=[x[1] for x in additions if x[1] in existing_titles]
    if collisions or title_collisions: raise RuntimeError(f"Wave 007 collides with existing guides: {collisions} {title_collisions}")
    catalog.TOPICS_4=[*catalog.TOPICS_4,*additions]; catalog.EXPECTED_GUIDES=EXPECTED_INSTITUTIONAL_GUIDES; catalog.CATALOG_VERSION=VERSION; catalog.RELEASE_DATE=RELEASE_DATE
    implementation.EXPECTED_INSTITUTIONAL_GUIDES=EXPECTED_INSTITUTIONAL_GUIDES; implementation.EXPECTED_SOURCE_GUIDES=EXPECTED_SOURCE_GUIDES; implementation.MINIMUM_PUBLISHED_GUIDES=MINIMUM_PUBLISHED_GUIDES; implementation.CONTENT_RELEASE_VERSION=VERSION; implementation.RELEASE_DATE=RELEASE_DATE
    generated=catalog.institutional_guides(); wave_slugs={x[0] for x in additions}; wave_guides=[g for g in generated if g["slug"] in wave_slugs]
    if len(wave_guides)!=50: raise RuntimeError("Wave 007 did not generate exactly 50 guides")
    report={"version":VERSION,"wave":WAVE,"target_total_pages":TARGET_TOTAL_PAGES,"added_guides":50,"cumulative_wave_guides":350,"expected_institutional_guides":EXPECTED_INSTITUTIONAL_GUIDES,"expected_source_guides":EXPECTED_SOURCE_GUIDES,"minimum_published_guides":MINIMUM_PUBLISHED_GUIDES,"unique_slugs":len({g["slug"] for g in wave_guides}),"unique_titles":len({g["title"] for g in wave_guides}),"minimum_sources":min(len(g.get("sources",[])) for g in wave_guides),"category_distribution":dict(sorted(Counter(g["category"] for g in wave_guides).items())),"excluded_candidates":sorted(EXCLUDED_SLUGS),"specialist_review_claimed":False}
    implementation._care_guides_wave_v406_installed=True; implementation._care_guides_wave_v406_report=report
    return report
