from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SCRIPTS=ROOT/"scripts"
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))
import care_guides_catalog_v246 as catalog
import care_guides_wave_v408 as wave
import publish_care_guides_v246 as implementation
from care_guides_sources_v246 import SOURCES

def test_wave_009_has_exactly_fifty_unique_topics():
    topics=wave.topics(); assert len(topics)==50; assert len({x[0] for x in topics})==50; assert len({x[1] for x in topics})==50; assert all(len(x)==9 for x in topics)

def test_wave_009_uses_supported_sources_and_categories():
    assert all(x[8] in SOURCES for x in wave.topics())
    normalized=wave.normalized_topics(); allowed=set(catalog.CATEGORIES)
    assert all(x[2] in allowed for x in normalized)

def test_wave_009_does_not_collide_with_previous_catalog():
    existing=catalog.institutional_guides(); slugs={g["slug"] for g in existing}; titles={g["title"] for g in existing}
    assert not ({x[0] for x in wave.normalized_topics()} & slugs); assert not ({x[1] for x in wave.normalized_topics()} & titles)

def test_wave_009_installs_full_contract():
    report=wave.install(implementation)
    assert report["added_guides"]==50; assert report["cumulative_wave_guides"]==450; assert report["expected_institutional_guides"]==537; assert report["expected_source_guides"]==551; assert report["minimum_published_guides"]==550; assert report["unique_slugs"]==50; assert report["unique_titles"]==50; assert report["minimum_sources"]>=2; assert report["specialist_review_claimed"] is False; assert catalog.EXPECTED_GUIDES==537; assert len(catalog.institutional_guides())==537

def test_wave_009_topics_have_substantive_fields():
    for topic in wave.topics():
        slug,title,category,summary,signals,first_step,avoid,plan,source_key=topic
        assert len(slug)>=12; assert len(title)>=18; assert len(summary)>=80; assert len(signals.split("|"))>=3; assert len(first_step)>=45; assert len(avoid)>=45; assert len(plan)>=50; assert category; assert source_key
