from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import care_guides_catalog_v246 as catalog
import care_guides_wave_v404 as wave
import publish_care_guides_v246 as implementation


def test_wave_005_has_exactly_fifty_unique_topics():
    topics = wave.topics()
    assert len(topics) == 50
    assert len({topic[0] for topic in topics}) == 50
    assert len({topic[1] for topic in topics}) == 50
    assert all(len(topic) == 9 for topic in topics)


def test_wave_005_uses_supported_categories_and_sources():
    supported_categories = set(catalog.CATEGORY_LABELS)
    supported_sources = set(catalog.SOURCES)
    for topic in wave.topics():
        assert topic[2] in supported_categories
        assert topic[8] in supported_sources


def test_wave_005_does_not_collide_with_previous_catalog():
    existing = catalog.institutional_guides()
    existing_slugs = {guide["slug"] for guide in existing}
    existing_titles = {guide["title"] for guide in existing}
    assert not ({topic[0] for topic in wave.topics()} & existing_slugs)
    assert not ({topic[1] for topic in wave.topics()} & existing_titles)


def test_wave_005_installs_full_contract():
    report = wave.install(implementation)
    assert report["added_guides"] == 50
    assert report["cumulative_wave_guides"] == 250
    assert report["expected_institutional_guides"] == 337
    assert report["expected_source_guides"] == 351
    assert report["minimum_published_guides"] == 350
    assert report["unique_slugs"] == 50
    assert report["unique_titles"] == 50
    assert report["minimum_sources"] >= 3
    assert report["specialist_review_claimed"] is False
    assert catalog.EXPECTED_GUIDES == 337
    assert len(catalog.institutional_guides()) == 337


def test_wave_005_topics_have_substantive_fields():
    for topic in wave.topics():
        slug, title, category, summary, signals, first_step, avoid, plan, source_key = topic
        assert len(slug) >= 12
        assert len(title) >= 18
        assert len(summary) >= 80
        assert len(signals.split("|")) >= 3
        assert len(first_step) >= 45
        assert len(avoid) >= 45
        assert len(plan) >= 50
        assert category
        assert source_key
