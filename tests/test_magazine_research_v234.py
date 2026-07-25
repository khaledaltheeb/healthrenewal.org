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
        self.assertEqual(len(pages), 60)
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(report["version"], 234)
            self.assertEqual(report["research_summaries_published"], 60)
            self.assertEqual(len(report["articles"]), 60)
            self.assertEqual(report["sitemap"]["child_urls"], 61)
            self.assertEqual(report["unwired_research_pages"], 0)
            self.assertEqual(report["index_contract"], "generated-from-discovered-articles")
            magazine = site / "magazine"
            source_headings = ("المصدر الأصلي", "السجل الأصلي", "السجل الجامعي", "السجل الجامعي الأصلي")
            limitation_terms = ("حدود", "قيود", "الحذر")
            for path in pages:
                text = (magazine / path.name).read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', text)
                self.assertTrue(any(heading in text for heading in source_headings), path.name)
                self.assertTrue(any(term in text for term in limitation_terms), path.name)
            sitemap = ET.parse(site / "sitemap-magazine.xml").getroot()
            urls = [node.text for node in sitemap.findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), 61)
            self.assertEqual(len(urls), len(set(urls)))
            for path in pages:
                self.assertIn(MODULE.URL + path.name, urls)
            saved = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["research_summaries_published"], 60)
            self.assertEqual(set(saved["articles"]), {path.name for path in pages})

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

    def test_generated_index_exposes_every_discovered_article(self) -> None:
        pages = MODULE.article_files()
        index = MODULE.render_index(pages)
        self.assertIn('"numberOfItems":60', index)
        self.assertEqual(index.count('class="card"'), 60)
        self.assertEqual(index.count('"@type":"ScholarlyArticle"'), 60)
        for path in pages:
            self.assertGreaterEqual(index.count(f'href="{path.name}"'), 2)
            self.assertIn(MODULE.URL + path.name, index)

    def test_sensitive_interpretations_keep_limits(self) -> None:
        checks = {
            "peer-led-adolescent-mental-health-2025.html": ("7,060", "لم يجد التحليل التلوي آثارًا دالة"),
            "youth-self-harm-interventions-meta-analysis-2026.html": ("RD = −0.12", "لا يعني اختفاء خطر الانتحار"),
            "adhd-screen-time-meta-analysis-2026.html": ("235,283", "لا تثبت النتائج أن الشاشة تسبب ADHD"),
            "aya-cancer-digital-mental-health-meta-analysis-2026.html": ("25 دراسة", "لا تستبدل علاج السرطان"),
            "adolescent-passive-smartphone-sensing-meta-analysis-2026.html": ("r = 0.12", "لا تكفي لتشخيص فرد"),
            "youth-transdiagnostic-internet-rct-2026.html": ("53%", "لا يثبت مساواة البرنامج بالعلاج الحضوري"),
            "down-syndrome-telehealth-systematic-review-2026.html": ("39 دراسة", "بديلًا كاملًا للرعاية الحضورية"),
            "homeless-youth-mental-disorders-meta-analysis-2026.html": ("25,320", "لا تسمح بتحديد اتجاه السببية"),
            "autism-parent-act-meta-analysis-2026.html": ("698 مشاركًا", "عدد التجارب سبع فقط"),
            "autism-caregiver-adjustment-review-2026.html": ("8 مقالات تدخلية", "تعريف موحد"),
            "family-carer-coping-mental-health-meta-analysis-2026.html": ("38 دراسة", "لا تثبت اتجاه السببية"),
            "autism-parent-resilience-factors-review-2026.html": ("13 دراسة", "معظم الدراسات مقطعية"),
            "autism-family-food-insecurity-meta-analysis-2026.html": ("انتشار مجمع 29%", "11 دراسة فقط"),
            "intellectual-disability-youth-healthcare-access-review-2026.html": ("33 دراسة", "تواصل غير واضح"),
            "neurodevelopmental-video-game-interventions-meta-analysis-2026.html": ("20 تجربة عشوائية", "لا يضمن انتقال الأثر"),
            "neurodevelopmental-exercise-executive-function-meta-analysis-2026.html": ("527 طفلًا", "I² = 81%"),
            "neurodevelopmental-sleep-family-wellbeing-review-2026.html": ("العلاقة قد تكون دائرية", "كثرة الدراسات المقطعية"),
            "down-syndrome-adult-medical-care-systematic-review-2026.html": ("8680 مرجعًا", "لم تُحدد دراسات مؤهلة"),
            "dcd-school-motor-interventions-meta-analysis-2026.html": ("Hedges g = 1.06", "لا يضمن التحسن نفسه"),
            "dcd-subtypes-systematic-review-2026.html": ("1,719 سجلًا", "لا يجوز استخدام هذه الأنماط"),
            "dcd-action-observation-motor-imagery-review-2026.html": ("199 طفلًا", "بديل عن التدريب الوظيفي"),
            "childhood-vision-impairment-longitudinal-review-2026.html": ("57,768 مشاركًا", "لا يثبت أن ضعف البصر وحده"),
            "visual-impairment-mental-health-review-2026.html": ("مراجعة سردية", "لا يعني أن كل شخص"),
            "intellectual-disability-healthcare-transition-review-2026.html": ("28 دراسة", "لا تختبر نموذج انتقال واحدًا"),
            "unilateral-cerebral-palsy-participation-meta-analysis-2026.html": ("I²=95%", "لا توجد طريقة واحدة"),
            "deaf-hard-hearing-adult-mental-disorders-review-2026.html": ("8,578,466", "لا تعني أن كل شخص"),
            "dysgraphia-interventions-scoping-review-2026.html": ("47 دراسة", "لا تحسب أثرًا علاجيًا مجمعًا"),
            "cerebral-palsy-participation-quality-life-study-2026.html": ("59 طفلًا", "لا تثبت اتجاه السببية"),
        }
        for filename, markers in checks.items():
            text = (ROOT / "magazine" / filename).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
