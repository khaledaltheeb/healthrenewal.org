from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_magazine_sources_v202.py"
spec = importlib.util.spec_from_file_location("magazine_source_audit", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


PAGE_TEMPLATE = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <link rel="canonical" href="https://healthrenewal.org/magazine/{slug}/">
  {meta}
</head>
<body>
<h1>{title}</h1>
<h2>سؤال الدراسة</h2><p>{long_text}</p>
<h2>تصميم الدراسة</h2><p>دراسة رصدية محكمة.</p>
<h2>العينة</h2><p>شارك في الدراسة 120 مشاركًا.</p>
<h2>التدخل والمقارنة</h2><p>تمت مقارنة المجموعات وفق بروتوكول الدراسة.</p>
<h2>النتائج</h2><p>{long_text}</p>
<h2>تفسير النتائج</h2><p>{long_text}</p>
<h2>القيود والتحيز</h2><p>توجد قيود متعلقة بحجم العينة والتعميم.</p>
<h2>قابلية التعميم</h2><p>يجب الحذر عند تعميم النتائج.</p>
<h2>قراءة روافد</h2><p>{long_text}</p>
<h2>الدلالات العملية</h2><p>{long_text}</p>
<h2>ما لا تثبته الدراسة</h2><p>لا تثبت الدراسة السببية المطلقة.</p>
<h2>المراجع والمصدر الأصلي</h2>
{source}
</body></html>
"""


class MagazineSourceContractV202Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.magazine = self.root / "magazine"
        self.magazine.mkdir(parents=True)
        self.old_root = mod.ROOT
        self.old_magazine = mod.MAGAZINE
        mod.ROOT = self.root
        mod.MAGAZINE = self.magazine

    def tearDown(self) -> None:
        mod.ROOT = self.old_root
        mod.MAGAZINE = self.old_magazine
        self.tmp.cleanup()

    @staticmethod
    def _long_text() -> str:
        return " ".join(["نتيجة علمية موثقة قابلة للمراجعة والتحقق"] * 90)

    def _write_page(self, rel: str, *, source: str, meta: str = "") -> Path:
        path = self.magazine / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        slug = path.parent.name if path.name == "index.html" else path.stem
        path.write_text(
            PAGE_TEMPLATE.format(
                title="عنوان دراسة اختبارية",
                slug=slug,
                long_text=self._long_text(),
                source=source,
                meta=meta,
            ),
            encoding="utf-8",
        )
        return path

    def test_recursive_discovery_keeps_nested_study_pages_and_nested_index(self) -> None:
        top = self._write_page(
            "top-study.html",
            source='<a href="https://doi.org/10.1000/test.1">المصدر</a>',
        )
        nested = self._write_page(
            "evidence/2026/nested-study.html",
            source='<a href="https://pubmed.ncbi.nlm.nih.gov/12345678/">PubMed</a>',
        )
        nested_index = self._write_page(
            "pediatric-oncology/theses/cd28-car-t-t-all-farber-2026/index.html",
            source='<a href="https://doi.org/10.5282/edoc.37260">الأطروحة الأصلية</a>',
        )
        (self.magazine / "index.html").write_text("<html><body>listing</body></html>", encoding="utf-8")
        (self.magazine / "page" / "2.html").parent.mkdir(parents=True)
        (self.magazine / "page" / "2.html").write_text("<html><body>listing</body></html>", encoding="utf-8")
        (self.magazine / "category" / "oncology" / "index.html").parent.mkdir(parents=True)
        (self.magazine / "category" / "oncology" / "index.html").write_text("<html><body>listing</body></html>", encoding="utf-8")

        found = mod.discover_pages()
        self.assertEqual(found, [nested, nested_index, top])

    def test_extracts_doi_and_marks_structurally_complete_page(self) -> None:
        page = self._write_page(
            "doi-study.html",
            source='<a href="https://doi.org/10.1234/ABC.DEF">DOI</a>',
            meta='<meta name="citation_doi" content="10.1234/ABC.DEF">',
        )
        audit = mod.audit_page(page)
        self.assertIn("10.1234/abc.def", audit.doi)
        self.assertEqual(audit.source_contract, "identifier_present")
        self.assertEqual(audit.page_contract, "complete")
        self.assertEqual(audit.bibliographic_verification, "pending")

    def test_extracts_pubmed_identifier(self) -> None:
        page = self._write_page(
            "pmid-study.html",
            source='<a href="https://pubmed.ncbi.nlm.nih.gov/12345678/">PubMed PMID: 12345678</a>',
        )
        audit = mod.audit_page(page)
        self.assertEqual(audit.pmid, ["12345678"])
        self.assertEqual(audit.source_contract, "identifier_present")

    def test_missing_source_is_not_counted_as_complete_publication(self) -> None:
        page = self._write_page("no-source.html", source="<p>مرجع غير محدد</p>")
        audit = mod.audit_page(page)
        self.assertEqual(audit.source_contract, "missing_source")
        self.assertIn("no_original_source_identifier_or_probable_source_url", audit.issues)

    def test_internal_rawafid_link_is_not_an_original_source(self) -> None:
        page = self._write_page(
            "internal-only.html",
            source='<a href="https://healthrenewal.org/research/another-page/">صفحة داخلية</a>',
        )
        audit = mod.audit_page(page)
        self.assertEqual(audit.source_urls, [])
        self.assertEqual(audit.source_contract, "missing_source")

    def test_manifest_separates_structure_from_bibliographic_verification(self) -> None:
        self._write_page(
            "verified-id-present.html",
            source='<a href="https://doi.org/10.5555/example.2026">المصدر</a>',
        )
        manifest = mod.build_manifest()
        self.assertEqual(manifest["summary"]["study_pages"], 1)
        self.assertEqual(manifest["summary"]["identifier_present"], 1)
        self.assertEqual(manifest["summary"]["bibliographically_verified"], 0)
        self.assertTrue(manifest["policy"]["bibliographic_verification_required_before_complete_publication"])


if __name__ == "__main__":
    unittest.main()
