from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "rebuild_encyclopedia_v13.py"
NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def load_builder():
    spec = importlib.util.spec_from_file_location("encyclopedia_v13_test", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load encyclopedia builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EncyclopediaSeoSearchIntentV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="encyclopedia-seo-v1-")
        cls.site = Path(cls.temp.name)
        cls.builder = load_builder()
        cls.builder.SITE = cls.site
        cls.builder.BASE = "https://healthrenewal.org/"
        cls.builder.TODAY = "2026-08-01"
        cls.report = cls.builder.build()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_all_2000_pages_have_unique_complete_seo(self) -> None:
        pages = sorted((self.site / "encyclopedia").glob("concept-*/index.html"))
        self.assertEqual(2000, len(pages))
        titles: set[str] = set()
        descriptions: set[str] = set()
        canonicals: set[str] = set()
        primary_questions: set[str] = set()

        required = (
            '<meta name="robots" content="index,follow',
            '<meta name="googlebot" content="index,follow',
            'property="og:image:alt"',
            'name="twitter:image:alt"',
            'hreflang="ar"',
            'hreflang="x-default"',
            'data-encyclopedia-seo="v1"',
            'data-search-intent="encyclopedia-v1"',
            'data-search-intent-faq="encyclopedia-v1"',
        )
        schema_types = {"Organization", "WebSite", "DefinedTerm", "Article", "WebPage", "BreadcrumbList", "FAQPage"}

        for page in pages:
            source = page.read_text(encoding="utf-8")
            for fragment in required:
                self.assertIn(fragment, source, f"{page}: {fragment}")
            self.assertEqual(1, source.count("<h1>"), page)
            self.assertEqual(1, source.count('data-search-intent="encyclopedia-v1"'), page)
            self.assertEqual(1, source.count('data-search-intent-faq="encyclopedia-v1"'), page)
            self.assertGreaterEqual(source.count('<article><h3>'), 5, page)

            title_match = re.search(r"<title>(.*?)</title>", source, re.S)
            desc_match = re.search(r'<meta name="description" content="([^"]+)">', source)
            canonical_match = re.search(r'<link rel="canonical" href="([^"]+)">', source)
            schema_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.S)
            primary_match = re.search(r'<p class="ency-v13__intent-query">(.*?)</p>', source, re.S)
            self.assertIsNotNone(title_match, page)
            self.assertIsNotNone(desc_match, page)
            self.assertIsNotNone(canonical_match, page)
            self.assertIsNotNone(schema_match, page)
            self.assertIsNotNone(primary_match, page)

            title = title_match.group(1)
            description = desc_match.group(1)
            canonical = canonical_match.group(1)
            primary = re.sub(r"<[^>]+>", " ", primary_match.group(1)).strip()
            self.assertTrue(15 <= len(title) <= 78, (page, len(title), title))
            self.assertTrue(90 <= len(description) <= 225, (page, len(description), description))
            self.assertRegex(canonical, r"^https://healthrenewal\.org/encyclopedia/concept-\d{4}/$")

            graph = json.loads(schema_match.group(1))
            types = {node.get("@type") for node in graph.get("@graph", [])}
            self.assertTrue(schema_types.issubset(types), (page, types))
            faq = next(node for node in graph["@graph"] if node.get("@type") == "FAQPage")
            self.assertEqual(5, len(faq["mainEntity"]), page)
            self.assertEqual(primary, faq["mainEntity"][0]["name"], page)

            titles.add(title)
            descriptions.add(description)
            canonicals.add(canonical)
            primary_questions.add(primary)

        self.assertEqual(2000, len(titles))
        self.assertEqual(2000, len(descriptions))
        self.assertEqual(2000, len(canonicals))
        self.assertEqual(2000, len(primary_questions))

    def test_every_detail_url_is_present_once_in_term_sitemaps(self) -> None:
        urls: list[str] = []
        counts = []
        for name in ("sitemap-terms-1.xml", "sitemap-terms-2.xml"):
            root = ET.parse(self.site / name).getroot()
            values = [node.text for node in root.findall("sm:url/sm:loc", NAMESPACE) if node.text]
            counts.append(len(values))
            urls.extend(values)
        self.assertEqual([1000, 1000], counts)
        self.assertEqual(2000, len(urls))
        self.assertEqual(2000, len(set(urls)))
        self.assertEqual(
            {f"https://healthrenewal.org/encyclopedia/concept-{index:04d}/" for index in range(1, 2001)},
            set(urls),
        )

    def test_search_intent_api_and_audit_cover_every_page(self) -> None:
        audit = json.loads((self.site / "api/encyclopedia-audit-v13.json").read_text(encoding="utf-8"))
        seo = json.loads((self.site / "api/encyclopedia-seo-search-intent-v1.json").read_text(encoding="utf-8"))
        expected = {
            "concept_pages": 2000,
            "unique_seo_titles": 2000,
            "unique_descriptions": 2000,
            "unique_primary_queries": 2000,
            "seo_complete_pages": 2000,
            "search_intent_sections": 2000,
            "faq_schema_pages": 2000,
        }
        for key, value in expected.items():
            self.assertEqual(value, audit[key], key)
        self.assertEqual("passed", seo["status"])
        self.assertEqual(2000, seo["pages"])
        self.assertEqual(2000, len(seo["items"]))
        for item in seo["items"]:
            intent = item["search_intent"]
            self.assertEqual("encyclopedia-search-intent-v1", intent["contract"])
            self.assertGreaterEqual(len(intent["all_queries"]), 6)
            self.assertTrue(intent["primary_query"].endswith("؟"))


if __name__ == "__main__":
    unittest.main()
