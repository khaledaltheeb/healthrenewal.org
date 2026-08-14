from __future__ import annotations

import care_guides_catalog_v246 as catalog
import care_guides_wave_v401 as base

EXCLUDED_OVERLAP_SLUGS = {"weekly-personal-care-review-card"}

# Some Wave 002/003 specs used semantic labels in the source-bundle column that
# are not registered v246 source keys. Resolve those labels deliberately from
# the topic context instead of falling back to a generic bundle or allowing a
# late KeyError inside the catalog builder.
_SOURCE_BUNDLE_BY_CONTEXT = {
    ("family", "children"): "youth",
    ("family", "services"): "services",
    ("family", "addictions"): "substance",
    ("family", "crisis"): "crisis",
    ("family", "daily"): "services",
    ("family", "neurodevelopment"): "developmental",
    ("caregiver", "older"): "dementia",
    ("caregiver", "services"): "chronic",
    ("therapy", "services"): "services",
    ("selfcare", "services"): "services",
    ("nutrition", "older"): "dementia",
    ("nutrition", "children"): "developmental",
    ("safety", "older"): "wandering",
    ("recovery", "addictions"): "substance",
    ("parenting", "children"): "youth",
    ("support", "services"): "services",
    ("executive", "neurodevelopment"): "developmental",
    ("executive", "services"): "work",
    ("person-centered", "older"): "dementia",
    ("transition", "older"): "dementia",
    ("coordination", "services"): "services",
}

_SOURCE_BUNDLE_BY_SLUG = {
    # Screen-use pages need the established gaming/digital-health evidence set
    # rather than a generic family-services bundle.
    "digital-overuse-family-plan": "gaming",
    "family-screen-time-transition-plan": "gaming",
}

_EXPANSION_SOURCE_BUNDLES = {
    "grief": [
        {
            "publisher": "World Health Organization",
            "title": "WHO guidelines on conditions specifically related to stress",
            "url": "https://www.who.int/publications/i/item/9789241505406",
            "year": 2013,
        },
        {
            "publisher": "NHS",
            "title": "Get help with grief after bereavement or loss",
            "url": "https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/feelings-and-symptoms/grief-bereavement-loss/",
            "year": 2026,
        },
        {
            "publisher": "CDC",
            "title": "Grief | How Right Now",
            "url": "https://www.cdc.gov/howrightnow/emotion/grief/index.html",
            "year": 2026,
        },
    ],
}


def _ensure_expansion_source_bundles() -> None:
    for name, sources in _EXPANSION_SOURCE_BUNDLES.items():
        if name not in catalog.SOURCES:
            catalog.SOURCES[name] = [dict(source) for source in sources]


def _resolve_source_bundle(slug: str, category: str, source_bundle: str) -> str:
    _ensure_expansion_source_bundles()
    if source_bundle in catalog.SOURCES:
        return source_bundle

    resolved = _SOURCE_BUNDLE_BY_SLUG.get(slug)
    if resolved is None:
        resolved = _SOURCE_BUNDLE_BY_CONTEXT.get((source_bundle, category))
    if resolved is None:
        raise RuntimeError(
            f"Unregistered care-guide source bundle {source_bundle!r} for {slug!r} "
            f"in category {category!r}"
        )
    if resolved not in catalog.SOURCES:
        raise RuntimeError(
            f"Care-guide source bundle mapping for {slug!r} resolves to missing key {resolved!r}"
        )
    return resolved


def normalize_topics(values: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    normalized: list[tuple[str, ...]] = []
    for raw_topic in values:
        if len(raw_topic) != 9:
            raise RuntimeError("Every wave topic must preserve the v246 nine-column contract")
        topic = tuple(str(field).strip() for field in raw_topic)
        slug, _title, category, *_middle, source_bundle = topic
        if category not in catalog.CATEGORY_LABELS:
            raise RuntimeError(f"Unregistered care-guide category {category!r} for {slug!r}")
        resolved_source_bundle = _resolve_source_bundle(slug, category, source_bundle)
        normalized.append((*topic[:8], resolved_source_bundle))
    return normalized


def topics() -> list[tuple[str, ...]]:
    values = [
        topic
        for topic in base.TOPICS_1A + base.TOPICS_1B + base.TOPICS_1C + base.TOPICS_2
        if topic[0].strip() not in EXCLUDED_OVERLAP_SLUGS
    ]
    if len(values) != base.EXPECTED_WAVE_GUIDES:
        raise RuntimeError(f"Expected {base.EXPECTED_WAVE_GUIDES} wave topics, found {len(values)}")
    return normalize_topics(values)


def install(implementation):
    original = base.topics
    base.topics = topics
    try:
        return base.install(implementation)
    finally:
        base.topics = original
