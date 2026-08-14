from __future__ import annotations

from collections import Counter

import care_guides_catalog_v246 as catalog
import care_guides_wave_v403 as previous_wave
from care_guides_topics_v404_1 import TOPICS as TOPICS_1
from care_guides_topics_v404_2 import TOPICS as TOPICS_2
from care_guides_topics_v404_3 import TOPICS as TOPICS_3
from care_guides_topics_v404_4 import TOPICS as TOPICS_4
from care_guides_topics_v404_5 import TOPICS as TOPICS_5

VERSION = 404
RELEASE_DATE = "2026-08-14"
WAVE = 5
EXPECTED_WAVE_GUIDES = 50
EXPECTED_INSTITUTIONAL_GUIDES = 337
EXPECTED_SOURCE_GUIDES = 351
MINIMUM_PUBLISHED_GUIDES = 350
TARGET_TOTAL_PAGES = 10000


def _normalize(topic: tuple[str, ...], group: int) -> tuple[str, ...]:
    slug, title, _category, summary, signals, first_step, avoid, plan, _source_key = topic
    category_by_group = {1: "daily", 2: "daily", 3: "services", 4: "services", 5: "daily"}
    source_by_group = {1: "rights", 2: "access", 3: "access", 4: "services", 5: "access"}
    return (
        slug,
        title,
        category_by_group[group],
        summary,
        signals,
        first_step,
        avoid,
        plan,
        source_by_group[group],
    )


def topics() -> list[tuple[str, ...]]:
    values = [
        *[_normalize(topic, 1) for topic in TOPICS_1],
        *[_normalize(topic, 2) for topic in TOPICS_2],
        *[_normalize(topic, 3) for topic in TOPICS_3],
        *[_normalize(topic, 4) for topic in TOPICS_4],
        *[_normalize(topic, 5) for topic in TOPICS_5],
    ]
    if len(values) != EXPECTED_WAVE_GUIDES:
        raise RuntimeError(f"Expected {EXPECTED_WAVE_GUIDES} wave topics, found {len(values)}")
    if any(len(topic) != 9 for topic in values):
        raise RuntimeError("Every wave topic must preserve the v246 nine-column contract")
    slugs = [topic[0] for topic in values]
    titles = [topic[1] for topic in values]
    if len(slugs) != len(set(slugs)) or len(titles) != len(set(titles)):
        raise RuntimeError("Wave 005 contains duplicate slugs or titles")
    return values


def install(implementation: object) -> dict[str, object]:
    if getattr(implementation, "_care_guides_wave_v404_installed", False):
        return getattr(implementation, "_care_guides_wave_v404_report")

    previous_wave.install(implementation)
    additions = topics()
    existing = catalog.institutional_guides()
    existing_slugs = {guide["slug"] for guide in existing}
    existing_titles = {guide["title"] for guide in existing}
    collisions = [topic[0] for topic in additions if topic[0] in existing_slugs]
    title_collisions = [topic[1] for topic in additions if topic[1] in existing_titles]
    if collisions or title_collisions:
        raise RuntimeError(f"Wave 005 collides with existing guides: {collisions} {title_collisions}")

    catalog.TOPICS_4 = [*catalog.TOPICS_4, *additions]
    catalog.EXPECTED_GUIDES = EXPECTED_INSTITUTIONAL_GUIDES
    catalog.CATALOG_VERSION = VERSION
    catalog.RELEASE_DATE = RELEASE_DATE

    implementation.EXPECTED_INSTITUTIONAL_GUIDES = EXPECTED_INSTITUTIONAL_GUIDES
    implementation.EXPECTED_SOURCE_GUIDES = EXPECTED_SOURCE_GUIDES
    implementation.MINIMUM_PUBLISHED_GUIDES = MINIMUM_PUBLISHED_GUIDES
    implementation.CONTENT_RELEASE_VERSION = VERSION
    implementation.RELEASE_DATE = RELEASE_DATE

    generated = catalog.institutional_guides()
    wave_slugs = {topic[0] for topic in additions}
    wave_guides = [guide for guide in generated if guide["slug"] in wave_slugs]
    if len(wave_guides) != EXPECTED_WAVE_GUIDES:
        raise RuntimeError("Wave 005 did not generate exactly 50 guides")

    report = {
        "version": VERSION,
        "wave": WAVE,
        "target_total_pages": TARGET_TOTAL_PAGES,
        "added_guides": EXPECTED_WAVE_GUIDES,
        "cumulative_wave_guides": 250,
        "expected_institutional_guides": EXPECTED_INSTITUTIONAL_GUIDES,
        "expected_source_guides": EXPECTED_SOURCE_GUIDES,
        "minimum_published_guides": MINIMUM_PUBLISHED_GUIDES,
        "unique_slugs": len({guide["slug"] for guide in wave_guides}),
        "unique_titles": len({guide["title"] for guide in wave_guides}),
        "minimum_sources": min(len(guide.get("sources", [])) for guide in wave_guides),
        "category_distribution": dict(sorted(Counter(guide["category"] for guide in wave_guides).items())),
        "specialist_review_claimed": False,
    }
    implementation._care_guides_wave_v404_installed = True
    implementation._care_guides_wave_v404_report = report
    return report
