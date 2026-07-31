from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_section_content_depth_v322 as depth322
import publish_evidence_literacy_library_v322 as library322


class EvidenceLiteracyLibraryV322Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "site"
        library = site / "library" / "index.html"
        library.parent.mkdir(parents=True, exist_ok=True)
        library.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            '<title>المكتبة الأكاديمية</title><meta name="description" content="مكتبة أكاديمية عربية.">'
            '<meta name="robots" content="index,follow"><link rel="canonical" href="https://healthrenewal.org/library/">'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage"}</script>'
            '</head><body><main><h1>المكتبة الأكاديمية</h1><p>محتوى تمهيدي للمكتبة.</p></main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-library.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/library/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        weak = site / "magazine" / "weak-page" / "index.html"
        weak.parent.mkdir(parents=True, exist_ok=True)
        weak.write_text(
            '<!doctype html><html lang="ar"><head><title>صفحة قصيرة</title>'
            '<meta name="description" content="صفحة قصيرة للاختبار.">'
            '<link rel="canonical" href="https://healthrenewal.org/magazine/weak-page/">'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script>'
            '</head><body><main><h1>صفحة قصيرة</h1><p>نص قصير.</p></main></body></html>',
            encoding="utf-8",
        )
        return site

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_publish_generates_four_deep_guides_and_collection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = library322.publish(site)
            self.assertEqual(report["version"], 322)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["guide_count"], 4)
            self.assertEqual(report["generated_page_count"], 5)
            self.assertEqual(report["section_count"], 24)
            self.assertGreaterEqual(report["source_count"], 12)
            self.assertGreaterEqual(report["minimum_guide_words"], 900)
            self.assertGreaterEqual(report["hub_words"], 500)
            self.assertFalse(report["external_methodology_review_completed"])
            self.assertEqual(report["next_review_due"], "2027-01-27")
            self.assertEqual(report["canonical_origin"], "https://healthrenewal.org")
            self.assertEqual(report["base_path"], "/")
            self.assertEqual(report["legacy_origins_remaining"], 0)

            expected = {
                "how-to-read-systematic-review": (
                    "المراجعة المنهجية ليست قوية لمجرد اسمها",
                    "الدلالة الإحصائية لا تحدد وحدها الأهمية العملية",
                    "جودة التقرير وفق PRISMA",
                ),
                "certainty-of-evidence-and-recommendations": (
                    "يقين الدليل يجيب عن مقدار الثقة",
                    "قوة التوصية تعبر عن مدى ترجيح خيار",
                    "التوصية المشروطة",
                ),
                "study-designs-bias-and-causality": (
                    "الارتباط يعني أن متغيرين يتحركان معًا",
                    "حجم العينة الكبير",
                    "STROBE",
                ),
                "appraise-clinical-guideline": (
                    "الإفصاح وحده ليس إدارة",
                    "تكييف الإرشاد ليس ترجمة لغوية فقط",
                    "تعارض المصالح",
                ),
            }
            for slug, phrases in expected.items():
                path = site / "library" / "evidence-literacy" / slug / "index.html"
                self.assertTrue(path.is_file())
                source = path.read_text(encoding="utf-8")
                self.assertEqual(source.count("<h1"), 1)
                self.assertEqual(source.count('class="section-card"'), 6)
                self.assertIn('"@type": "Article"', source)
                self.assertIn('"@type": "BreadcrumbList"', source)
                self.assertIn("لم تكتمل مراجعة خارجية مستقلة من متخصص في منهجية البحث", source)
                self.assertIsNone(library322.BANNED.search(source))
                self.assertGreaterEqual(library322.words(source), 900)
                self.assertNotIn("khaledaltheeb.github.io/pterminology-site", source)
                self.assertNotIn("/pterminology-site/", source)
                for phrase in phrases:
                    self.assertIn(phrase, source)

            hub = (site / "library" / "evidence-literacy" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(hub.count("<h1"), 1)
            self.assertEqual(hub.count('class="card"'), 4)
            self.assertIn("جودة التقرير لا تساوي بالضرورة جودة الدراسة", hub)
            parent = (site / "library" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(parent.count(library322.PARENT_MARKER), 1)
            self.assertEqual(parent.count("/library/evidence-literacy/"), 1)
            self.assertNotIn("/pterminology-site/", parent)

            api = json.loads((site / "api" / "evidence-literacy-library-v322.json").read_text(encoding="utf-8"))
            self.assertEqual(api, report)
            urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-library.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            for route in ["/library/evidence-literacy/"] + [f"/library/evidence-literacy/{slug}/" for slug in expected]:
                self.assertEqual(urls.count(library322.BASE + route), 1)
            self.assertEqual(len(urls), len(set(urls)))
            self.assertTrue(all(url.startswith("https://healthrenewal.org/") for url in urls))

    def test_publication_and_audit_are_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            library322.publish(site)
            first_audit = depth322.audit(site)
            tracked = [
                site / "library" / "index.html",
                site / "library" / "evidence-literacy" / "index.html",
                site / "library" / "evidence-literacy" / "how-to-read-systematic-review" / "index.html",
                site / "library" / "evidence-literacy" / "certainty-of-evidence-and-recommendations" / "index.html",
                site / "library" / "evidence-literacy" / "study-designs-bias-and-causality" / "index.html",
                site / "library" / "evidence-literacy" / "appraise-clinical-guideline" / "index.html",
                site / "sitemap-library.xml",
                site / "api" / "evidence-literacy-library-v322.json",
                site / "api" / "section-content-depth-v322.json",
            ]
            before = [self.digest(path) for path in tracked]
            library322.publish(site)
            second_audit = depth322.audit(site)
            after = [self.digest(path) for path in tracked]
            self.assertEqual(before, after)
            self.assertEqual(first_audit, second_audit)
            self.assertEqual(second_audit["evidence_literacy_page_count"], 5)
            self.assertGreaterEqual(second_audit["evidence_literacy_minimum_guide_words"], 900)
            self.assertIn("magazine", second_audit["highest_priority_sections"])
            self.assertIn("do not by themselves prove", second_audit["measurement_note"])

    def test_manifest_rejects_unused_or_unknown_sources(self) -> None:
        payload = library322.read_payload()
        payload["sources"].append(
            {
                "id": "X1",
                "organization": "Example",
                "title": "Unused source",
                "url": "https://example.org/unused-v322",
                "level": "S5",
                "reviewed": "2026-01-01",
            }
        )
        with self.assertRaises(SystemExit):
            library322.validate(payload)

    def test_reporting_guideline_is_not_treated_as_quality_score(self) -> None:
        payload = library322.read_payload()
        guides, _ = library322.validate(payload)
        text = json.dumps(guides, ensure_ascii=False)
        self.assertIn("التقرير الكامل وفق إرشاد مناسب يسهل التقييم، لكنه لا يصلح تصميمًا ضعيفًا", text)
        self.assertIn("اعتبار الالتزام بقائمة STROBE تقييمًا لجودة الدراسة نفسها", text)
        self.assertIn("خلط جودة التقرير وفق PRISMA مع انخفاض خطر التحيز", text)


if __name__ == "__main__":
    unittest.main()
