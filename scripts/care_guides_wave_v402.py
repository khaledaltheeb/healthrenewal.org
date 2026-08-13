from __future__ import annotations

from collections import Counter

import care_guides_catalog_v246 as catalog
import care_guides_wave_v401 as previous_wave
from care_guides_topics_v402_1 import TOPICS as TOPICS_1
from care_guides_topics_v402_2b import TOPICS as TOPICS_2
from care_guides_topics_v402_3 import TOPICS as TOPICS_3
from care_guides_topics_v402_4 import TOPICS as TOPICS_4
from care_guides_topics_v402_5a import TOPICS as TOPICS_5A
from care_guides_topics_v402_5b import TOPICS as TOPICS_5B

VERSION = 402
RELEASE_DATE = "2026-08-14"
WAVE = 3
EXPECTED_WAVE_GUIDES = 50
EXPECTED_INSTITUTIONAL_GUIDES = 237
EXPECTED_SOURCE_GUIDES = 251
MINIMUM_PUBLISHED_GUIDES = 250
TARGET_TOTAL_PAGES = 10000


def topics() -> list[tuple[str, ...]]:
    values = [*TOPICS_1, *TOPICS_2, *TOPICS_3, *TOPICS_4, *TOPICS_5A, *TOPICS_5B]
    if len(values) != EXPECTED_WAVE_GUIDES:
        raise RuntimeError(f"Expected {EXPECTED_WAVE_GUIDES} wave topics, found {len(values)}")
    if any(len(topic) != 9 for topic in values):
        raise RuntimeError("Every wave topic must preserve the v246 nine-column contract")
    slugs = [topic[0] for topic in values]
    titles = [topic[1] for topic in values]
    if len(slugs) != len(set(slugs)) or len(titles) != len(set(titles)):
        raise RuntimeError("Wave 003 contains duplicate slugs or titles")
    return values


def install(implementation: object) -> dict[str, object]:
    if getattr(implementation, "_care_guides_wave_v402_installed", False):
        return getattr(implementation, "_care_guides_wave_v402_report")

    previous_wave.install(implementation)
    additions = topics()
    existing = catalog.institutional_guides()
    existing_slugs = {guide["slug"] for guide in existing}
    existing_titles = {guide["title"] for guide in existing}
    collisions = [topic[0] for topic in additions if topic[0] in existing_slugs]
    title_collisions = [topic[1] for topic in additions if topic[1] in existing_titles]
    if collisions or title_collisions:
        raise RuntimeError(f"Wave 003 collides with existing guides: {collisions} {title_collisions}")

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
        raise RuntimeError("Wave 003 did not generate exactly 50 guides")

    report = {
        "version": VERSION,
        "wave": WAVE,
        "target_total_pages": TARGET_TOTAL_PAGES,
        "added_guides": EXPECTED_WAVE_GUIDES,
        "cumulative_wave_guides": 150,
        "expected_institutional_guides": EXPECTED_INSTITUTIONAL_GUIDES,
        "expected_source_guides": EXPECTED_SOURCE_GUIDES,
        "minimum_published_guides": MINIMUM_PUBLISHED_GUIDES,
        "unique_slugs": len({guide["slug"] for guide in wave_guides}),
        "unique_titles": len({guide["title"] for guide in wave_guides}),
        "minimum_sources": min(len(guide.get("sources", [])) for guide in wave_guides),
        "category_distribution": dict(sorted(Counter(guide["category"] for guide in wave_guides).items())),
        "specialist_review_claimed": False,
    }
    implementation._care_guides_wave_v402_installed = True
    implementation._care_guides_wave_v402_report = report
    return report
