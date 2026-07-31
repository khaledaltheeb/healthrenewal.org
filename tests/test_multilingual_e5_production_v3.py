from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MultilingualE5ProductionV3Tests(unittest.TestCase):
    def test_custom_domain_is_the_corpus_source(self) -> None:
        local = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")
        remote = (ROOT / "scripts/build_remote_semantic_search_index.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/semantic-search-index.yml").read_text(encoding="utf-8")
        self.assertIn('BASE_URL = "https://healthrenewal.org/"', local)
        self.assertIn('DEFAULT_BASE_URL = "https://healthrenewal.org/"', remote)
        self.assertIn("normalize_site_url", remote)
        self.assertIn("https://healthrenewal.org/sitemap-index.xml", workflow)
        self.assertNotIn("--base-url https://khaledaltheeb.github.io/pterminology-site/", workflow)

    def test_model_contract_is_pinned_and_consistent(self) -> None:
        manifest = json.loads((ROOT / "ai-search/data/manifest.json").read_text(encoding="utf-8"))
        worker = (ROOT / "ai-search/assets/search-worker.js").read_text(encoding="utf-8")
        builder = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")
        self.assertEqual(manifest["model"], "intfloat/multilingual-e5-small")
        self.assertEqual(manifest["browserModel"], "Xenova/multilingual-e5-small")
        self.assertEqual(manifest["dimensions"], 384)
        self.assertEqual(manifest["queryPrefix"], "query: ")
        self.assertEqual(manifest["passagePrefix"], "passage: ")
        self.assertIn(manifest["modelRevision"], builder)
        self.assertIn(manifest["browserModelRevision"], worker)
        self.assertIn("normalize_embeddings=True", builder)
        self.assertIn("pooling: 'mean', normalize: true", worker)

    def test_generated_results_are_unique_per_page(self) -> None:
        worker = (ROOT / "ai-search/assets/search-worker.js").read_text(encoding="utf-8")
        self.assertIn("function dedupeRankedByUrl", worker)
        self.assertIn("const uniqueRanked = dedupeRankedByUrl", worker)

    def test_search_page_uses_active_canonical(self) -> None:
        page = (ROOT / "ai-search/index.html").read_text(encoding="utf-8")
        self.assertIn('rel="canonical" href="https://healthrenewal.org/ai-search/"', page)
        self.assertNotIn("khaledaltheeb.github.io/pterminology-site/ai-search/", page)


if __name__ == "__main__":
    unittest.main()
