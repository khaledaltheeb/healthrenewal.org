from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from publish_research_magazine_v232 import CONTENT, load_data, publish


class ResearchMagazineV232Tests(unittest.TestCase):
    def make_site(self, root: Path, mode: str = "sitemapindex") -> Path:
        site = root / "site"
        site.mkdir()
        if mode == "sitemapindex":
            text = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>'
            )
        else:
            text = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
            )
        (site / "sitemap.xml").write_text(text, encoding="utf-8")
        return site

    def write_variant(self, root: Path, mutate) -> Path:
        data = copy.deepcopy(load_data())
        mutate(data)
        target = root / "variant.json"
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return target

    def test_publishes_all_real_research_pages_and_sources(self) -> None:
        data = load_data()
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = publish(site)
            self.assertEqual(report["published_pages"], len(data["summaries"]))
            self.assertEqual(report["target_pages"], 100)
            self.assertEqual(report["sitemap"]["urls"], len(data["summaries"]) + 1)
            index = (site / "magazine" / "index.html").read_text(encoding="utf-8")
            self.assertIn(f'الدفعة المنشورة: {len(data["summaries"])}', index)
            for item in data["summaries"]:
                page = site / "magazine" / "research" / item["slug"] / "index.html"
                self.assertTrue(page.is_file(), item["slug"])
                html = page.read_text(encoding="utf-8")
                self.assertIn(item["title_ar"], html)
                self.assertIn(item["title_original"], html)
                self.assertIn(item["doi"], html)
                self.assertIn(item["pmid"], html)
                self.assertIn("فتح المصدر الأصلي عبر DOI", html)
                self.assertIn("فتح سجل PubMed", html)
                self.assertIn("ScholarlyArticle", html)
                self.assertIn(f'research/{item["slug"]}/', index)

    def test_sitemap_contains_index_and_every_article_once(self) -> None:
        data = load_data()
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            publish(site)
            root = ET.parse(site / "sitemap-magazine.xml").getroot()
            urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), len(data["summaries"]) + 1)
            self.assertEqual(len(urls), len(set(urls)))
            self.assertIn("https://khaledaltheeb.github.io/pterminology-site/magazine/", urls)
            for item in data["summaries"]:
                self.assertIn(
                    f'https://khaledaltheeb.github.io/pterminology-site/magazine/research/{item["slug"]}/',
                    urls,
                )

    def test_publisher_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            first = publish(site)
            paths = [site / "magazine" / "index.html", site / "sitemap-magazine.xml"]
            paths.extend(site / path for path in first["pages"])
            before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
            second = publish(site)
            after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
            self.assertEqual(before, after)
            self.assertEqual(first["published_pages"], second["published_pages"])
            main = ET.parse(site / "sitemap.xml").getroot()
            refs = [
                (node.text or "").strip()
                for node in main.findall("{*}sitemap/{*}loc")
                if (node.text or "").strip().endswith("sitemap-magazine.xml")
            ]
            self.assertEqual(refs, ["https://khaledaltheeb.github.io/pterminology-site/sitemap-magazine.xml"])

    def test_duplicate_doi_and_pmid_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            variant = self.write_variant(
                root,
                lambda data: data["summaries"][1].update(
                    doi=data["summaries"][0]["doi"],
                    pmid=data["summaries"][0]["pmid"],
                ),
            )
            with self.assertRaises(SystemExit) as ctx:
                load_data(variant)
            self.assertIn("duplicate doi", str(ctx.exception))
            self.assertIn("duplicate pmid", str(ctx.exception))

    def test_short_or_unverified_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            variant = self.write_variant(
                root,
                lambda data: data["summaries"][0].update(
                    summary_ar="ملخص قصير",
                    doi="not-a-doi",
                ),
            )
            with self.assertRaises(SystemExit) as ctx:
                load_data(variant)
            message = str(ctx.exception)
            self.assertIn("Arabic summary is too short", message)
            self.assertIn("invalid DOI", message)

    def test_article_has_safety_and_no_false_external_review_claim(self) -> None:
        data = load_data()
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            publish(site)
            for item in data["summaries"]:
                html = (
                    site / "magazine" / "research" / item["slug"] / "index.html"
                ).read_text(encoding="utf-8")
                self.assertIn("لا يشخّص حالة", html)
                self.assertIn("دون ادعاء اعتماد خارجي", html)
                self.assertNotIn("مراجعة اختصاصية خارجية مكتملة", html)
                self.assertNotIn("علاج مضمون", html)

    def test_urlset_main_sitemap_is_supported_without_duplicates(self) -> None:
        data = load_data()
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp), mode="urlset")
            publish(site)
            publish(site)
            root = ET.parse(site / "sitemap.xml").getroot()
            urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), len(data["summaries"]) + 1)
            self.assertEqual(len(urls), len(set(urls)))


if __name__ == "__main__":
    unittest.main()
