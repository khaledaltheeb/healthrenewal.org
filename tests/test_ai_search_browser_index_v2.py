from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "ai-search" / "assets" / "search-core.js"
WORKER = ROOT / "ai-search" / "assets" / "search-worker.js"
APP = ROOT / "ai-search" / "assets" / "app.js"
MANIFEST = ROOT / "ai-search" / "data" / "manifest.json"
SITEMAP_INDEX = ROOT / "sitemap-index.xml"


class BrowserSemanticSearchV2Tests(unittest.TestCase):
    def test_browser_fallback_discovers_complete_sitemap_corpus(self) -> None:
        core = CORE.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        self.assertIn("discoverDocuments", core)
        self.assertIn("sitemap-index.xml", app)
        self.assertIn("maxDocuments = 6000", core)
        self.assertIn("<sitemapindex", SITEMAP_INDEX.read_text(encoding="utf-8"))

    def test_local_e5_vectors_are_cached_without_private_api(self) -> None:
        core = CORE.read_text(encoding="utf-8")
        worker = WORKER.read_text(encoding="utf-8")
        self.assertIn("indexedDB.open", core)
        self.assertIn("writeVectorCache", worker)
        self.assertIn("Xenova/multilingual-e5-small", worker)
        self.assertIn("passage: ", worker)
        self.assertIn("query: ", worker)
        self.assertNotIn("OPENAI_API_KEY", core + worker)
        self.assertNotIn("ANTHROPIC_API_KEY", core + worker)

    def test_precomputed_index_remains_optional_acceleration(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        worker = WORKER.read_text(encoding="utf-8")
        self.assertEqual(manifest["dimensions"], 384)
        self.assertIn("loadGenerated", worker)
        self.assertIn("local-sitemap", worker)
        self.assertIn("indexMode", APP.read_text(encoding="utf-8"))

    def test_search_is_retrieval_only(self) -> None:
        page = (ROOT / "ai-search" / "index.html").read_text(encoding="utf-8")
        self.assertIn("لا تنشئ تشخيصًا", page)
        self.assertIn("فتح الصفحة الأصلية", APP.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
