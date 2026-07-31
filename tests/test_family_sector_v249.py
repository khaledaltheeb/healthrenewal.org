from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_family_sector_v249 as family

SOURCE = ROOT / "content" / "sectors-v10" / "family.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FamilySectorV249Tests(unittest.TestCase):
    def fixture(self) -> tuple[Path, Path, dict]:
        root = Path(tempfile.mkdtemp(prefix="family-sector-v249-"))
        self.addCleanup(shutil.rmtree, root, True)
        site = root / "site"
        source = root / "family.json"
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        shell = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>قديم</title><meta name="description" content="قديم"><meta name="robots" content="noindex"></head><body><header><a href="/">الرئيسية</a></header><main><h1>صفحة قديمة</h1><p>محتوى مختصر</p></main><footer>حقوق المنصة</footer></body></html>'''
        hub = site / "sectors" / "family" / "index.html"
        hub.parent.mkdir(parents=True)
        hub.write_text(shell, encoding="utf-8")
        for item in data["articles"]:
            page = site / "sectors" / "family" / item["slug"] / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text(shell, encoding="utf-8")
        (site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\nSitemap: https://healthrenewal.org/sitemap.xml\n",
            encoding="utf-8",
        )
        return site, source, data

    def test_source_inventory_is_complete_and_unique(self) -> None:
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        articles = data["articles"]
        self.assertEqual(len(articles), 20)
        slugs = [item["slug"] for item in articles]
        self.assertEqual(len(slugs), len(set(slugs)))
        for required in (
            "emotional-safety",
            "active-listening",
            "healthy-boundaries",
            "conflict-repair",
            "family-meetings",
            "family-grief",
            "divorce-support",
            "caregiver-burnout",
        ):
            self.assertIn(required, slugs)

    def test_upgrade_enforces_depth_metadata_schema_safety_and_discovery(self) -> None:
        site, source, data = self.fixture()
        report = family.upgrade(site, source)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["version"], 249)
        self.assertEqual(report["source_articles"], 20)
        self.assertEqual(report["article_pages_enriched"], 20)
        self.assertGreaterEqual(report["hub_words"], 2500)
        self.assertGreaterEqual(report["minimum_article_words"], 800)
        self.assertEqual(report["hub_h1"], 1)
        self.assertGreaterEqual(report["hub_h2"], 15)
        self.assertEqual(report["faq_items"], 6)
        self.assertGreaterEqual(report["institutional_sources"], 12)
        self.assertFalse(report["banned_term_present"])
        self.assertFalse(report["diagnostic_claim_present"])

        hub = (site / "sectors/family/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count("<main"), 1)
        self.assertEqual(hub.count("<h1"), 1)
        self.assertEqual(hub.count('rel="canonical"'), 1)
        self.assertEqual(hub.count('name="robots"'), 1)
        self.assertEqual(hub.count('name="googlebot"'), 1)
        self.assertNotIn("noindex", hub.lower())
        self.assertIn("CollectionPage", hub)
        self.assertIn("BreadcrumbList", hub)
        self.assertIn("ItemList", hub)
        self.assertIn("FAQPage", hub)
        self.assertIn("الأشخاص ذوي الاحتياجات الخاصة", hub)
        self.assertIn("خطة أسرية لمدة 30 يومًا", hub)
        for item in data["articles"]:
            self.assertIn(f'/sectors/family/{item["slug"]}/', hub)
            page = site / "sectors" / "family" / item["slug"] / "index.html"
            text = page.read_text(encoding="utf-8")
            self.assertEqual(text.count("<main"), 1, item["slug"])
            self.assertEqual(text.count("<h1"), 1, item["slug"])
            self.assertEqual(text.count('rel="canonical"'), 1, item["slug"])
            self.assertEqual(text.count('name="robots"'), 1, item["slug"])
            self.assertEqual(text.count('name="googlebot"'), 1, item["slug"])
            self.assertEqual(text.count('data-family-article-schema-v249='), 1, item["slug"])
            self.assertIn('"@type":"Article"', text, item["slug"])
            self.assertIn("خطة متابعة لمدة أسبوعين", text, item["slug"])
            self.assertNotIn("noindex", text.lower(), item["slug"])

        robots = (site / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(robots.count("Allow: /sectors/family/"), 1)
        written = json.loads((site / "api/family-sector-v249.json").read_text(encoding="utf-8"))
        self.assertEqual(written, report)

    def test_second_run_is_byte_stable_and_reports_no_new_pages(self) -> None:
        site, source, _ = self.fixture()
        first = family.upgrade(site, source)
        paths = sorted((site / "sectors/family").rglob("index.html")) + [site / "robots.txt"]
        before = {path.relative_to(site).as_posix(): digest(path) for path in paths}
        second = family.upgrade(site, source)
        after = {path.relative_to(site).as_posix(): digest(path) for path in paths}
        self.assertEqual(first["hub_words"], second["hub_words"])
        self.assertEqual(first["minimum_article_words"], second["minimum_article_words"])
        self.assertEqual(second["article_pages_enriched"], 0)
        self.assertEqual(before, after)

    def test_missing_article_page_fails_closed(self) -> None:
        site, source, data = self.fixture()
        target = site / "sectors" / "family" / data["articles"][3]["slug"] / "index.html"
        target.unlink()
        with self.assertRaisesRegex(ValueError, "family_article_missing"):
            family.upgrade(site, source)

    def test_duplicate_slug_fails_closed(self) -> None:
        site, source, data = self.fixture()
        data["articles"][1]["slug"] = data["articles"][0]["slug"]
        source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate_slugs"):
            family.upgrade(site, source)


if __name__ == "__main__":
    unittest.main()
