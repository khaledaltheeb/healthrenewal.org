import json
import tempfile
import unittest
from pathlib import Path

from scripts import publish_editorial_methodology_v178 as publisher


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v178" / "editorial-methodology-ar.json"


class EditorialMethodologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))
        cls.html = publisher.render()

    def test_content_is_substantial_and_explicit(self):
        text = " ".join(
            p for section in self.data["sections"] for p in section["paragraphs"]
        )
        self.assertGreaterEqual(len(text.split()), 500)
        for phrase in [
            "لا تعني أن كل صفحة راجعها اختصاصي خارجي",
            "لا تنشأ صفحة لمجرد استهداف كلمة مفتاحية",
            "الفرع أو المسودة أو الدمج ليس نشرًا",
            "لا تسجل الصفحة منشورة إلا بعد نجاح GitHub Pages",
        ]:
            self.assertIn(phrase, text)

    def test_metadata_schema_and_accessibility(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('<link rel="canonical" href="https://healthrenewal.org/editorial-methodology/">', self.html)
        self.assertIn('application/ld+json', self.html)
        self.assertIn('"Article"', self.html)
        self.assertIn('"BreadcrumbList"', self.html)
        self.assertIn('href="#content"', self.html)
        self.assertEqual(self.html.count("<h1>"), 1)

    def test_no_false_external_review_or_accreditation(self):
        forbidden = ["مراجع من خبراء", "معتمد دوليًا", "اعتماد مهني مؤكد"]
        for phrase in forbidden:
            self.assertNotIn(phrase, self.html)
        self.assertIn("لا تدعي مراجعة اختصاصي خارجي أو اعتمادًا مهنيًا", self.html)

    def test_build_outputs_are_explicitly_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_site = publisher.SITE
            publisher.SITE = Path(tmp)
            try:
                publisher.main()
            finally:
                publisher.SITE = old_site
            page = Path(tmp) / "editorial-methodology" / "index.html"
            report = json.loads((Path(tmp) / "api" / "editorial-methodology-v178.json").read_text(encoding="utf-8"))
            self.assertTrue(page.is_file())
            self.assertEqual(report["status"], "built-not-published")
            self.assertTrue((Path(tmp) / "sitemap-editorial-methodology.xml").is_file())


if __name__ == "__main__":
    unittest.main()
