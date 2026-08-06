import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "special-needs/conditions/cornelia-de-lange-syndrome/source-verification.json"


def load_record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_source_record_exists_and_uses_single_canonical_slug():
    assert RECORD.is_file()
    record = load_record()
    assert record["condition"]["canonical_slug"] == "cornelia-de-lange-syndrome"
    assert record["publication_requirements"]["canonical_path"] == "/special-needs/conditions/cornelia-de-lange-syndrome/"
    assert record["publication_requirements"]["single_slug_only"] is True


def test_review_status_and_publication_status_are_honest():
    status = load_record()["status"]
    assert status["review_status"] == "internally-reviewed"
    assert status["external_review"] == "recommended-not-completed"
    assert status["publication_status"] == "production-source-wired"
    assert status["verified_at"] == "2026-08-05"
    assert status["next_review_due"] > status["verified_at"]


def test_primary_sources_and_identifiers_are_present():
    record = load_record()
    sources = {source["id"]: source for source in record["sources"]}
    assert {"genereviews-2026", "international-consensus-2018", "orphanet-199", "nord-2023"} <= set(sources)
    assert sources["genereviews-2026"]["last_update"] == "2026-06-16"
    consensus = sources["international-consensus-2018"]
    assert consensus["doi"] == "10.1038/s41576-018-0031-0"
    assert consensus["pmid"] == "29995837"
    assert consensus["pmcid"] == "PMC7136165"
    assert sources["orphanet-199"]["orpha_code"] == "ORPHA:199"
    assert all(source["url"].startswith("https://") for source in sources.values())


def test_rights_contract_prevents_copying_logos_and_partnership_claims():
    rights = load_record()["rights_and_attribution"]
    assert rights["classification"] == "link-cite-and-original-summary-only"
    forbidden = " ".join(rights["not_allowed_without_separate_permission"])
    for required in ("نسخ", "ترجمة", "الشعارات", "الشراكة", "المراجعة الخارجية"):
        assert required in forbidden


def test_professional_boundaries_block_diagnosis_and_individual_treatment():
    boundaries = load_record()["professional_boundaries"]
    prohibited = " ".join(boundaries["prohibited_uses"])
    for required in ("التشخيص الذاتي", "جرعات", "الاستشارة الوراثية", "اعتماد"):
        assert required in prohibited


def test_claim_governance_requires_primary_sources_for_clinical_claims():
    record = load_record()
    claims = {item["claim_area"]: item for item in record["claim_governance"]}
    for area in ("التشخيص والطيف الظاهري", "المتابعة الصحية والتدخلات", "السلوك والصحة النفسية والتواصل"):
        assert "genereviews-2026" in claims[area]["required_sources"]
        assert "international-consensus-2018" in claims[area]["required_sources"]


def test_publication_contract_requires_depth_schema_and_accessibility():
    requirements = load_record()["publication_requirements"]
    sections = " ".join(requirements["required_sections"])
    gates = " ".join(requirements["quality_gates"])
    for required in ("التشخيص التفريقي", "الانتقال للرشد", "ما يجب تجنبه", "20 خطوة", "حدود الاستخدام"):
        assert required in sections
    assert {"Article", "BreadcrumbList"} <= set(requirements["required_schema"])
    for required in ("canonical", "روابط داخلية", "RTL", "الهاتف", "الطباعة", "_site"):
        assert required in gates


def test_record_contains_no_false_external_review_or_partnership_claim():
    text = RECORD.read_text(encoding="utf-8")
    forbidden_claims = (
        '"external_review": "completed"',
        '"accredited": true',
        '"partnership": true',
        '"endorsed": true',
    )
    for claim in forbidden_claims:
        assert claim not in text
