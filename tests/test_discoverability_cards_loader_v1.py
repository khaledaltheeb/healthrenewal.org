from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = {
    "/family-guide/",
    "/ai-search/",
    "/contact/",
    "/source-registry/",
    "/team-and-partners/",
    "/accessibility/",
    "/learning-paths/opportunities/",
    "/provider-assessment-demo/training/",
    "/provider-assessment-demo/professional-console.html",
    "/special-needs/assistive-technology/",
    "/special-needs/conditions/prader-willi-syndrome/",
    "/special-needs/assistive-technology/selection-checklist/",
    "/special-needs/assistive-technology/training/",
    "/special-needs/assistive-technology/ethics-and-service/",
    "/special-needs/assistive-technology/innovation-review/",
    "/special-needs/assistive-technology/continuing-education/",
}


def test_platform_shell_loads_discoverability_catalog():
    shell = (ROOT / "assets/platform/platform-core.js").read_text(encoding="utf-8")
    assert "discoverability-cards.js?v=1.0.0" in shell
    assert "data-pt-discoverability-loader" in shell


def test_catalog_exposes_all_previously_hidden_pages():
    catalog = (ROOT / "assets/platform/discoverability-cards.js").read_text(encoding="utf-8")
    assert catalog.count("section.dataset.ptDiscoverabilityCards = 'v1'") == 1
    assert catalog.count(".pt-discovery-card") >= 1
    for target in TARGETS:
        assert target in catalog, target
    assert len(TARGETS) == 16


def test_catalog_is_limited_to_nearest_section_hubs():
    catalog = (ROOT / "assets/platform/discoverability-cards.js").read_text(encoding="utf-8")
    for hub in (
        "'/sections/'",
        "'/learning-paths/'",
        "'/provider-assessment-demo/'",
        "'/special-needs/'",
        "'/special-needs/assistive-technology/'",
    ):
        assert hub in catalog
