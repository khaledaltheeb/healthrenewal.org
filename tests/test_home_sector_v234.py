from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "upgrade_home_sector_v234.py"
SOURCE = ROOT / "content" / "sectors-v10" / "home.json"
spec = importlib.util.spec_from_file_location("home_sector_v234", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def shell(title: str, canonical: str, body: str) -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="وصف قديم"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><link rel="stylesheet" href="/assets/css/theme-v10.css"></head><body><header id="global-header"><nav>التنقل</nav></header><main>{body}</main><footer id="global-footer">الحقوق</footer><script>navigator.serviceWorker.register('/sw.js')</script></body></html>'''


class HomeSectorV234Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="home-sector-v234-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp, ignore_errors=True))
        self.site = self.temp / "site"
        payload = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.articles = payload["articles"]
        self.assertEqual(len(self.articles), 20)

        hub = self.site / "sectors" / "home" / "index.html"
        hub.parent.mkdir(parents=True)
        hub.write_text(shell("صفحة قديمة", "https://old.invalid/", "<h1>الصحة النفسية للعائلة</h1><p>محتوى أولي.</p>"), encoding="utf-8")
        for article in self.articles:
            target = self.site / "sectors" / "home" / article["slug"] / "index.html"
            target.parent.mkdir(parents=True)
            target.write_text(
                shell(
                    article["title"],
                    f'https://old.invalid/{article["slug"]}/',
                    f'<article><h1>{article["title"]}</h1><p>{article["summary"]}</p></article>',
                ),
                encoding="utf-8",
            )
        (self.site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")

    def run_upgrade(self) -> dict[str, object]:
        with contextlib.redirect_stdout(io.StringIO()):
            return module.upgrade(self.site, SOURCE)

    def test_upgrades_complete_twenty_page_sector_and_is_idempotent(self) -> None:
        report = self.run_upgrade()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["version"], 234)
        self.assertEqual(report["source_articles"], 20)
        self.assertEqual(report["article_pages_enriched"], 20)
        self.assertGreaterEqual(report["hub_words"], module.MINIMUM_HUB_WORDS)
        self.assertGreaterEqual(report["minimum_article_words"], module.MINIMUM_ARTICLE_WORDS)
        self.assertEqual(report["word_count_method"], "semantic-visible-tokens-v244")
        self.assertEqual(report["depth_contract_version"], 244)
        self.assertEqual(report["semantic_depth_blocks_added"], 21)
        self.assertEqual(report["hub_h1"], 1)
        self.assertGreaterEqual(report["hub_h2"], 10)
        self.assertEqual(report["faq_items"], 6)
        self.assertGreaterEqual(report["institutional_sources"], 10)
        self.assertFalse(report["banned_term_present"])
        self.assertFalse(report["diagnostic_claim_present"])

        hub_path = self.site / "sectors" / "home" / "index.html"
        hub = hub_path.read_text(encoding="utf-8")
        self.assertEqual(hub.count("<h1"), 1)
        self.assertEqual(hub.count('rel="canonical"'), 1)
        self.assertEqual(hub.count('name="robots"'), 1)
        self.assertEqual(hub.count('name="googlebot"'), 1)
        self.assertEqual(hub.count('name="keywords"'), 1)
        self.assertEqual(hub.count('data-home-sector-v234="1"'), 1)
        self.assertEqual(hub.count(module.HUB_DEPTH_MARKER), 1)
        for schema_type in ("CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"):
            self.assertIn(schema_type, hub)
        for section_id in (
            "overview",
            "framework",
            "stages",
            "signals",
            "meeting",
            "plan",
            "guides",
            "professional-help",
            "faq",
            "sources",
            "methodology",
        ):
            self.assertIn(f'id="{section_id}"', hub)
        self.assertIn('id="global-header"', hub)
        self.assertIn('id="global-footer"', hub)
        self.assertIn("navigator.serviceWorker.register", hub)
        self.assertNotIn("noindex", hub.lower())

        for article in self.articles:
            text = (self.site / "sectors" / "home" / article["slug"] / "index.html").read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1"), 1, article["slug"])
            self.assertEqual(text.count('rel="canonical"'), 1, article["slug"])
            self.assertEqual(text.count(module.ARTICLE_START), 1, article["slug"])
            self.assertEqual(text.count(module.ARTICLE_DEPTH_MARKER), 1, article["slug"])
            self.assertIn('"@type":"Article"', text, article["slug"])
            self.assertIn("قياس الأثر لمدة أسبوعين", text, article["slug"])
            self.assertIn("للأشخاص ذوي الاحتياجات الخاصة", text, article["slug"])
            self.assertNotIn("noindex", text.lower(), article["slug"])
            self.assertGreaterEqual(module.semantic_visible_words(text), module.MINIMUM_ARTICLE_WORDS)

        robots = (self.site / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(robots.count("# home-sector-v234"), 1)
        self.assertIn("Allow: /sectors/home/", robots)
        self.assertIn("Sitemap: https://healthrenewal.org/sitemap.xml", robots)
        evidence = json.loads((self.site / "api" / "home-sector-v234.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["source_articles"], 20)
        self.assertEqual(evidence["word_count_method"], "semantic-visible-tokens-v244")

        before = {
            path.relative_to(self.site): path.read_text(encoding="utf-8")
            for path in self.site.rglob("*")
            if path.is_file() and path.name != "home-sector-v234.json"
        }
        second = self.run_upgrade()
        after = {
            path.relative_to(self.site): path.read_text(encoding="utf-8")
            for path in self.site.rglob("*")
            if path.is_file() and path.name != "home-sector-v234.json"
        }
        self.assertEqual(before, after)
        self.assertEqual(second["article_pages_enriched"], 0)
        self.assertEqual(second["semantic_depth_blocks_added"], 0)
        self.assertFalse(second["robots_updated"])

    def test_replaces_complete_generated_v10_multi_main_range(self) -> None:
        generated = (
            '<!doctype html><html><head><title>قديم</title></head><body>'
            '<header id="global-header">الهيدر</header>'
            '<main id="content-v10"><div>مسار التنقل</div></main>'
            '<section class="hero-v10"><main class="hero-grid-v10"><h1>العنوان القديم</h1></main></section>'
            '<main><section><h2>المحتوى القديم</h2></section></main>'
            '<footer id="global-footer">الفوتر</footer></body></html>'
        )
        replacement = '<main id="home-v234"><h1>العنوان المؤسسي الجديد</h1></main>'
        updated = module.replace_main(generated, replacement)
        self.assertEqual(updated.count("<main"), 1)
        self.assertEqual(updated.count("<h1"), 1)
        self.assertIn('id="global-header"', updated)
        self.assertIn('id="global-footer"', updated)
        self.assertIn('id="home-v234"', updated)
        self.assertNotIn("العنوان القديم", updated)
        self.assertNotIn("المحتوى القديم", updated)
        self.assertNotIn("hero-v10", updated)

    def test_rejects_explicit_robots_block(self) -> None:
        (self.site / "robots.txt").write_text(
            "User-agent: *\nDisallow: /sectors/home/\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "robots_disallows_home_sector"):
            self.run_upgrade()


if __name__ == "__main__":
    unittest.main()
