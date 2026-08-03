from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_care_guides_v21 as publisher  # noqa: E402

SOURCE = ROOT / "content/v18/adhd-wfadhd-authorized-expansion-ar.json"
EXPECTED_SECTIONS = {
    "wfadhd_source_attribution",
    "evidence_foundation",
    "lifespan_assessment_pathway",
    "psychosocial_framework",
    "treatment_coordination",
    "communication_anti_stigma",
    "adult_adhd_pathway",
    "referral_continuity",
    "coaching_pathway",
    "professional_learning_path",
    "evidence_boundaries",
}
PROHIBITED = (
    r"اعتماد الاتحاد للمنصة",
    r"شريك رسمي",
    r"جرعة موصى بها",
    r"أوقف الدواء",
    r"شفاء مضمون",
    r"يشخ[ّ]?صك",
)


def load_payload() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_permission_provenance_and_independent_attribution_are_explicit() -> None:
    payload = load_payload()
    provenance = payload["provenance"]
    assert payload["language"] == "ar"
    assert payload["target_slug"] == "adhd-family-practical-guide"
    assert provenance["rights_status"] == "written-translation-permission-received"
    assert provenance["permission_received_at"] == "2026-08-03"
    assert "Gmail" in provenance["permission_evidence"]
    assert "لا تعني" in provenance["editorial_status"]
    assert "لا توجد دعوى شراكة" in provenance["commercial_claim"]


def test_expansion_is_deep_structured_and_non_repetitive() -> None:
    payload = load_payload()
    sections = payload["sections"]
    assert EXPECTED_SECTIONS == set(sections)
    assert set(payload["section_labels"]) == EXPECTED_SECTIONS
    assert sum(len(items) for items in sections.values()) >= 100
    assert all(len(items) >= 5 for items in sections.values())

    normalized: list[str] = []
    for section, items in sections.items():
        for item in items:
            value = re.sub(r"\s+", " ", item).strip().casefold()
            assert len(re.findall(r"[\w\u0600-\u06ff]+", value)) >= 7, (section, item)
            normalized.append(value)
    assert len(normalized) == len(set(normalized))


def test_sources_are_official_unique_and_cover_core_federation_resources() -> None:
    sources = load_payload()["source_additions"]
    assert len(sources) >= 7
    urls = [source["url"] for source in sources]
    assert len(urls) == len(set(urls))
    assert all(urlparse(url).scheme == "https" for url in urls)
    assert all(urlparse(url).netloc == "www.adhd-federation.org" for url in urls)
    titles = " ".join(source["title"] for source in sources)
    for marker in (
        "ADHD Guide",
        "Consensus Statement",
        "Referral Toolkit",
        "Talking about ADHD",
        "Coaching",
        "Practice Guidelines",
        "Seminars",
    ):
        assert marker in titles


def test_medical_safety_and_no_endorsement_overclaim() -> None:
    rendered = json.dumps(load_payload(), ensure_ascii=False)
    for pattern in PROHIBITED:
        assert re.search(pattern, rendered, re.IGNORECASE) is None, pattern
    assert "لا تعني أن الاتحاد راجع النص العربي أو اعتمده" in rendered
    assert "خدمات الطوارئ المحلية" in rendered
    assert "لا توجد وصفة عامة" in rendered
    assert "ليس خدمة طوارئ" in rendered


def test_publisher_merges_expansion_into_the_existing_adhd_guide() -> None:
    _, guides = publisher._load_legacy_guides_with_review_provenance()
    guide = next(
        item for item in guides if item.get("slug") == "adhd-family-practical-guide"
    )
    for section in EXPECTED_SECTIONS:
        assert section in guide
        assert guide[section]
    assert guide["reviewed_at"] == "2026-08-03"
    assert guide["review_status"] == "source-authorized-internally-reviewed"
    assert guide["translation_provenance"]["rights_status"] == (
        "written-translation-permission-received"
    )
    federation_sources = [
        source
        for source in guide["sources"]
        if urlparse(source["url"]).netloc == "www.adhd-federation.org"
    ]
    assert len(federation_sources) >= 7
