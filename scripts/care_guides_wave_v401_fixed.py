from __future__ import annotations
import care_guides_wave_v401 as base
EXCLUDED_OVERLAP_SLUGS = {"weekly-personal-care-review-card"}

def topics():
    values = [topic for topic in base.TOPICS_1A + base.TOPICS_1B + base.TOPICS_1C + base.TOPICS_2 if topic[0] not in EXCLUDED_OVERLAP_SLUGS]
    if len(values) != base.EXPECTED_WAVE_GUIDES:
        raise RuntimeError(f"Expected {base.EXPECTED_WAVE_GUIDES} wave topics, found {len(values)}")
    return values

def install(implementation):
    original = base.topics
    base.topics = topics
    try:
        return base.install(implementation)
    finally:
        base.topics = original
