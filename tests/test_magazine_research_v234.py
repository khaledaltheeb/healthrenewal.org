from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_magazine_v201.py"
SPEC = importlib.util.spec_from_file_location("publish_magazine_v234", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MagazineResearchV234Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        site.mkdir()
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
            encoding="utf-8",
        )
        return site

    def test_publishes_every_discovered_article_and_sitemap(self) -> None:
        pages = MODULE.article_files()
        self.assertEqual(len(pages), 21)
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(report["version"], 234)
            self.assertEqual(report["research_summaries_published"], len(pages))
            self.assertEqual(len(report["articles"]), len(pages))
            self.assertEqual(report["sitemap"]["child_urls"], len(pages) + 1)
            self.assertEqual(report["unwired_research_pages"], 0)
            self.assertEqual(report["source_heading_contract"], "article-or-official-repository")
            self.assertEqual(report["limitations_contract"], "limitations-or-cautions-required")

            magazine = site / "magazine"
            self.assertTrue((magazine / "index.html").is_file())
            self.assertTrue((magazine / "research.css").is_file())
            source_headings = ("المصدر الأصلي", "السجل الأصلي", "السجل الجامعي", "السجل الجامعي الأصلي")
            limitation_terms = ("حدود", "قيود", "الحذر")
            for path in pages:
                text = (magazine / path.name).read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', text)
                self.assertTrue(any(heading in text for heading in source_headings), path.name)
                self.assertTrue(any(term in text for term in limitation_terms), path.name)

            sitemap = ET.parse(site / "sitemap-magazine.xml").getroot()
            urls = [node.text for node in sitemap.findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), len(pages) + 1)
            self.assertEqual(len(urls), len(set(urls)))
            self.assertIn(MODULE.URL, urls)
            for path in pages:
                self.assertIn(MODULE.URL + path.name, urls)

            saved = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["research_summaries_published"], len(pages))
            self.assertEqual(set(saved["articles"]), {path.name for path in pages})
            self.assertEqual(len(saved["source_sha256"]), len(pages))

    def test_publish_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            first = MODULE.publish(site)
            sitemap_before = (site / "sitemap-magazine.xml").read_bytes()
            index_before = (site / "magazine" / "index.html").read_bytes()
            second = MODULE.publish(site)
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(sitemap_before, (site / "sitemap-magazine.xml").read_bytes())
            self.assertEqual(index_before, (site / "magazine" / "index.html").read_bytes())

    def test_peer_led_summary_reports_null_findings(self) -> None:
        text = (ROOT / "magazine" / "peer-led-adolescent-mental-health-2025.html").read_text(encoding="utf-8")
        self.assertIn("لم يجد التحليل التلوي آثارًا دالة", text)
        self.assertIn("7,060", text)
        self.assertIn("ست دراسات من أصل سبع", text)
        self.assertNotIn("قد تُظهر فوائد لبعض مؤشرات الرفاه", text)

    def test_index_exposes_every_discovered_article(self) -> None:
        index = (ROOT / "magazine" / "index.html").read_text(encoding="utf-8")
        self.assertIn('"numberOfItems":21', index)
        self.assertIn('"hasPart"', index)
        self.assertEqual(index.count('class="card"'), 21)
        for path in MODULE.article_files():
            self.assertGreaterEqual(index.count(f'href="{path.name}"'), 2)
            self.assertIn(MODULE.URL + path.name, index)

    def test_high_risk_interpretations_and_theses_keep_limits(self) -> None:
        checks = {
            "adhd-school-social-skills-meta-analysis-2026.html": ("0.09", "أثر مهمل عمليًا"),
            "intensive-community-care-adolescents-2026.html": ("16,546", "أحجام الأثر صغيرة"),
            "neurodivergent-university-mental-health-interventions-2026.html": ("37 دراسة", "ضعف التصميم التشاركي"),
            "thesis-autism-heterogeneity-research-2025.html": ("النص الكامل محجوب", "51 ورقة"),
            "thesis-autistic-camouflaging-mental-health-2025.html": ("الارتباط", "لا يثبت"),
            "thesis-sensory-processing-adhd-autism-2026.html": ("الملخص الرسمي", "لا يجوز استخدام النتائج لتحديد تشخيص"),
            "autism-social-functioning-meta-analysis-2026.html": ("2,622 دراسة", "لا تبرر فرض نمط تواصل واحد"),
            "autism-ssri-children-meta-analysis-2026.html": ("606 مشاركين", "لا يعني إيقاف دواء موصوف فجأة"),
            "adhd-screen-time-meta-analysis-2026.html": ("235,283", "لا تثبت النتائج أن الشاشة تسبب ADHD"),
            "adhd-technology-interventions-meta-analysis-2026.html": ("p = 0.059", "لا تساوي تلقائيًا تحسنًا في السلوك اليومي"),
            "adhd-physical-fitness-meta-analysis-2026.html": ("SMD = −0.46", "لا تبرر النتيجة افتراض ضعف جسدي"),
            "autism-sleep-disorders-prevalence-meta-analysis-2026.html": ("I² = 98.8%", "لا يمكن استنتاج السببية"),
        }
        for filename, markers in checks.items():
            text = (ROOT / "magazine" / filename).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
