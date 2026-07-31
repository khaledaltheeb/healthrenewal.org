from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "upgrade_women_sector_v244.py"
spec = importlib.util.spec_from_file_location("women_sector_v244", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.path.insert(0, str(ROOT / "scripts"))
spec.loader.exec_module(module)


def shell(title: str, canonical: str) -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="وصف قديم"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><link rel="manifest" href="/manifest.webmanifest"></head><body><header id="global-header"><nav>التنقل</nav></header><main><p>محتوى قديم أول.</p></main><main><h1>{title}</h1><p>محتوى قديم ثان.</p></main><footer id="global-footer">الحقوق</footer><script>navigator.serviceWorker.register('/sw.js')</script></body></html>'''


class WomenSectorV244Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="women-sector-v244-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp, ignore_errors=True))
        self.site = self.temp / "site"
        self.source = self.temp / "women.json"
        slugs = [
            "perinatal-mental-health", "postpartum-depression", "pregnancy-anxiety", "birth-trauma",
            "infertility-stress", "pregnancy-loss", "pmdd", "perimenopause", "menopause-wellbeing",
            "women-adhd", "women-autism", "care-load", "work-burnout-women", "violence-safety",
            "body-image", "eating-wellbeing", "sleep-women", "relationships-boundaries",
            "caregiver-wellbeing", "women-recovery-plan",
        ]
        articles = []
        for index, slug in enumerate(slugs, 1):
            articles.append({
                "slug": slug,
                "title": f"دليل الصحة النفسية للمرأة رقم {index}",
                "summary": "شرح عملي منظم يربط الأعراض بالسياق والجسد والوظيفة اليومية ويحدد مسار طلب المساعدة.",
                "signals": ["تغير مستمر عن خط الأساس", "تعطل النوم أو العمل أو الرعاية", "انسحاب أو قلق أو حزن متزايد"],
                "steps": ["سجلي النمط والمدة", "رتبي دعمًا عمليًا", "احجزي تقييمًا عند استمرار التعطل", "ضعي خطة أمان عند الخطر"],
                "phrases": ["أحتاج تقييمًا شاملًا لا تفسيرًا واحدًا", "أحتاج مساعدة عملية محددة اليوم"],
                "avoid": "اختزال التجربة في الهرمونات أو لوم المرأة أو اتخاذ قرار دوائي ذاتي.",
            })
        self.source.write_text(json.dumps({"key": "women", "articles": articles}, ensure_ascii=False), encoding="utf-8")
        self.articles = articles

        hub = self.site / "sectors" / "women" / "index.html"
        hub.parent.mkdir(parents=True)
        hub.write_text(shell("صفحة المرأة القديمة", "https://old.invalid/women/"), encoding="utf-8")
        for article in articles:
            target = self.site / "sectors" / "women" / article["slug"] / "index.html"
            target.parent.mkdir(parents=True)
            target.write_text(shell(article["title"], f'https://old.invalid/{article["slug"]}/'), encoding="utf-8")
        (self.site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")

    def run_upgrade(self) -> dict[str, object]:
        with contextlib.redirect_stdout(io.StringIO()):
            return module.upgrade(self.site, self.source)

    def test_upgrades_twenty_guides_and_is_idempotent(self) -> None:
        report = self.run_upgrade()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["version"], 244)
        self.assertEqual(report["source_articles"], 20)
        self.assertEqual(report["article_pages_enriched"], 20)
        self.assertGreaterEqual(report["hub_words"], 2200)
        self.assertGreaterEqual(report["minimum_article_words"], 700)
        self.assertEqual(report["hub_h1"], 1)
        self.assertGreaterEqual(report["hub_h2"], 15)
        self.assertEqual(report["faq_items"], 6)
        self.assertGreaterEqual(report["institutional_sources"], 12)
        self.assertFalse(report["banned_term_present"])
        self.assertFalse(report["diagnostic_claim_present"])

        hub_path = self.site / "sectors" / "women" / "index.html"
        hub = hub_path.read_text(encoding="utf-8")
        self.assertEqual(hub.count("<main"), 1)
        self.assertEqual(hub.count("<h1"), 1)
        self.assertEqual(hub.count('rel="canonical"'), 1)
        self.assertEqual(hub.count('name="robots"'), 1)
        self.assertEqual(hub.count('name="googlebot"'), 1)
        self.assertEqual(hub.count('name="keywords"'), 1)
        self.assertEqual(hub.count('data-women-sector-v244="1"'), 1)
        for schema_type in ("CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"):
            self.assertIn(schema_type, hub)
        for section_id in ("principles", "life-course", "observe", "perinatal", "cycle", "menopause", "work", "safety", "triage", "plan", "appointment", "family", "inclusion", "guides", "faq", "sources", "methodology"):
            self.assertIn(f'id="{section_id}"', hub)
        self.assertIn('id="global-header"', hub)
        self.assertIn('id="global-footer"', hub)
        self.assertIn("navigator.serviceWorker.register", hub)
        self.assertNotIn("noindex", hub.lower())

        for article in self.articles:
            text = (self.site / "sectors" / "women" / article["slug"] / "index.html").read_text(encoding="utf-8")
            self.assertEqual(text.count("<main"), 1, article["slug"])
            self.assertEqual(text.count("<h1"), 1, article["slug"])
            self.assertEqual(text.count('rel="canonical"'), 1, article["slug"])
            self.assertEqual(text.count(f'data-women-article-v244="{article["slug"]}"'), 1, article["slug"])
            self.assertIn('"@type":"Article"', text, article["slug"])
            self.assertIn("متابعة لمدة أسبوعين", text, article["slug"])
            self.assertIn("ذات الاحتياجات الخاصة", text, article["slug"])
            self.assertIn("متى تصبح الاستجابة عاجلة؟", text, article["slug"])
            self.assertNotIn("noindex", text.lower(), article["slug"])

        robots = (self.site / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(robots.count("# women-sector-v244"), 1)
        self.assertIn("Allow: /sectors/women/", robots)
        self.assertIn("Sitemap: https://healthrenewal.org/sitemap.xml", robots)
        evidence = json.loads((self.site / "api" / "women-sector-v244.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence, report)

        before = {path.relative_to(self.site): path.read_bytes() for path in self.site.rglob("*") if path.is_file() and path.name != "women-sector-v244.json"}
        second = self.run_upgrade()
        after = {path.relative_to(self.site): path.read_bytes() for path in self.site.rglob("*") if path.is_file() and path.name != "women-sector-v244.json"}
        self.assertEqual(before, after)
        self.assertEqual(second["article_pages_enriched"], 0)
        self.assertFalse(second["robots_updated"])

    def test_rejects_explicit_robots_block(self) -> None:
        (self.site / "robots.txt").write_text("User-agent: *\nDisallow: /sectors/women/\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "robots_disallows_women_sector"):
            self.run_upgrade()

    def test_rejects_incomplete_source_inventory(self) -> None:
        payload = json.loads(self.source.read_text(encoding="utf-8"))
        payload["articles"].pop()
        self.source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "women_source_requires_20_articles"):
            self.run_upgrade()


if __name__ == "__main__":
    unittest.main()
