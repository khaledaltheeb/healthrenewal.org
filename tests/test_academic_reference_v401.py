from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import enhance_academic_reference_v400 as base  # noqa: E402
import enhance_academic_reference_v401 as depth  # noqa: E402
import publish_academic_library_v326 as academic  # noqa: E402


def all_items():
    for section_slug, section in academic.SECTIONS.items():
        for item in section["entries"]:
            yield section_slug, section, item


def test_reference_inventory_and_unique_routes() -> None:
    rows = list(all_items())
    assert len(rows) == 80
    routes = {f"/library/{section}/{item['slug']}/" for section, _, item in rows}
    assert len(routes) == 80
    assert {key: len(value["entries"]) for key, value in academic.SECTIONS.items()} == {
        "branches": 25,
        "therapies": 27,
        "research": 28,
    }


def test_every_reference_page_meets_depth_sources_and_governance_contract() -> None:
    original = base.MIN_WORDS
    base.MIN_WORDS = 650
    try:
        for section_slug, section, item in all_items():
            page, preliminary_words, references = base.render(section_slug, section, item)
            assert preliminary_words >= 650
            assert references >= 6
            marker = "</article></div></main>"
            assert page.count(marker) == 1
            page = page.replace(marker, depth.appendix(section_slug, item) + marker, 1)
            assert base.words(page) >= 1000
            assert page.count("<h1") == 1
            assert page.count('class="governance-grid"') == 1
            assert page.count('id="reference-use"') == 1
            assert f'https://healthrenewal.org/library/{section_slug}/{item["slug"]}/' in page
            assert "المراجعة الخارجية المستقلة لم تكتمل" in page
    finally:
        base.MIN_WORDS = original


def test_source_registry_uses_secure_traceable_urls() -> None:
    assert len(base.SOURCES) >= 25
    for source_id, (_, _, url) in base.SOURCES.items():
        parsed = urlparse(url)
        assert parsed.scheme == "https", source_id
        assert parsed.netloc, source_id
        assert "example." not in parsed.netloc, source_id


def test_alias_targets_exist_and_do_not_create_new_canonical_topics() -> None:
    for section_slug, aliases in base.ALIASES.items():
        canonical_titles = {item["title"] for item in academic.SECTIONS[section_slug]["entries"]}
        for alias, target in aliases.items():
            assert alias != target
            assert target in canonical_titles, (section_slug, alias, target)


def test_special_evidence_notes_point_to_existing_entries() -> None:
    known_slugs = {item["slug"] for _, _, item in all_items()}
    assert set(base.EVIDENCE_NOTES).issubset(known_slugs)
    assert set(base.SLUG_REFS).issubset(known_slugs)


def test_outer_publisher_uses_the_final_v401_depth_pass() -> None:
    source = (SCRIPTS / "publish_evidence_literacy_library_v322.py").read_text(encoding="utf-8")
    assert "from enhance_academic_reference_v401 import enhance as enhance_academic_reference" in source
    assert 'reference.get("version") != 401' in source
    assert 'reference.get("minimum_entry_words", 0)) < 1000' in source
    assert 'reference.get("minimum_references", 0)) < 6' in source
    assert 'reference.get("duplicate_and_alias_redirects", 0)) < 18' in source
    assert '"api/academic-library-reference-v401.json"' in source
