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

    def test_local_e5_reranking_is_bounded_and_private(self) -> None:
        core = CORE.read_text(encoding="utf-8")
        worker = WORKER.read_text(encoding="utf-8")
        self.assertIn("MAX_SEED_CANDIDATES = 96", worker)
        self.assertIn("MAX_HYDRATED_CANDIDATES = 36", worker)
        self.assertIn("candidatePool", worker)
        self.assertIn("hydrateCandidates", worker)
        self.assertIn("Xenova/multilingual-e5-small", worker)
        self.assertIn("761b726dd34fb83930e26aab4e9ac3899aa1fa78", worker)
        self.assertIn("dedupeRankedByUrl", worker)
        self.assertIn("revision: MODEL_REVISION", worker)
        self.assertIn("passage: ", worker)
        self.assertIn("query: ", worker)
        self.assertIn("QUERY_ALIASES", worker)
        self.assertNotIn("ensureLocalVectors", worker)
        self.assertNotIn("documents.length * DIMENSIONS", worker)
        self.assertNotIn("OPENAI_API_KEY", core + worker)
        self.assertNotIn("ANTHROPIC_API_KEY", core + worker)

    def test_precomputed_index_remains_optional_acceleration(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        worker = WORKER.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], 2)
        self.assertEqual(manifest["dimensions"], 384)
        self.assertEqual(manifest["corpusBaseUrl"], "https://healthrenewal.org/")
        self.assertTrue(manifest["normalized"])
        self.assertIn("loadGeneratedIndex", worker)
        self.assertIn("local-rerank", worker)
        self.assertIn("indexMode", app)
        self.assertIn("مجموعة مرشحة محدودة", app)

    def test_search_is_retrieval_only(self) -> None:
        page = (ROOT / "ai-search" / "index.html").read_text(encoding="utf-8")
        self.assertIn("لا تنشئ تشخيصًا", page)
        self.assertIn("فتح الصفحة الأصلية", APP.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
