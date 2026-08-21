import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "materialize_pediatric_oncology.py"
SPEC = importlib.util.spec_from_file_location("materialize_pediatric_oncology", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def row(kind="study", slug="sample-study"):
    plural = "studies" if kind == "study" else "theses"
    token = "a" * 32 if kind == "study" else "b" * 32
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "slug": slug,
        "title": "عنوان علمي تجريبي للأطفال",
        "excerpt": "ملخص عربي مستقل يوضح هدف الصفحة للقارئ دون مبالغة.",
        "body_text": "## السؤال العلمي\n" + "كلمة علمية مفيدة " * 520 + "\n\n## القيود\nهذه حدود مهمة للدراسة.",
        "body_json": {"blocks": []},
        "content_type": "research",
        "status": "scheduled",
        "scheduled_at": "2026-08-21T00:00:00+00:00",
        "published_at": None,
        "updated_at": "2026-08-21T00:00:00+00:00",
        "seo_title": "عنوان علمي للأطفال",
        "seo_description": "وصف علمي عربي واضح للمادة البحثية يشرح التصميم والنتائج والقيود ويقود القارئ إلى المصدر الأصلي دون تقديم توصية علاجية فردية أو مبالغة.",
        "canonical_url": f"/magazine/pediatric-oncology/{plural}/{slug}/",
        "robots_index": True,
        "robots_follow": True,
        "schema_json": {
            "pediatric_oncology_program": True,
            "publication_ready": True,
            "release_token": token,
            "evidence_record_type": kind,
            "evidence_digest_contract_version": 1,
            "evidence_public_route_contract_version": 2,
            "content_evidence_audit_status": "passed",
            "content_evidence_audit_release_token": token,
            "source_identity_verified": True,
            "originality_report": {"passed": True, "release_token": token},
        },
        "references_json": [
            {"url": "https://pubmed.ncbi.nlm.nih.gov/12345678/", "title": "Primary source"},
            {"url": "https://doi.org/10.1000/example", "title": "DOI"},
            {"url": "https://www.cancer.gov/", "title": "NCI"},
        ],
        "author_display_name": "فريق تحرير منصة روافد",
    }


class MaterializerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ped-onc-materializer-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_article_contains_exact_release_contract(self):
        item = row(); text = MOD.render_article(item)
        self.assertIn('<meta name="rawafid-release-token" content="' + "a" * 32 + '">', text)
        self.assertIn('<link rel="canonical" href="https://healthrenewal.org' + item["canonical_url"] + '">', text)
        self.assertIn('<meta name="robots" content="index,follow', text)
        self.assertEqual(text.count("<h1>"), 1)
        self.assertIn("السؤال العلمي", text)
        self.assertIn("Primary source", text)

    def test_rejects_wrong_route_family(self):
        item = row("study"); item["canonical_url"] = "/magazine/pediatric-oncology/theses/sample-study/"
        with self.assertRaises(ValueError): MOD.validate_row(item)

    def test_rejects_path_traversal(self):
        item = row(); item["canonical_url"] = "/magazine/pediatric-oncology/studies/../escape/"
        with self.assertRaises(ValueError): MOD.destination_for(self.tmp, item)

    def test_materializes_study_thesis_and_hubs(self):
        payload = {"schema_version": 1, "items": [row(), row("thesis", "sample-thesis")]}
        report = MOD.materialize(self.tmp, payload)
        self.assertEqual(report["records"], 2)
        self.assertEqual(report["studies"], 1)
        self.assertEqual(report["theses"], 1)
        expected = [self.tmp / "magazine/pediatric-oncology/index.html", self.tmp / "magazine/pediatric-oncology/studies/index.html", self.tmp / "magazine/pediatric-oncology/theses/index.html", self.tmp / "magazine/pediatric-oncology/studies/sample-study/index.html", self.tmp / "magazine/pediatric-oncology/theses/sample-thesis/index.html"]
        self.assertTrue(all(path.is_file() for path in expected))
        self.assertIn("sample-study", expected[1].read_text(encoding="utf-8"))
        self.assertIn("sample-thesis", expected[2].read_text(encoding="utf-8"))

    def test_refuses_to_overwrite_non_owned_page(self):
        item = row(); path = MOD.destination_for(self.tmp, item); path.parent.mkdir(parents=True); path.write_text("<!doctype html><title>human page</title>", encoding="utf-8")
        with self.assertRaises(RuntimeError): MOD.materialize(self.tmp, {"schema_version": 1, "items": [item]})

    def test_removes_stale_owned_article_only(self):
        stale = self.tmp / "magazine/pediatric-oncology/studies/old-study/index.html"; stale.parent.mkdir(parents=True); stale.write_text(MOD.MARKER + " stale", encoding="utf-8")
        report = MOD.materialize(self.tmp, {"schema_version": 1, "items": [row()]})
        self.assertFalse(stale.exists()); self.assertIn("magazine/pediatric-oncology/studies/old-study/index.html", report["removed"])

    def test_preserves_unowned_stale_article(self):
        stale = self.tmp / "magazine/pediatric-oncology/studies/old-study/index.html"; stale.parent.mkdir(parents=True); stale.write_text("human page", encoding="utf-8")
        MOD.materialize(self.tmp, {"schema_version": 1, "items": [row()]}); self.assertTrue(stale.exists())

    def test_report_is_deterministic_for_same_payload(self):
        payload = {"schema_version": 1, "items": [row()]}; MOD.materialize(self.tmp, payload); report_path = self.tmp / MOD.REPORT_PATH; first = report_path.read_text(encoding="utf-8"); MOD.materialize(self.tmp, payload); second = report_path.read_text(encoding="utf-8"); self.assertEqual(first, second)

    def test_markdown_parser_preserves_full_body(self):
        source = "## عنوان\nفقرة أولى\nفقرة ثانية\n\n- واحد\n- اثنان\n\n### فرعي\nنهاية"; rendered = MOD.body_html(source)
        for phrase in ("عنوان", "فقرة أولى", "فقرة ثانية", "واحد", "اثنان", "فرعي", "نهاية"): self.assertIn(phrase, rendered)

    def test_route_contract_requires_version_two(self):
        item = row(); item["schema_json"]["evidence_public_route_contract_version"] = 1
        with self.assertRaises(ValueError): MOD.route_info(item)


if __name__ == "__main__":
    unittest.main()
