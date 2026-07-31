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

ORIGIN = "https://healthrenewal.org"


class EvidenceTrustPublicationV322Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "site"
        library = site / "library" / "index.html"
        library.parent.mkdir(parents=True, exist_ok=True)
        library.write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head>'
            '<meta charset="utf-8"><title>المكتبة</title>'
            f'<link rel="canonical" href="{ORIGIN}/library/">'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage"}</script>'
            '</head><body><main><h1>المكتبة</h1></main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-library.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{ORIGIN}/library/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    def test_source_pages_have_institutional_depth_and_boundaries(self) -> None:
        trust = (ROOT / "trust" / "index.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(publisher.words(trust), 1100)
        self.assertEqual(trust.count("<h1"), 1)
        self.assertIn(f'rel="canonical" href="{ORIGIN}/trust/"', trust)
        self.assertIn("application/ld+json", trust)
        for phrase in (
            "لا تتعامل المنهجية مع عدد الكلمات بوصفه جودة",
            "التحليل التلوي لا يحول الدراسات غير المتشابهة أو المتحيزة إلى نتيجة موثوقة",
            "الإفصاح عن التعارض لا يساوي إدارته",
            "لم تكتمل مراجعة خارجية مستقلة شاملة لكل إجراءاتها",
            "الاختبارات الآلية اكتمال المراجعة العلمية البشرية",
        ):
            self.assertIn(phrase, trust)

        start = (ROOT / "start-here" / "index.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(publisher.words(start), 900)
        self.assertEqual(start.count("<h1"), 1)
        self.assertIn(f'rel="canonical" href="{ORIGIN}/start-here/"', start)
        self.assertIn("application/ld+json", start)
        for phrase in (
            "المعلومات التثقيفية تساعد على الفهم والاستعداد للحوار مع المختص",
            "وجود علامة واحدة لا يثبت الحالة",
            "استخدم الأدوات لفهم نمط أو متابعة تغير أو تجهيز نقاش، لا لإثبات تشخيص",
            "حدود الاختبارات الآلية",
            "خطة عشر دقائق",
        ):
            self.assertIn(phrase, start)

        special = (ROOT / "special-needs" / "index.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(publisher.words(special), 1300)
        self.assertEqual(special.count("<h1"), 1)
        self.assertIn(f'rel="canonical" href="{ORIGIN}/special-needs/"', special)
        self.assertIn("application/ld+json", special)
        self.assertIsNone(publisher.BANNED.search(special))
        for phrase in (
            "الاحتياج لا يلغي القدرة",
            "التقييم الشامل: سؤال متعدد المصادر لا اختبار منفرد",
            "التواصل حق، وليس مكافأة",
            "التعليم الدامج: حضور ومشاركة وتعلم وانتماء",
            "قائمة مقدمي الخدمات تبقى فارغة حتى اكتمال التحقق المهني",
            "لم تكتمل مراجعة خارجية مستقلة شاملة للمركز",
        ):
            self.assertIn(phrase, special)

    def test_wrapper_publishes_institutional_pages_report_and_sitemaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = publisher.publish(site)
            trust = site / "trust" / "index.html"
            start = site / "start-here" / "index.html"
            special = site / "special-needs" / "index.html"
            self.assertTrue(trust.is_file())
            self.assertTrue(start.is_file())
            self.assertTrue(special.is_file())
            self.assertEqual(report["canonical_origin"], ORIGIN)
            self.assertEqual(report["base_path"], "/")
            self.assertEqual(report["legacy_origins_remaining"], 0)
            self.assertTrue(report["trust_page_published"])
            self.assertEqual(report["trust_page_path"], "trust/index.html")
            self.assertGreaterEqual(report["trust_page_words"], 1100)
            self.assertEqual(
                report["trust_page_review_status"],
                "internally-reviewed-external-methodology-review-required",
            )
            self.assertTrue(report["trust_page_sitemap_registered"])
            self.assertTrue(report["start_here_page_published"])
            self.assertEqual(report["start_here_page_path"], "start-here/index.html")
            self.assertGreaterEqual(report["start_here_page_words"], 900)
            self.assertTrue(report["start_here_page_sitemap_registered"])
            self.assertTrue(report["special_needs_hub_published"])
            self.assertEqual(report["special_needs_hub_path"], "special-needs/index.html")
            self.assertGreaterEqual(report["special_needs_hub_words"], 1300)
            self.assertEqual(
                report["special_needs_hub_review_status"],
                "internally-reviewed-external-specialist-review-required",
            )
            self.assertTrue(report["special_needs_sitemap_published"])
            api = json.loads(
                (site / "api" / "evidence-literacy-library-v322.json").read_text(encoding="utf-8")
            )
            self.assertEqual(api, report)
            library_urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-library.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            for url in (f"{ORIGIN}/trust/", f"{ORIGIN}/start-here/"):
                self.assertEqual(library_urls.count(url), 1)
            self.assertEqual(len(library_urls), len(set(library_urls)))
            self.assertTrue(all(url.startswith(f"{ORIGIN}/") for url in library_urls))
            special_urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            self.assertEqual(special_urls.count(f"{ORIGIN}/special-needs/"), 1)
            self.assertEqual(len(special_urls), len(set(special_urls)))
            self.assertTrue(all(url.startswith(f"{ORIGIN}/") for url in special_urls))


if __name__ == "__main__":
    unittest.main()
