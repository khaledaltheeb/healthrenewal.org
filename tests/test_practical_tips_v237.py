from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/publish_practical_tips_v237.py"
spec = importlib.util.spec_from_file_location("tips_v237", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PracticalTipsV237Tests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path]:
        repo = root / "repo"
        site = root / "site"
        (repo / "content/sectors-v10").mkdir(parents=True)
        (repo / "content/v15").mkdir(parents=True)
        (repo / "content/v237").mkdir(parents=True)
        existing = []
        details = {}
        for index in range(20):
            slug = f"existing-{index:02d}"
            existing.append({
                "slug": slug,
                "title": f"دليل قائم {index:02d}",
                "category": "الأسرة",
                "tips": [f"خطوة {step} للدليل {index}" for step in range(1, 7)],
            })
            details[slug] = {
                "summary": f"ملخص عربي أصلي للدليل القائم {index} يشرح موقفًا عمليًا وأثره اليومي.",
                "when": "يفيد عند تكرر الموقف وتأثيره في الروتين أو العلاقات أو المشاركة اليومية.",
                "script": "سنبدأ بخطوة واحدة واضحة، ثم نراجع الأثر دون لوم أو استعجال.",
                "avoid": "تجنب الإهانة والضغط والتشخيص السريع وتغيير عدة عوامل معًا.",
                "success": "يظهر تحسن وظيفي صغير ويقل مقدار المساعدة أو شدة الضيق.",
                "seek_help": "اطلب مساعدة عند خطر فوري أو استمرار التعطل أو أفكار الأذى.",
            }
        (repo / "content/sectors-v10/tips.json").write_text(
            json.dumps({"guides": existing}, ensure_ascii=False), encoding="utf-8"
        )
        (repo / "content/v15/tips-details-v15.json").write_text(
            json.dumps(details, ensure_ascii=False), encoding="utf-8"
        )
        shutil.copy2(
            ROOT / "content/v237/practical-tips-v237.json",
            repo / "content/v237/practical-tips-v237.json",
        )
        (site / "assets").mkdir(parents=True)
        (site / "assets/logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )
        return repo, site

    def test_registry_has_eighty_unique_new_guides(self) -> None:
        registry = json.loads((ROOT / "content/v237/practical-tips-v237.json").read_text(encoding="utf-8"))
        guides = registry["new_guides"]
        self.assertEqual(registry["version"], 237)
        self.assertEqual(registry["target_total_guides"], 100)
        self.assertEqual(registry["minimum_visible_words"], 700)
        self.assertEqual(len(guides), 80)
        self.assertEqual(len({item["slug"] for item in guides}), 80)
        self.assertEqual(len({item["title"] for item in guides}), 80)
        self.assertTrue(all(len(item["tips"]) >= 6 for item in guides))
        self.assertGreaterEqual(len({item["category"] for item in guides}), 25)

    def test_publish_creates_hundred_deep_guides_and_ten_topics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, site = self.make_fixture(Path(tmp))
            report = module.publish(site, repo)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["guide_count"], 100)
            self.assertEqual(report["preserved_existing_guides"], 20)
            self.assertEqual(report["new_guides"], 80)
            self.assertEqual(report["pillar_count"], 10)
            self.assertGreaterEqual(report["category_count"], 25)
            self.assertGreaterEqual(report["minimum_after_words"], 700)
            self.assertEqual(report["remaining_below_minimum"], 0)
            self.assertEqual(report["sitemap_urls"], 111)
            self.assertEqual(report["topic_depth_status"], "passed")
            self.assertEqual(report["topic_depth_pages"], 10)
            self.assertGreaterEqual(report["minimum_topic_characters"], 1800)
            self.assertEqual(len(list((site / "tips").glob("*/index.html"))), 100)
            self.assertEqual(len(list((site / "tips/topics").glob("*/index.html"))), 10)

    def test_pages_have_metadata_schema_sources_and_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, site = self.make_fixture(Path(tmp))
            module.publish(site, repo)
            page = (site / "tips/school-refusal-first-steps/index.html").read_text(encoding="utf-8")
            for marker in (
                '<html lang="ar" dir="rtl">',
                '<meta name="description"',
                '<meta name="keywords"',
                '<meta name="robots"',
                '<meta name="googlebot"',
                '<link rel="canonical"',
                '"@type": "HowTo"',
                '"@type": "Article"',
                '"@type": "BreadcrumbList"',
                "متى تحتاج إلى مساعدة مهنية أو عاجلة؟",
                "لا توقف دواءً",
                "خدمات الطوارئ المحلية",
                "NICE",
                "أدلة مرتبطة",
            ):
                self.assertIn(marker, page)
            self.assertEqual(page.count("<h1>"), 1)
            self.assertNotIn("معاقين", page)

    def test_topic_pages_have_institutional_methodology_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, site = self.make_fixture(Path(tmp))
            report = module.publish(site, repo)
            pages = sorted((site / "tips/topics").glob("*/index.html"))
            self.assertEqual(len(pages), 10)
            lengths = []
            for page in pages:
                source = page.read_text(encoding="utf-8")
                self.assertEqual(source.count(module.TOPIC_START), 1, page)
                self.assertEqual(source.count(module.TOPIC_END), 1, page)
                for marker in (
                    "خطة تطبيق من سبع مراحل",
                    "تكييف المسار بحسب العمر والقدرة والسياق",
                    "مؤشرات متابعة عملية",
                    "حدود السلامة ومتى تنتقل إلى مساعدة متخصصة",
                    "طريقة اختيار الدليل التالي",
                ):
                    self.assertIn(marker, source, page)
                lengths.append(len(module._plain(source)))
            self.assertGreaterEqual(min(lengths), 1800)
            self.assertEqual(report["minimum_topic_characters"], min(lengths))

    def test_existing_guides_are_preserved_and_deepened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, site = self.make_fixture(Path(tmp))
            report = module.publish(site, repo)
            existing = next(item for item in report["pages"] if item["slug"] == "existing-00")
            self.assertGreaterEqual(existing["visible_words"], 700)
            page = (site / existing["path"]).read_text(encoding="utf-8")
            self.assertIn("دليل قائم 00", page)
            self.assertIn("ملخص عربي أصلي", page)

    def test_publish_is_deterministic_for_content_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, site = self.make_fixture(Path(tmp))
            first = module.publish(site, repo)
            first_paths = [item["path"] for item in first["pages"]]
            second = module.publish(site, repo)
            second_paths = [item["path"] for item in second["pages"]]
            self.assertEqual(first_paths, second_paths)
            self.assertEqual(first["guide_count"], second["guide_count"])
            self.assertEqual(second["remaining_below_minimum"], 0)
            self.assertEqual(second["topic_depth_pages"], 10)
            self.assertGreaterEqual(second["minimum_topic_characters"], 1800)
            self.assertEqual(len(list((site / "tips").glob("*/index.html"))), 100)
            for page in (site / "tips/topics").glob("*/index.html"):
                source = page.read_text(encoding="utf-8")
                self.assertEqual(source.count(module.TOPIC_START), 1, page)
                self.assertEqual(source.count(module.TOPIC_END), 1, page)

    def test_search_index_and_sitemap_have_all_guides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, site = self.make_fixture(Path(tmp))
            module.publish(site, repo)
            index = (site / "tips/index.html").read_text(encoding="utf-8")
            self.assertEqual(index.count('class="tip237-card"'), 100)
            self.assertIn('id="tips-search"', index)
            sitemap = (site / "sitemap-tips.xml").read_text(encoding="utf-8")
            self.assertEqual(sitemap.count("<url>"), 111)
            self.assertIn("/tips/topics/sleep/", sitemap)
            self.assertIn("/tips/school-refusal-first-steps/", sitemap)

    def test_no_prohibited_promises_or_stigmatizing_term(self) -> None:
        registry = (ROOT / "content/v237/practical-tips-v237.json").read_text(encoding="utf-8")
        rendered = module._compatibility_block("عنوان تجريبي") + module._topic_depth_block("مسار تجريبي")
        combined = registry + rendered
        for phrase in ("شفاء مضمون", "يعالج نهائيًا", "بديل عن الطبيب", "تشخيصك هو", "معاقين"):
            self.assertNotIn(phrase, combined)


if __name__ == "__main__":
    unittest.main()
