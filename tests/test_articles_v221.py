from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_articles_v221.py"
SOURCE = ROOT / "content" / "v221" / "articles" / "normal-anxiety-vs-anxiety-disorder-ar.json"


class StrictHTMLParser(HTMLParser):
    pass


class ArticlesV221Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="articles-v221-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp, ignore_errors=True))
        (self.temp / "magazine").mkdir(parents=True)
        (self.temp / "magazine/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body>'
            '<section><h2>قائمة فحص كل مادة علمية</h2><ol><li>فحص</li></ol></section>'
            '</body></html>',
            encoding="utf-8",
        )
        (self.temp / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )

    def publish(self) -> None:
        subprocess.run(["python3", str(PUBLISHER), str(self.temp)], cwd=ROOT, check=True)

    def test_source_contract_and_official_sources(self) -> None:
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(data["review_status"], "internally-reviewed")
        self.assertEqual(data["publication_status"], "approved-for-build")
        self.assertEqual(data["risk_level"], "moderate")
        self.assertTrue(90 <= len(data["description"]) <= 180)
        hosts = {urlparse(source["url"]).hostname for source in data["sources"]}
        self.assertEqual(
            hosts,
            {"www.who.int", "www.nimh.nih.gov", "www.nice.org.uk", "www.nhs.uk"},
        )
        text = " ".join(
            data["quick_answer"]
            + [item["normal"] + " " + item["concern"] for item in data["comparison"]]
            + [paragraph for section in data["sections"] for paragraph in section["paragraphs"]]
            + [item["myth"] + " " + item["fact"] for item in data["myths"]]
        )
        self.assertGreaterEqual(len(re.findall(r"[\u0600-\u06FF]+", text)), 1400)
        for phrase in ("تشخيصك هو", "يعالج نهائيًا", "يضمن الشفاء", "بديل عن الطبيب"):
            self.assertNotIn(phrase, text)

    def test_publishes_deep_article_index_magazine_link_and_sitemap_idempotently(self) -> None:
        self.publish()
        paths = {
            "article": self.temp / "articles/normal-anxiety-vs-anxiety-disorder/index.html",
            "index": self.temp / "articles/index.html",
            "magazine": self.temp / "magazine/index.html",
            "sitemap": self.temp / "sitemap-articles.xml",
            "report": self.temp / "api/articles-v221.json",
        }
        for path in paths.values():
            self.assertTrue(path.is_file(), path)

        article = paths["article"].read_text(encoding="utf-8")
        index = paths["index"].read_text(encoding="utf-8")
        magazine = paths["magazine"].read_text(encoding="utf-8")
        StrictHTMLParser().feed(article)
        StrictHTMLParser().feed(index)

        self.assertEqual(len(re.findall(r"<h1\b", article)), 1)
        self.assertEqual(len(re.findall(r"<h1\b", index)), 1)
        self.assertGreaterEqual(len(re.findall(r"<h2\b", article)), 12)
        self.assertIn('dir="rtl"', article)
        self.assertIn('lang="ar"', article)
        self.assertIn('<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/articles/normal-anxiety-vs-anxiety-disorder/">', article)
        for marker in (
            '<meta name="description"',
            '<meta name="keywords"',
            'property="og:image"',
            'name="twitter:card"',
            '"@type":"Article"',
            '"@type":"BreadcrumbList"',
            'class="urgent"',
            "المصادر الرسمية",
            "متى يكون التقييم المهني خطوة مناسبة؟",
            "ورقة ملاحظة سبعة أيام",
            "حدود هذا المقال",
        ):
            self.assertIn(marker, article)
        self.assertNotIn("approved-for-build", article)
        self.assertNotIn(">API<", article)
        self.assertEqual(magazine.count("data-articles-v221"), 1)
        self.assertEqual(magazine.count('href="/pterminology-site/articles/normal-anxiety-vs-anxiety-disorder/"'), 1)

        visible = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", article, flags=re.S)
        self.assertGreaterEqual(len(re.findall(r"[\u0600-\u06FF]+", visible)), 1400)

        tree = ET.parse(paths["sitemap"])
        urls = [node.text for node in tree.getroot().findall("{*}url/{*}loc") if node.text]
        self.assertEqual(
            urls,
            [
                "https://khaledaltheeb.github.io/pterminology-site/articles/",
                "https://khaledaltheeb.github.io/pterminology-site/articles/normal-anxiety-vs-anxiety-disorder/",
            ],
        )
        main_tree = ET.parse(self.temp / "sitemap.xml")
        child_urls = [node.text for node in main_tree.getroot().findall("{*}sitemap/{*}loc") if node.text]
        self.assertEqual(child_urls.count("https://khaledaltheeb.github.io/pterminology-site/sitemap-articles.xml"), 1)

        report = json.loads(paths["report"].read_text(encoding="utf-8"))
        self.assertEqual(report["articles"], 1)
        self.assertEqual(report["authoritative_sources"], 5)
        self.assertTrue(report["magazine_linked"])
        self.assertFalse(report["live_verified"])

        before = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
        self.publish()
        after = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
