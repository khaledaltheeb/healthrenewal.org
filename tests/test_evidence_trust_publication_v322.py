from __future__ import annotations

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

import publish_evidence_literacy_library_v322 as publisher


class EvidenceTrustPublicationV322Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "site"
        library = site / "library" / "index.html"
        library.parent.mkdir(parents=True, exist_ok=True)
        library.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head>'
            '<meta charset="utf-8"><title>المكتبة</title>'
            '<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/library/">'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage"}</script>'
            '</head><body><main><h1>المكتبة</h1></main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-library.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/library/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    def test_source_page_has_institutional_depth_and_boundaries(self) -> None:
        path = ROOT / "trust" / "index.html"
        source = path.read_text(encoding="utf-8")
        self.assertGreaterEqual(publisher.words(source), 1100)
        self.assertEqual(source.count("<h1"), 1)
        self.assertIn('rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/trust/"', source)
        self.assertIn('application/ld+json', source)
        for phrase in (
            "لا تتعامل المنهجية مع عدد الكلمات بوصفه جودة",
            "التحليل التلوي لا يحول الدراسات غير المتشابهة أو المتحيزة إلى نتيجة موثوقة",
            "الإفصاح عن التعارض لا يساوي إدارته",
            "لم تكتمل مراجعة خارجية مستقلة شاملة لكل إجراءاتها",
            "الاختبارات الآلية اكتمال المراجعة العلمية البشرية",
        ):
            self.assertIn(phrase, source)

    def test_wrapper_publishes_trust_page_report_and_sitemap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = publisher.publish(site)
            trust = site / "trust" / "index.html"
            self.assertTrue(trust.is_file())
            self.assertTrue(report["trust_page_published"])
            self.assertEqual(report["trust_page_path"], "trust/index.html")
            self.assertGreaterEqual(report["trust_page_words"], 1100)
            self.assertEqual(
                report["trust_page_review_status"],
                "internally-reviewed-external-methodology-review-required",
            )
            self.assertTrue(report["trust_page_sitemap_registered"])
            api = json.loads(
                (site / "api" / "evidence-literacy-library-v322.json").read_text(encoding="utf-8")
            )
            self.assertEqual(api, report)
            urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-library.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            self.assertEqual(
                urls.count("https://khaledaltheeb.github.io/pterminology-site/trust/"),
                1,
            )
            self.assertEqual(len(urls), len(set(urls)))


if __name__ == "__main__":
    unittest.main()
