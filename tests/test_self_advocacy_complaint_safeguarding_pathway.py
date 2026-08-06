import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths/self-advocacy/complaint-and-safeguarding-pathway.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_publication_metadata_and_review_contract():
    data = load_data()
    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] == "2027-02-06"
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema_types"]))


def test_pathway_is_complete_practical_and_person_led():
    data = load_data()
    pathway = data["pathway"]
    assert len(pathway) >= 7
    assert [item["step"] for item in pathway] == list(range(1, len(pathway) + 1))
    assert all(item.get("title") and item.get("quality_marker") for item in pathway)

    serialized = json.dumps(pathway, ensure_ascii=False)
    required = [
        "بكلماته",
        "السلامة",
        "التصعيد",
        "الانتقام",
        "وسيلة التواصل",
        "الخصوصية",
        "المراجعة",
        "تضارب المصالح",
    ]
    for phrase in required:
        assert phrase in serialized


def test_questions_actions_and_outcome_measures_are_substantive():
    data = load_data()
    questions = []
    for item in data["pathway"]:
        questions.extend(item.get("questions", []))
    assert len(questions) >= 18
    assert all(len(question.strip()) >= 20 for question in questions)
    assert len(data["practical_phrases"]) >= 6

    final_step = data["pathway"][-1]
    assert len(final_step["outcome_measures"]) >= 8
    assert "سلامة الشخص" in final_step["outcome_measures"]
    assert "منع الانتقام" in final_step["outcome_measures"]


def test_professional_limits_and_emergency_boundary():
    data = load_data()
    limits = " ".join(data["professional_limits"])
    for phrase in [
        "لا يمثل استشارة قانونية",
        "تختلف جهات الشكوى",
        "خطر مباشر",
        "لا يجوز إجبار الشخص",
        "غياب الدليل المكتوب",
    ]:
        assert phrase in limits


def test_internal_links_and_source_governance():
    data = load_data()
    links = data["internal_links"]
    assert len(links) >= 5
    assert all(item["href"].startswith("/") and item["label"] for item in links)

    sources = data["sources"]
    assert len(sources) >= 3
    assert all(item["url"].startswith("https://") for item in sources)
    assert all(item["rights"] == "link-cite-and-original-summary-only" for item in sources)
    publishers = {item["publisher"] for item in sources}
    assert "United Nations" in publishers
    assert "World Health Organization" in publishers


def test_disclosures_block_unproven_endorsement_and_restricted_copying():
    data = load_data()
    disclosures = " ".join(data["disclosures"].values())
    assert "لا توجد شراكة" in disclosures
    assert "اعتماد" in disclosures
    assert "دون نسخ أو ترجمة مطولة" in disclosures
    assert "القوانين والجهات والمواعيد المحلية" in disclosures


def test_faq_is_accessible_and_not_legally_overstated():
    data = load_data()
    faq = data["faq"]
    assert len(faq) >= 4
    assert all(item["question"].endswith("؟") for item in faq)
    assert all(len(item["answer"]) >= 60 for item in faq)
    faq_text = json.dumps(faq, ensure_ascii=False)
    assert "الصمت" in faq_text
    assert "دعم قانوني" in faq_text


def test_language_avoids_stigmatizing_or_false_authority_terms():
    text = DATA_PATH.read_text(encoding="utf-8")
    forbidden = [
        "المعاقين",
        "معتمد من منظمة الصحة العالمية",
        "بالتعاون مع الأمم المتحدة",
        "شريك رسمي",
        "يضمن النتيجة",
    ]
    for phrase in forbidden:
        assert phrase not in text
